"""
speech/tts.py — edge-tts based text-to-speech for the robot waiter.

Usage
-----
Synthesise complete audio (buffered):

    from robot_waiter_ai.speech.tts import TextToSpeech

    tts = TextToSpeech()                          # tr-TR-EmelNeural by default
    audio_bytes = await tts.synthesize("Merhaba!")
    # audio_bytes is a raw MP3 blob ready to send to the browser or write to disk

Streaming (lower time-to-first-audio):

    async for chunk in tts.synthesize_streaming("Siparişinizi alıyorum."):
        await websocket.send_bytes(chunk)         # send each chunk as it arrives

Design notes
------------
* Uses edge-tts (rany2/edge-tts) which wraps Microsoft Edge's online neural TTS
  service.  No API key required; requires an internet connection.
* Turkish neural voices: tr-TR-EmelNeural (female) and tr-TR-AhmetNeural (male).
* The async interface mirrors stt.py — synthesize() and synthesize_streaming()
  are both coroutines and safe to call from any asyncio event loop.
* No state is mutated after __init__, so a single TextToSpeech instance is safe
  to share across concurrent requests.
* edge-tts is imported lazily inside each method so that the rest of the project
  remains importable even without edge-tts installed.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import AsyncIterator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

DEFAULT_VOICE: str = "tr-TR-EmelNeural"
DEFAULT_RATE: str = "+0%"
DEFAULT_VOLUME: str = "+0%"

# Hardcoded — no network call required to enumerate these.
_SUPPORTED_TR_VOICES: list[str] = [
    "tr-TR-EmelNeural",   # female, natural, warm
    "tr-TR-AhmetNeural",  # male, clear, professional
]


# ---------------------------------------------------------------------------
# TextToSpeech
# ---------------------------------------------------------------------------

class TextToSpeech:
    """Async wrapper around edge-tts for Turkish neural speech synthesis."""

    AUDIO_CONTENT_TYPE: str = "audio/mpeg"

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        rate: str = DEFAULT_RATE,
        volume: str = DEFAULT_VOLUME,
    ) -> None:
        self.voice = voice
        self.rate = rate
        self.volume = volume

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @staticmethod
    def available_turkish_voices() -> list[str]:
        """Return the list of supported Turkish edge-tts voices.

        This is a hardcoded list — no network call is made.  Call
        ``edge-tts --list-voices`` on the CLI if you want the full
        catalogue of all edge-tts voices.

        Returns
        -------
        list[str]
            ["tr-TR-EmelNeural", "tr-TR-AhmetNeural"]
        """
        return list(_SUPPORTED_TR_VOICES)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _import_edge_tts():
        """Import edge_tts or raise a clear RuntimeError with install hint."""
        try:
            import edge_tts  # type: ignore
            return edge_tts
        except ImportError as exc:
            raise RuntimeError(
                "edge-tts gerekli: pip install edge-tts"
            ) from exc

    def _validate_text(self, text: str) -> str:
        """Strip and validate input text; raise ValueError if empty."""
        stripped = text.strip()
        if not stripped:
            raise ValueError("Metin boş olamaz.")
        return stripped

    def _make_communicate(self, text: str):
        """Construct an edge_tts.Communicate instance for the given text."""
        edge_tts = self._import_edge_tts()
        return edge_tts.Communicate(
            text,
            self.voice,
            rate=self.rate,
            volume=self.volume,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def synthesize(self, text: str) -> bytes:
        """Synthesise *text* and return complete audio as a bytes object.

        Collects all audio chunks from edge-tts into memory before returning.
        Use :meth:`synthesize_streaming` for lower time-to-first-audio when
        serving over a streaming HTTP or WebSocket connection.

        Parameters
        ----------
        text:
            Turkish text to synthesise.  Must not be empty or whitespace-only.

        Returns
        -------
        bytes
            Raw MP3 audio data.  Send directly as an HTTP response body or
            pass to the browser via a Blob URL.

        Raises
        ------
        ValueError
            If *text* is empty or contains only whitespace.
        RuntimeError
            If edge-tts is not installed.
        Exception
            Network or service errors propagate from edge-tts unchanged so the
            caller can decide how to handle them (retry, fallback, etc.).
        """
        stripped = self._validate_text(text)
        communicate = self._make_communicate(stripped)

        audio_chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

        audio_bytes = b"".join(audio_chunks)
        logger.debug(
            "synthesize(): voice=%s, text_len=%d, audio_bytes=%d",
            self.voice,
            len(stripped),
            len(audio_bytes),
        )
        return audio_bytes

    async def synthesize_streaming(self, text: str) -> AsyncIterator[bytes]:
        """Async generator that yields MP3 audio chunks as they arrive.

        Each yielded value is a ``bytes`` object containing one chunk of MP3
        data.  The caller can forward chunks immediately to the client for
        the lowest possible time-to-first-audio.

        Parameters
        ----------
        text:
            Turkish text to synthesise.  Must not be empty or whitespace-only.

        Yields
        ------
        bytes
            Individual MP3 audio chunks in order.

        Raises
        ------
        ValueError
            If *text* is empty or contains only whitespace.
        RuntimeError
            If edge-tts is not installed.
        Exception
            Network or service errors propagate unchanged.
        """
        stripped = self._validate_text(text)
        communicate = self._make_communicate(stripped)

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                logger.debug(
                    "synthesize_streaming(): yielding %d bytes", len(chunk["data"])
                )
                yield chunk["data"]


# ---------------------------------------------------------------------------
# PiperTTS — offline, aarch64-compatible
# ---------------------------------------------------------------------------

_SPEECH_DIR = Path(__file__).resolve().parent          # speech/
_PROJECT_ROOT = _SPEECH_DIR.parent.parent              # Garson-bot/

_PIPER_BINARY_CANDIDATES: list[str] = [
    str(_PROJECT_ROOT / "piper" / "piper"),
    str(_PROJECT_ROOT / "piper" / "piper.exe"),
    "piper",
]

_PIPER_MODEL_CANDIDATES: list[Path] = [
    _PROJECT_ROOT / "robot_waiter_ai" / "models" / "tr_TR-fahrettin-medium.onnx",
    _PROJECT_ROOT / "robot_waiter_ai" / "models" / "tr_TR-fahrettin-high.onnx",
    _PROJECT_ROOT / "models" / "tr_TR-fahrettin-medium.onnx",
]


def _find_piper_binary(override: str | None = None) -> str | None:
    import shutil
    if override:
        return override if Path(override).is_file() else None
    for candidate in _PIPER_BINARY_CANDIDATES:
        p = Path(candidate)
        if p.is_file() and os.access(str(p), os.X_OK):
            return str(p)
        if "/" not in candidate:
            found = shutil.which(candidate)
            if found:
                return found
    return None


def _find_piper_model(override: str | None = None) -> Path | None:
    if override:
        p = Path(override)
        return p if p.exists() else None
    for candidate in _PIPER_MODEL_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


class PiperTTS:
    """Offline TTS using the Piper binary (aarch64 + x86_64). Returns WAV audio."""

    AUDIO_CONTENT_TYPE: str = "audio/wav"

    def __init__(
        self,
        binary: str | None = None,
        model: str | None = None,
    ) -> None:
        resolved_binary = _find_piper_binary(binary)
        if not resolved_binary:
            raise RuntimeError(
                "Piper binary bulunamadı. "
                "scripts/setup_jetson_piper.sh ile kurun veya binary= belirtin."
            )
        resolved_model = _find_piper_model(model)
        if not resolved_model:
            raise RuntimeError(
                "Piper Türkçe modeli bulunamadı. "
                "robot_waiter_ai/models/tr_TR-fahrettin-medium.onnx bekleniyor."
            )
        self._binary = resolved_binary
        self._model = resolved_model
        logger.debug("PiperTTS: binary=%s  model=%s", self._binary, self._model)

    def _validate_text(self, text: str) -> str:
        stripped = text.strip()
        if not stripped:
            raise ValueError("Metin boş olamaz.")
        return stripped

    def _run_piper_blocking(self, text: str) -> bytes:
        fd, tmp = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            result = subprocess.run(
                [self._binary, "--model", str(self._model),
                 "--output_file", tmp, "--quiet"],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"piper exited {result.returncode}: "
                    f"{result.stderr.decode(errors='replace')[:200]}"
                )
            return Path(tmp).read_bytes()
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    async def synthesize(self, text: str) -> bytes:
        import asyncio
        stripped = self._validate_text(text)
        return await asyncio.to_thread(self._run_piper_blocking, stripped)

    async def synthesize_streaming(self, text: str) -> AsyncIterator[bytes]:
        wav_bytes = await self.synthesize(text)
        yield wav_bytes


# ---------------------------------------------------------------------------
# Smoke test — run with:  python -m robot_waiter_ai.speech.tts
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio
    import sys
    from pathlib import Path

    logging.basicConfig(level=logging.DEBUG)

    async def _smoke_test() -> None:
        tts = TextToSpeech()

        # Check voices list — no network call.
        voices = TextToSpeech.available_turkish_voices()
        assert voices == ["tr-TR-EmelNeural", "tr-TR-AhmetNeural"], (
            f"Unexpected voices: {voices}"
        )
        logger.info("available_turkish_voices() OK: %s", voices)

        # ValueError on empty text.
        try:
            await tts.synthesize("   ")
            assert False, "Expected ValueError for whitespace input"
        except ValueError as exc:
            logger.info("Empty-text guard OK: %s", exc)

        # Full synthesis — requires internet + edge-tts installed.
        test_text = "Merhaba, hoş geldiniz."
        logger.info("Synthesising: %r", test_text)
        audio_bytes = await tts.synthesize(test_text)

        assert len(audio_bytes) > 0, "synthesize() returned empty bytes"
        logger.info("synthesize() OK: %d bytes received", len(audio_bytes))

        # Save to disk so you can listen to verify quality.
        out_path = Path("/tmp/tts_smoke_test.mp3")
        out_path.write_bytes(audio_bytes)
        print(f"Saved: {out_path}  ({len(audio_bytes):,} bytes)")

        # Streaming sanity-check — collect chunks and verify total > 0.
        chunks = []
        async for chunk in tts.synthesize_streaming(test_text):
            chunks.append(chunk)
        assert chunks, "synthesize_streaming() yielded no chunks"
        assert sum(len(c) for c in chunks) > 0, (
            "Streaming produced no audio data"
        )
        logger.info(
            "synthesize_streaming() OK: %d chunks, %d total bytes",
            len(chunks),
            sum(len(c) for c in chunks),
        )

        logger.info("Smoke test passed.")

    asyncio.run(_smoke_test())
    sys.exit(0)
