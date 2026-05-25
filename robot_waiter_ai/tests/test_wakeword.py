"""
Unit tests for speech/mic.py — wake word detection.

All tests mock sounddevice and openwakeword so no hardware or extra
dependencies are required.  Tests run offline in CI and on hardware-free
dev machines.
"""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import MagicMock

import numpy as np
import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wakeword_model_class(model_name: str, scores: list[float]):
    """Return a fake openWakeWord Model class that replays the given scores.

    Each call to ``predict()`` consumes the next score from *scores*.
    Once exhausted it returns 0.0 indefinitely.
    """
    score_iter = iter(scores)

    class FakeWakeWordModel:
        def __init__(self, wakeword_models=None, inference_framework=None, **kwargs):
            self.models = {model_name: None}

        def predict(self, audio_chunk):
            try:
                score = next(score_iter)
            except StopIteration:
                score = 0.0
            return {model_name: score}

    return FakeWakeWordModel


def _make_fake_sd_with_stream(scores_per_read: list[float] | None = None):
    """Return a (fake_sd, read_log) pair.

    fake_sd.InputStream acts as a context manager whose read() appends each
    call to *read_log* and returns a zero-filled numpy array.

    *scores_per_read* is not consumed here — it's used by the model mock.
    """
    read_log: list[int] = []  # stores the `frames` argument of each read()

    class FakeInputStream:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, frames: int):
            read_log.append(frames)
            return np.zeros((frames, 1), dtype="int16"), False

    fake_sd = MagicMock()
    fake_sd.InputStream.return_value = FakeInputStream()
    return fake_sd, read_log


def _fake_oww_module(model_class) -> MagicMock:
    """Return a fake openwakeword.model module with Model set to *model_class*."""
    m = MagicMock()
    m.Model = model_class
    return m


# ---------------------------------------------------------------------------
# listen_for_wakeword — guard checks (no hardware needed)
# ---------------------------------------------------------------------------

def test_listen_for_wakeword_raises_when_mic_not_opened():
    """open() must be called before listen_for_wakeword()."""
    from robot_waiter_ai.speech.mic import ReSpeakerMic

    mic = ReSpeakerMic()
    # _device_index is None — open() was never called

    with pytest.raises(RuntimeError, match="açılmamış"):
        asyncio.run(mic.listen_for_wakeword())


def test_listen_for_wakeword_raises_when_openwakeword_not_installed():
    """RuntimeError with helpful install hint when openwakeword is missing."""
    from robot_waiter_ai.speech.mic import ReSpeakerMic

    mic = ReSpeakerMic()
    mic._device_index = 0  # simulate open()

    fake_sd, _ = _make_fake_sd_with_stream()

    patched_modules = {
        "sounddevice": fake_sd,
        "openwakeword": None,       # causes ImportError on `from openwakeword...`
        "openwakeword.model": None,
    }
    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "sounddevice", fake_sd)
        mp.setitem(sys.modules, "openwakeword", None)
        mp.setitem(sys.modules, "openwakeword.model", None)

        with pytest.raises(RuntimeError, match="openwakeword"):
            asyncio.run(mic.listen_for_wakeword())


# ---------------------------------------------------------------------------
# listen_for_wakeword — detection
# ---------------------------------------------------------------------------

def test_listen_for_wakeword_returns_after_detection():
    """Returns once the model score crosses the threshold."""
    from robot_waiter_ai.speech.mic import ReSpeakerMic, WAKEWORD_CHUNK_SAMPLES

    mic = ReSpeakerMic()
    mic._device_index = 0

    # Reads 1 & 2 → below threshold; read 3 → detected
    ModelClass = _make_wakeword_model_class("hey_garson", [0.1, 0.2, 0.9])
    fake_sd, read_log = _make_fake_sd_with_stream()

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "sounddevice", fake_sd)
        mp.setitem(sys.modules, "openwakeword", MagicMock())
        mp.setitem(sys.modules, "openwakeword.model", _fake_oww_module(ModelClass))

        asyncio.run(mic.listen_for_wakeword(model_path="hey_garson", threshold=0.5))

    # Exactly 3 reads should have happened before the function returned.
    assert len(read_log) == 3
    # Each read must have requested the correct chunk size.
    assert all(frames == WAKEWORD_CHUNK_SAMPLES for frames in read_log)


def test_listen_for_wakeword_detects_on_first_frame():
    """Immediate detection on the very first audio frame."""
    from robot_waiter_ai.speech.mic import ReSpeakerMic

    mic = ReSpeakerMic()
    mic._device_index = 0

    ModelClass = _make_wakeword_model_class("hey_garson", [1.0])
    fake_sd, read_log = _make_fake_sd_with_stream()

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "sounddevice", fake_sd)
        mp.setitem(sys.modules, "openwakeword", MagicMock())
        mp.setitem(sys.modules, "openwakeword.model", _fake_oww_module(ModelClass))

        asyncio.run(mic.listen_for_wakeword(model_path="hey_garson", threshold=0.5))

    assert len(read_log) == 1


def test_listen_for_wakeword_exact_threshold_triggers_detection():
    """A score exactly equal to threshold should count as detected."""
    from robot_waiter_ai.speech.mic import ReSpeakerMic

    mic = ReSpeakerMic()
    mic._device_index = 0

    ModelClass = _make_wakeword_model_class("hey_garson", [0.0, 0.5])
    fake_sd, read_log = _make_fake_sd_with_stream()

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "sounddevice", fake_sd)
        mp.setitem(sys.modules, "openwakeword", MagicMock())
        mp.setitem(sys.modules, "openwakeword.model", _fake_oww_module(ModelClass))

        asyncio.run(mic.listen_for_wakeword(model_path="hey_garson", threshold=0.5))

    assert len(read_log) == 2


def test_listen_for_wakeword_uses_default_model_path_when_none_passed():
    """When model_path=None the default path is forwarded to the model loader."""
    from robot_waiter_ai.speech.mic import ReSpeakerMic, DEFAULT_WAKEWORD_MODEL_PATH

    mic = ReSpeakerMic()
    mic._device_index = 0

    received_paths: list[list[str]] = []

    class CapturingModel:
        def __init__(self, wakeword_models=None, **kwargs):
            received_paths.append(list(wakeword_models or []))
            self.models = {"hey_garson": None}

        def predict(self, chunk):
            return {"hey_garson": 1.0}  # immediate detection

    fake_sd, _ = _make_fake_sd_with_stream()

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "sounddevice", fake_sd)
        mp.setitem(sys.modules, "openwakeword", MagicMock())
        mp.setitem(sys.modules, "openwakeword.model", _fake_oww_module(CapturingModel))

        asyncio.run(mic.listen_for_wakeword())  # model_path=None → should use default

    assert received_paths == [[DEFAULT_WAKEWORD_MODEL_PATH]]


# ---------------------------------------------------------------------------
# listen_for_wakeword — timeout
# ---------------------------------------------------------------------------

def test_listen_for_wakeword_raises_timeout_error_when_deadline_passes():
    """TimeoutError must be raised if the wake word is not detected in time."""
    from robot_waiter_ai.speech.mic import ReSpeakerMic

    mic = ReSpeakerMic()
    mic._device_index = 0

    # Score always 0.0 — will never detect
    ModelClass = _make_wakeword_model_class("hey_garson", [])

    fake_reads = 0

    class SlowInputStream:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, frames: int):
            nonlocal fake_reads
            fake_reads += 1
            import time; time.sleep(0.005)  # 5 ms per frame — burns through 10 ms timeout fast
            return np.zeros((frames, 1), dtype="int16"), False

    fake_sd = MagicMock()
    fake_sd.InputStream.return_value = SlowInputStream()

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "sounddevice", fake_sd)
        mp.setitem(sys.modules, "openwakeword", MagicMock())
        mp.setitem(sys.modules, "openwakeword.model", _fake_oww_module(ModelClass))

        with pytest.raises(TimeoutError):
            asyncio.run(mic.listen_for_wakeword(
                model_path="hey_garson",
                threshold=0.5,
                timeout=0.015,  # 15 ms — guaranteed to expire
            ))


# ---------------------------------------------------------------------------
# listen_and_capture
# ---------------------------------------------------------------------------

def test_listen_and_capture_raises_when_mic_not_opened():
    """open() must be called before listen_and_capture()."""
    from robot_waiter_ai.speech.mic import ReSpeakerMic

    mic = ReSpeakerMic()

    with pytest.raises(RuntimeError, match="açılmamış"):
        asyncio.run(mic.listen_and_capture())


def test_listen_and_capture_returns_wav_bytes_after_detection():
    """After wake word detection, capture() is called and WAV bytes are returned."""
    from robot_waiter_ai.speech.mic import ReSpeakerMic

    mic = ReSpeakerMic()
    mic._device_index = 0

    # Wake word detected on first frame
    ModelClass = _make_wakeword_model_class("hey_garson", [1.0])
    fake_sd, _ = _make_fake_sd_with_stream()

    # sd.rec() is used by _blocking_capture — return a plausible numpy array
    capture_seconds = 4
    num_frames = int(capture_seconds * mic.sample_rate)
    fake_sd.rec.return_value = np.zeros((num_frames, 1), dtype="int16")

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "sounddevice", fake_sd)
        mp.setitem(sys.modules, "openwakeword", MagicMock())
        mp.setitem(sys.modules, "openwakeword.model", _fake_oww_module(ModelClass))

        wav_bytes = asyncio.run(
            mic.listen_and_capture(model_path="hey_garson", seconds=capture_seconds)
        )

    assert isinstance(wav_bytes, bytes)
    # A valid WAV file starts with the "RIFF" header
    assert wav_bytes[:4] == b"RIFF", "Result should be a valid WAV file"
    # sd.rec was called (i.e., capture() ran after wake word detection)
    assert fake_sd.rec.called
