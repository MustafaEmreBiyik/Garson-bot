"""
speech/mic.py — ReSpeaker Mic Array v2.0 capture for the robot waiter.

Hardware
--------
* ReSpeaker Mic Array v2.0 (Seeed Studio)
* USB: idVendor=0x2886, idProduct=0x0018
* 4 microphones with on-chip beamforming, AEC, DOA (0–359°)
* Channel 0 is the beamformed + AEC-applied output (mono, ready for STT)

Install requirements
--------------------
    pip install sounddevice pyusb numpy
    # Linux only — also install the OS-level backends:
    sudo apt install libusb-1.0-0 libportaudio2

Usage
-----
    from robot_waiter_ai.speech.mic import ReSpeakerMic

    mic = ReSpeakerMic()
    await mic.open()                          # detect device, apply tuning
    print("DOA:", await mic.get_doa())        # direction of arrival 0–359°
    wav_bytes = await mic.capture(seconds=4)  # returns WAV bytes (16-bit, 16kHz, mono)
    await mic.close()

    # Pass wav_bytes directly to SpeechToText.transcribe():
    from robot_waiter_ai.speech.stt import SpeechToText
    stt = SpeechToText()
    result = await stt.transcribe(wav_bytes)
    print(result["text"])

Design notes
------------
* open() / capture() / get_doa() are all async; blocking I/O runs in a thread
  pool via asyncio.to_thread — same discipline as stt.py.
* sounddevice and pyusb are imported lazily inside open() so the module is
  importable even without hardware or the libraries installed.
* is_capturing is set True before capture() enters the thread and reset in a
  finally block, preventing a TTS-playback feedback loop.
* _blocking_capture() uses sd.rec() (pull-based) for a fixed-duration
  recording — straightforward, no ring buffer, matches the stt.py bytes API.
* WAV output is packed in-memory via io.BytesIO + wave; no temp files.
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
import wave
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

RESPEAKER_VENDOR_ID: int = 0x2886
RESPEAKER_PRODUCT_ID: int = 0x0018

DEFAULT_SAMPLE_RATE: int = 16000      # Hz — matches Whisper's expected input
DEFAULT_CAPTURE_SECONDS: float = 4.0  # seconds per capture call
MAX_CAPTURE_SECONDS: float = 30.0     # hard upper bound to prevent hangs

# Wake word constants — openWakeWord
# Place trained "hey_garson" ONNX model at this path, or pass model_path explicitly.
DEFAULT_WAKEWORD_MODEL_PATH: str = "robot_waiter_ai/models/hey_garson.onnx"
DEFAULT_WAKEWORD_THRESHOLD: float = 0.5
_WAKEWORD_CHUNK_MS: int = 80  # 80 ms per inference frame
WAKEWORD_CHUNK_SAMPLES: int = int(_WAKEWORD_CHUNK_MS * DEFAULT_SAMPLE_RATE / 1000)  # = 1280


# ---------------------------------------------------------------------------
# ReSpeakerMic
# ---------------------------------------------------------------------------

class ReSpeakerMic:
    """Async interface to the ReSpeaker Mic Array v2.0.

    Parameters
    ----------
    sample_rate:
        PCM sample rate in Hz.  Defaults to 16 000 (Whisper-compatible).
    capture_seconds:
        Default recording duration used when ``capture()`` is called without
        an explicit ``seconds`` argument.
    max_capture_seconds:
        Hard upper bound on any single recording; prevents accidental hangs.
    """

    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        capture_seconds: float = DEFAULT_CAPTURE_SECONDS,
        max_capture_seconds: float = MAX_CAPTURE_SECONDS,
    ) -> None:
        self.sample_rate = sample_rate
        self.capture_seconds = capture_seconds
        self.max_capture_seconds = max_capture_seconds

        # Set by open(); cleared by close().
        self._device_index: int | None = None
        self._tuning: Any = None

        # Public flag — callers (e.g. TTS playback) should check this before
        # starting audio output to avoid feeding the microphone its own voice.
        self.is_capturing: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def open(self) -> None:
        """Detect the ReSpeaker device and apply DSP tuning parameters.

        Must be called once before ``capture()`` or ``get_doa()``.

        Raises
        ------
        RuntimeError
            If the sounddevice audio device or the USB control device is not
            found, or if the required libraries are not installed.
        """
        # ---- lazy imports (allow module import without hardware/libs) --------
        try:
            import sounddevice as sd  # noqa: F401 — just checking availability
        except ImportError as exc:
            raise RuntimeError(
                "sounddevice gerekli: pip install sounddevice"
            ) from exc

        try:
            import usb.core  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "pyusb gerekli: pip install pyusb"
            ) from exc

        # ---- find sounddevice index -----------------------------------------
        idx = self.find_device_index()
        if idx is None:
            raise RuntimeError(
                "ReSpeaker cihazı bulunamadı. USB bağlantısını kontrol edin."
            )
        self._device_index = idx
        print(f"[mic] ReSpeaker ses cihazı bulundu → sounddevice index {idx}")

        # ---- find USB control device (for Tuning / DOA) ---------------------
        await asyncio.to_thread(self._init_tuning)

        # ---- apply DSP settings ---------------------------------------------
        await asyncio.to_thread(self._apply_tuning)

    async def capture(self, seconds: float | None = None) -> bytes:
        """Record audio and return a WAV byte string.

        Parameters
        ----------
        seconds:
            Recording duration.  Defaults to ``self.capture_seconds``.

        Returns
        -------
        bytes
            A complete WAV file (16-bit PCM, mono, ``self.sample_rate`` Hz)
            suitable for passing directly to ``SpeechToText.transcribe()``.

        Raises
        ------
        ValueError
            If ``seconds`` exceeds ``self.max_capture_seconds``.
        RuntimeError
            If a capture is already in progress, or if ``open()`` has not
            been called yet.
        """
        duration = seconds if seconds is not None else self.capture_seconds

        if duration > self.max_capture_seconds:
            raise ValueError(
                f"Kayıt süresi {self.max_capture_seconds:.0f} saniyeyi aşamaz "
                f"(istenen: {duration:.1f} s)."
            )

        if self._device_index is None:
            raise RuntimeError(
                "Mikrofon açılmamış. Önce await mic.open() çağırın."
            )

        if self.is_capturing:
            raise RuntimeError("Zaten kayıt yapılıyor.")

        self.is_capturing = True
        try:
            wav_bytes = await asyncio.to_thread(self._blocking_capture, duration)
        finally:
            self.is_capturing = False

        return wav_bytes

    async def get_doa(self) -> int:
        """Return the current Direction of Arrival angle (0–359 degrees).

        Raises
        ------
        RuntimeError
            If ``open()`` has not been called yet.
        """
        if self._tuning is None:
            raise RuntimeError(
                "Mikrofon açılmamış. Önce await mic.open() çağırın."
            )
        angle = await asyncio.to_thread(lambda: self._tuning.direction)
        return int(angle)

    async def listen_for_wakeword(
        self,
        model_path: str | None = None,
        *,
        threshold: float = DEFAULT_WAKEWORD_THRESHOLD,
        timeout: float | None = None,
    ) -> None:
        """Stream microphone audio and return when the wake word is detected.

        Uses openWakeWord for on-device inference — no cloud call required.
        Audio is fed to the model in 80 ms frames (1 280 samples @ 16 kHz),
        matching the frame size openWakeWord was trained on.

        Parameters
        ----------
        model_path:
            Path to the ONNX wake word model file.
            Defaults to DEFAULT_WAKEWORD_MODEL_PATH.
            Train a custom "hey garson" model with openWakeWord's training
            pipeline and place it at the default path, or pass the path here.
        threshold:
            Detection confidence threshold in [0, 1].  Default 0.5.
        timeout:
            Maximum seconds to wait for a detection.
            ``None`` (default) means wait indefinitely.

        Raises
        ------
        RuntimeError
            If ``open()`` has not been called, or if openwakeword is not
            installed (``pip install openwakeword``).
        TimeoutError
            If *timeout* elapses before a detection is made.
        """
        if self._device_index is None:
            raise RuntimeError(
                "Mikrofon açılmamış. Önce await mic.open() çağırın."
            )
        resolved_path = model_path or DEFAULT_WAKEWORD_MODEL_PATH
        await asyncio.to_thread(
            self._blocking_listen_for_wakeword,
            resolved_path,
            threshold,
            timeout,
        )

    async def listen_and_capture(
        self,
        model_path: str | None = None,
        *,
        seconds: float | None = None,
        threshold: float = DEFAULT_WAKEWORD_THRESHOLD,
        timeout: float | None = None,
    ) -> bytes:
        """Wait for the wake word, then immediately capture a command utterance.

        Combines :meth:`listen_for_wakeword` and :meth:`capture` into a single
        convenience call.  Pass the returned WAV bytes directly to
        ``SpeechToText.transcribe()``.

        Parameters
        ----------
        model_path:
            Wake word model path.  Defaults to DEFAULT_WAKEWORD_MODEL_PATH.
        seconds:
            Capture duration after the wake word.
            Defaults to ``self.capture_seconds``.
        threshold:
            Wake word detection threshold.  Default 0.5.
        timeout:
            Wake word detection timeout in seconds.  ``None`` = wait forever.

        Returns
        -------
        bytes
            WAV bytes (16-bit PCM, mono, ``self.sample_rate`` Hz) of the
            utterance recorded after the wake word.

        Raises
        ------
        RuntimeError
            If ``open()`` has not been called, or openwakeword is not installed.
        TimeoutError
            If *timeout* elapses without a wake word detection.
        ValueError
            If *seconds* exceeds ``self.max_capture_seconds``.
        """
        await self.listen_for_wakeword(
            model_path,
            threshold=threshold,
            timeout=timeout,
        )
        return await self.capture(seconds=seconds)

    async def close(self) -> None:
        """Release resources.  Safe to call even if already closed."""
        if self._tuning is not None:
            try:
                await asyncio.to_thread(self._tuning.close)
            except Exception:
                pass  # best-effort — USB device may already be gone
        self._tuning = None
        self._device_index = None
        logger.debug("[mic] Kapatıldı.")

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def find_device_index() -> int | None:
        """Search sounddevice for a ReSpeaker input device.

        Searches all devices case-insensitively for "respeaker" in the name.

        Returns
        -------
        int or None
            The sounddevice device index, or ``None`` if not found.
        """
        try:
            import sounddevice as sd
        except ImportError:
            return None

        for i, dev in enumerate(sd.query_devices()):
            if "respeaker" in dev["name"].lower() and dev["max_input_channels"] > 0:
                return i
        return None

    # ------------------------------------------------------------------
    # Internal helpers (blocking — always called via asyncio.to_thread)
    # ------------------------------------------------------------------

    def _init_tuning(self) -> None:
        """Find the USB control device and create the Tuning instance.

        Runs in a worker thread (blocking USB enumeration).
        """
        import usb.core

        from robot_waiter_ai.speech.tuning import Tuning

        dev = usb.core.find(
            idVendor=RESPEAKER_VENDOR_ID,
            idProduct=RESPEAKER_PRODUCT_ID,
        )
        if dev is None:
            raise RuntimeError(
                "ReSpeaker USB cihazı bulunamadı. "
                f"(idVendor=0x{RESPEAKER_VENDOR_ID:04x}, "
                f"idProduct=0x{RESPEAKER_PRODUCT_ID:04x}) "
                "USB bağlantısını ve libusb kurulumunu kontrol edin."
            )
        self._tuning = Tuning(dev)
        print(f"[mic] ReSpeaker USB kontrol cihazı bulundu (versiyon: {self._tuning.version})")

    def _apply_tuning(self) -> None:
        """Write DSP tuning parameters to the device.

        Runs in a worker thread (blocking USB control transfers).

        Settings applied
        ----------------
        AECFREEZEONOFF = 0  — AEC adaptive mode (not frozen; filter keeps updating)
        AGCONOFF       = 1  — Automatic Gain Control ON
        CNIONOFF       = 1  — Comfort Noise Insertion ON (noise suppression)
        """
        settings = {
            "AECFREEZEONOFF": 0,  # AEC unfreeze — let echo canceller adapt
            "AGCONOFF": 1,        # AGC on
            "CNIONOFF": 1,        # noise suppression on
        }
        for name, value in settings.items():
            self._tuning.write(name, value)
            print(f"[mic] Tuning → {name} = {value}")

    def _blocking_listen_for_wakeword(
        self,
        model_path: str,
        threshold: float,
        timeout: float | None,
    ) -> None:
        """Blocking wake word detection loop.  Always run via asyncio.to_thread.

        Streams 80 ms audio frames from the ReSpeaker and feeds each frame to
        the openWakeWord model.  Returns as soon as the model's confidence
        for the target wake word reaches or exceeds *threshold*.

        Parameters
        ----------
        model_path:
            Path to the .onnx model file or an openWakeWord built-in model name.
        threshold:
            Detection confidence threshold in [0, 1].
        timeout:
            Seconds before TimeoutError is raised.  ``None`` = no limit.

        Raises
        ------
        RuntimeError
            If openwakeword is not installed.
        TimeoutError
            If *timeout* elapses without a detection.
        """
        import sounddevice as sd

        try:
            from openwakeword.model import Model as WakeWordModel  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "openwakeword gerekli: pip install openwakeword"
            ) from exc

        model = WakeWordModel(wakeword_models=[model_path], inference_framework="onnx")
        # openWakeWord uses the filename stem (without extension) as the model name.
        model_name = list(model.models.keys())[0]
        logger.info(
            "[mic] Wake word modeli yüklendi: '%s' (eşik: %.2f)", model_name, threshold
        )

        deadline: float | None = (
            time.monotonic() + timeout if timeout is not None else None
        )

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            device=self._device_index,
            blocksize=WAKEWORD_CHUNK_SAMPLES,
        ) as stream:
            while True:
                if deadline is not None and time.monotonic() > deadline:
                    raise TimeoutError(
                        f"Wake word {timeout:.1f} saniye içinde algılanamadı."
                    )

                audio_chunk, _ = stream.read(WAKEWORD_CHUNK_SAMPLES)
                prediction = model.predict(audio_chunk.flatten())
                score = float(prediction.get(model_name, 0.0))

                if score >= threshold:
                    logger.info("[mic] Wake word algılandı (skor: %.3f)", score)
                    return

    def _blocking_capture(self, seconds: float) -> bytes:
        """Record ``seconds`` of audio and return WAV bytes.

        Runs in a worker thread (blocking PortAudio call).

        Parameters
        ----------
        seconds:
            Recording duration in seconds.

        Returns
        -------
        bytes
            In-memory WAV file: 16-bit PCM, mono, ``self.sample_rate`` Hz.
        """
        import sounddevice as sd
        import numpy as np

        num_frames = int(seconds * self.sample_rate)

        logger.debug(
            "[mic] Kayıt başlıyor: %.1f s, %d Hz, device=%s",
            seconds,
            self.sample_rate,
            self._device_index,
        )

        # sd.rec returns a numpy array of shape (num_frames, channels).
        # channels=1 → channel 0, which is the beamformed + AEC output.
        recording: np.ndarray = sd.rec(
            num_frames,
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            device=self._device_index,
            blocking=True,
        )

        logger.debug("[mic] Kayıt tamamlandı: %d frame", recording.shape[0])

        # Flatten to 1-D and pack into a WAV container in memory.
        pcm_data: bytes = recording.flatten().tobytes()

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)          # 16-bit = 2 bytes per sample
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm_data)

        wav_bytes = buf.getvalue()
        logger.debug("[mic] WAV paketi: %d bayt", len(wav_bytes))
        return wav_bytes


# ---------------------------------------------------------------------------
# Smoke test — run with:  python -m robot_waiter_ai.speech.mic
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from pathlib import Path

    logging.basicConfig(level=logging.DEBUG)

    async def smoke() -> None:
        mic = ReSpeakerMic()

        # Static helper — does not need open()
        idx = ReSpeakerMic.find_device_index()
        print(f"find_device_index() → {idx}")

        await mic.open()

        doa = await mic.get_doa()
        print(f"DOA: {doa}°")

        print("Capturing 2 seconds...")
        wav_bytes = await mic.capture(seconds=2)
        print(f"Captured bytes: {len(wav_bytes)}")

        out = Path("/tmp/mic_smoke_test.wav")
        out.write_bytes(wav_bytes)
        print(f"Saved: {out}")

        await mic.close()
        print("Smoke test passed.")

    asyncio.run(smoke())
    sys.exit(0)
