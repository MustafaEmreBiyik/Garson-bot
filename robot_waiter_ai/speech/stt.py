"""
speech/stt.py — Faster-Whisper based speech-to-text for the robot waiter.

Design notes
------------
* Uses faster-whisper (CTranslate2 backend) for low-latency transcription.
* VAD is handled by faster-whisper's built-in vad_filter — no external
  silero-vad dependency required.
* transcribe() is fully async: model loading and inference both run in a
  thread pool via asyncio.to_thread so they never block the event loop.
* _load_model() uses a double-checked threading.Lock so the WhisperModel is
  initialised exactly once even when concurrent requests arrive before the
  first transcription completes.
* Language is hardcoded to Turkish ("tr") by default; pass language= explicitly
  to override.
* initial_prompt is capped at _PROMPT_MAX_CHARS characters (~224 Whisper
  tokens), truncated at the last comma so it never cuts mid-word.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_PROMPT_MAX_CHARS: int = 300   # safe cap for Whisper's ~224-token prompt window
_VAD_MIN_SILENCE_MS: int = 500  # ms of silence that triggers a VAD segment boundary


# ---------------------------------------------------------------------------
# SpeechToText
# ---------------------------------------------------------------------------

class SpeechToText:
    """Async wrapper around a faster-whisper WhisperModel.

    Parameters
    ----------
    model_size:
        One of "tiny", "base", "small", "medium", "large-v2", etc.
    device:
        "cpu" or "cuda".
    compute_type:
        Quantisation level, e.g. "int8", "float16", "float32".
    """

    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model: Any = None          # lazy-loaded on first transcribe()
        self._load_lock = threading.Lock()  # guards double-checked init

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        """Load the WhisperModel exactly once, thread-safely (double-checked).

        Safe to call from multiple threads concurrently — only the first
        caller actually constructs the model; all others return immediately
        once the model is ready.
        """
        if self._model is not None:
            return
        with self._load_lock:
            if self._model is not None:  # re-check after acquiring lock
                return
            try:
                from faster_whisper import WhisperModel  # type: ignore

                logger.info(
                    "Loading faster-whisper model '%s' on %s (%s) …",
                    self._model_size,
                    self._device,
                    self._compute_type,
                )
                self._model = WhisperModel(
                    self._model_size,
                    device=self._device,
                    compute_type=self._compute_type,
                )
                logger.info("faster-whisper model loaded.")
            except ImportError as exc:
                raise RuntimeError(
                    "faster-whisper is not installed. "
                    "Run: pip install faster-whisper"
                ) from exc

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @staticmethod
    def build_initial_prompt(names: list[str]) -> str:
        """Build a Whisper initial_prompt from a list of proper nouns.

        The prompt helps Whisper recognise domain-specific words (menu items,
        staff names, etc.).  It is capped at _PROMPT_MAX_CHARS characters and
        truncated at the last comma so it never cuts a word in half.

        Parameters
        ----------
        names:
            Arbitrary strings to embed in the prompt (menu items, aliases, …).

        Returns
        -------
        str
            Comma-separated, deduplicated, alphabetically sorted, ≤_PROMPT_MAX_CHARS chars,
            never cut mid-word.
        """
        prompt_str = ", ".join(sorted(set(names)))
        if len(prompt_str) <= _PROMPT_MAX_CHARS:
            return prompt_str
        truncated = prompt_str[:_PROMPT_MAX_CHARS]
        last_comma = truncated.rfind(",")
        return truncated[:last_comma] if last_comma != -1 else truncated

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        language: str = "tr",
        initial_prompt: str | None = None,
        use_vad: bool = True,
    ) -> dict:
        """Transcribe raw audio bytes and return a structured result dict.

        Parameters
        ----------
        audio_bytes:
            Raw audio data (WAV, MP3, WebM, etc. — any format ffmpeg
            understands).  Pass empty bytes to get a fast no-op response.
        language:
            BCP-47 language code.  Defaults to "tr" (Turkish).
        initial_prompt:
            Optional prompt string to bias recognition vocabulary.
            Capped at _PROMPT_MAX_CHARS characters internally.
        use_vad:
            When True (default) faster-whisper's built-in VAD filter is
            enabled to skip silent regions.

        Returns
        -------
        dict with keys:
            text                 – full transcript string
            segments             – list of {start, end, text} dicts
            language             – detected language code
            language_probability – confidence of language detection (0–1)
            low_confidence       – True only when the empty-bytes fast path fires
        """
        # Fast path — empty audio, skip model entirely.
        if not audio_bytes:
            return {
                "text": "",
                "segments": [],
                "language": language,
                "language_probability": 0.0,
                "low_confidence": True,
            }

        # Model loading is blocking (downloads weights, allocates memory).
        # Run it in a thread so the event loop stays responsive.
        await asyncio.to_thread(self._load_model)

        # Cap prompt length so it never exceeds Whisper's token budget.
        if initial_prompt and len(initial_prompt) > _PROMPT_MAX_CHARS:
            initial_prompt = initial_prompt[:_PROMPT_MAX_CHARS]

        # Write audio bytes to a temporary file so faster-whisper can
        # decode them via ffmpeg.
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            result = await self._transcribe_in_thread(
                tmp_path=tmp_path,
                language=language,
                initial_prompt=initial_prompt,
                vad_enabled=use_vad,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        return result

    async def _transcribe_in_thread(
        self,
        tmp_path: str,
        language: str,
        initial_prompt: str | None,
        vad_enabled: bool,
    ) -> dict:
        """Run blocking faster-whisper inference inside a thread pool thread.

        The generator returned by WhisperModel.transcribe() is lazy — it must
        be fully consumed inside the same thread where it was created, before
        returning to the event loop.
        """

        def _run_transcribe() -> tuple[list, Any]:
            segs_gen, info = self._model.transcribe(
                tmp_path,
                language=language,
                initial_prompt=initial_prompt,
                vad_filter=vad_enabled,
                vad_parameters={"min_silence_duration_ms": _VAD_MIN_SILENCE_MS},
                word_timestamps=False,
            )
            # Consume the generator fully inside the worker thread.
            segs = list(segs_gen)
            return segs, info

        segs, info = await asyncio.to_thread(_run_transcribe)

        segments: list[dict] = []
        texts: list[str] = []
        for s in segs:
            segments.append({"start": s.start, "end": s.end, "text": s.text})
            texts.append(s.text)

        return {
            "text": " ".join(texts).strip(),
            "segments": segments,
            "language": info.language,
            "language_probability": info.language_probability,
            "low_confidence": False,
        }


# ---------------------------------------------------------------------------
# Smoke test — run with:  python -m robot_waiter_ai.speech.stt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)

    async def _smoke_test() -> None:
        stt = SpeechToText(model_size="tiny", device="cpu", compute_type="int8")

        # build_initial_prompt: deduplication + sort + cap + no mid-word cut
        prompt = SpeechToText.build_initial_prompt(
            ["Ayran", "Döner", "Ayran", "Baklava"] * 30  # long list → tests cap
        )
        assert len(prompt) <= _PROMPT_MAX_CHARS, f"Prompt too long: {len(prompt)}"
        assert not prompt.endswith(","), f"Prompt ends with comma: {prompt!r}"
        logger.info("initial_prompt (%d chars): %s", len(prompt), prompt)

        # Empty bytes → fast path fires without loading the model.
        result = await stt.transcribe(b"", initial_prompt="")
        required_keys = {"text", "segments", "language", "language_probability", "low_confidence"}
        missing = required_keys - set(result.keys())
        assert not missing, f"Result dict missing keys: {missing}"
        assert result["low_confidence"] is True, "Expected low_confidence=True for empty input"
        assert result["text"] == "", f"Expected empty text, got: {result['text']!r}"
        logger.info("Empty-bytes fast path OK: %s", result)

        logger.info("Smoke test passed.")

    asyncio.run(_smoke_test())
    sys.exit(0)
