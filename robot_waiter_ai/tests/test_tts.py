"""
Unit tests for speech/tts.py.

All tests mock edge_tts.Communicate so no network access or real edge-tts
installation is required.  Tests run offline in CI and on hardware-free dev
machines.
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_communicate(chunks: list[dict]):
    """Return a Communicate-like *class* whose stream() yields the given chunks.

    The returned class captures ``chunks`` via closure, so each call to
    ``stream()`` replays the same sequence.
    """
    class FakeCommunicate:
        def __init__(self, text, voice, rate="+0%", volume="+0%"):
            self.text = text
            self.voice = voice
            self.rate = rate
            self.volume = volume

        async def stream(self):
            for chunk in chunks:
                yield chunk

    return FakeCommunicate


def _make_fake_edge_tts(chunks: list[dict]):
    """Return a fake edge_tts module whose Communicate class replays ``chunks``."""
    fake_module = MagicMock()
    fake_module.Communicate = _make_fake_communicate(chunks)
    return fake_module


# ---------------------------------------------------------------------------
# available_turkish_voices
# ---------------------------------------------------------------------------

def test_available_turkish_voices_returns_both_voices():
    from robot_waiter_ai.speech.tts import TextToSpeech

    voices = TextToSpeech.available_turkish_voices()

    assert voices == ["tr-TR-EmelNeural", "tr-TR-AhmetNeural"]


def test_available_turkish_voices_returns_a_copy():
    from robot_waiter_ai.speech.tts import TextToSpeech

    v1 = TextToSpeech.available_turkish_voices()
    v2 = TextToSpeech.available_turkish_voices()

    assert v1 == v2
    assert v1 is not v2, "should return a new list each time"


# ---------------------------------------------------------------------------
# synthesize — happy path
# ---------------------------------------------------------------------------

def test_synthesize_concatenates_audio_chunks():
    from robot_waiter_ai.speech.tts import TextToSpeech

    tts = TextToSpeech()
    chunks = [
        {"type": "audio", "data": b"chunk1"},
        {"type": "audio", "data": b"chunk2"},
        {"type": "audio", "data": b"chunk3"},
    ]
    with patch.object(tts, "_import_edge_tts", return_value=_make_fake_edge_tts(chunks)):
        result = asyncio.run(tts.synthesize("Merhaba"))

    assert result == b"chunk1chunk2chunk3"


def test_synthesize_ignores_non_audio_chunks():
    from robot_waiter_ai.speech.tts import TextToSpeech

    tts = TextToSpeech()
    chunks = [
        {"type": "metadata", "data": b"should_be_ignored"},
        {"type": "audio", "data": b"audio_only"},
        {"type": "WordBoundary", "offset": 0},
    ]
    with patch.object(tts, "_import_edge_tts", return_value=_make_fake_edge_tts(chunks)):
        result = asyncio.run(tts.synthesize("Test"))

    assert result == b"audio_only"


def test_synthesize_returns_empty_bytes_when_no_audio_chunks():
    from robot_waiter_ai.speech.tts import TextToSpeech

    tts = TextToSpeech()
    chunks = [{"type": "metadata"}]
    with patch.object(tts, "_import_edge_tts", return_value=_make_fake_edge_tts(chunks)):
        result = asyncio.run(tts.synthesize("Test"))

    assert result == b""


def test_synthesize_strips_surrounding_whitespace_before_synthesis():
    from robot_waiter_ai.speech.tts import TextToSpeech

    tts = TextToSpeech()
    received_texts: list[str] = []

    class CapturingCommunicate:
        def __init__(self, text, voice, rate="+0%", volume="+0%"):
            received_texts.append(text)

        async def stream(self):
            yield {"type": "audio", "data": b"x"}

    fake_edge = MagicMock()
    fake_edge.Communicate = CapturingCommunicate
    with patch.object(tts, "_import_edge_tts", return_value=fake_edge):
        asyncio.run(tts.synthesize("  Merhaba  "))

    assert received_texts == ["Merhaba"]


# ---------------------------------------------------------------------------
# synthesize — voice / rate / volume forwarded correctly
# ---------------------------------------------------------------------------

def test_synthesize_passes_voice_rate_volume_to_communicate():
    from robot_waiter_ai.speech.tts import TextToSpeech

    tts = TextToSpeech(voice="tr-TR-AhmetNeural", rate="+10%", volume="-5%")
    received: dict[str, str] = {}

    class CapturingCommunicate:
        def __init__(self, text, voice, rate="+0%", volume="+0%"):
            received.update({"voice": voice, "rate": rate, "volume": volume})

        async def stream(self):
            yield {"type": "audio", "data": b"x"}

    fake_edge = MagicMock()
    fake_edge.Communicate = CapturingCommunicate
    with patch.object(tts, "_import_edge_tts", return_value=fake_edge):
        asyncio.run(tts.synthesize("Test"))

    assert received["voice"] == "tr-TR-AhmetNeural"
    assert received["rate"] == "+10%"
    assert received["volume"] == "-5%"


def test_synthesize_default_voice_is_emel():
    from robot_waiter_ai.speech.tts import TextToSpeech, DEFAULT_VOICE

    tts = TextToSpeech()
    received: dict[str, str] = {}

    class CapturingCommunicate:
        def __init__(self, text, voice, rate="+0%", volume="+0%"):
            received["voice"] = voice

        async def stream(self):
            yield {"type": "audio", "data": b"x"}

    fake_edge = MagicMock()
    fake_edge.Communicate = CapturingCommunicate
    with patch.object(tts, "_import_edge_tts", return_value=fake_edge):
        asyncio.run(tts.synthesize("Test"))

    assert received["voice"] == DEFAULT_VOICE
    assert received["voice"] == "tr-TR-EmelNeural"


# ---------------------------------------------------------------------------
# synthesize — error cases
# ---------------------------------------------------------------------------

def test_synthesize_raises_value_error_on_empty_string():
    from robot_waiter_ai.speech.tts import TextToSpeech

    tts = TextToSpeech()

    with pytest.raises(ValueError, match="boş"):
        asyncio.run(tts.synthesize(""))


def test_synthesize_raises_value_error_on_whitespace_only():
    from robot_waiter_ai.speech.tts import TextToSpeech

    tts = TextToSpeech()

    with pytest.raises(ValueError, match="boş"):
        asyncio.run(tts.synthesize("   \t\n"))


def test_synthesize_raises_runtime_error_when_edge_tts_not_installed():
    from robot_waiter_ai.speech.tts import TextToSpeech

    tts = TextToSpeech()

    with patch.object(
        tts,
        "_import_edge_tts",
        side_effect=RuntimeError("edge-tts gerekli: pip install edge-tts"),
    ):
        with pytest.raises(RuntimeError, match="edge-tts"):
            asyncio.run(tts.synthesize("Merhaba"))


# ---------------------------------------------------------------------------
# synthesize_streaming — happy path
# ---------------------------------------------------------------------------

def test_synthesize_streaming_yields_audio_chunks_in_order():
    from robot_waiter_ai.speech.tts import TextToSpeech

    tts = TextToSpeech()
    chunks = [
        {"type": "audio", "data": b"stream1"},
        {"type": "metadata"},
        {"type": "audio", "data": b"stream2"},
    ]
    with patch.object(tts, "_import_edge_tts", return_value=_make_fake_edge_tts(chunks)):
        async def collect():
            result = []
            async for chunk in tts.synthesize_streaming("Merhaba"):
                result.append(chunk)
            return result

        collected = asyncio.run(collect())

    assert collected == [b"stream1", b"stream2"]


def test_synthesize_streaming_yields_nothing_for_non_audio_chunks():
    from robot_waiter_ai.speech.tts import TextToSpeech

    tts = TextToSpeech()
    chunks = [{"type": "metadata"}, {"type": "WordBoundary"}]
    with patch.object(tts, "_import_edge_tts", return_value=_make_fake_edge_tts(chunks)):
        async def collect():
            result = []
            async for chunk in tts.synthesize_streaming("Test"):
                result.append(chunk)
            return result

        collected = asyncio.run(collect())

    assert collected == []


# ---------------------------------------------------------------------------
# synthesize_streaming — error cases
# ---------------------------------------------------------------------------

def test_synthesize_streaming_raises_value_error_on_empty_text():
    from robot_waiter_ai.speech.tts import TextToSpeech

    tts = TextToSpeech()

    with pytest.raises(ValueError, match="boş"):
        async def consume():
            async for _ in tts.synthesize_streaming(""):
                pass

        asyncio.run(consume())


def test_synthesize_streaming_raises_value_error_on_whitespace_only():
    from robot_waiter_ai.speech.tts import TextToSpeech

    tts = TextToSpeech()

    with pytest.raises(ValueError, match="boş"):
        async def consume():
            async for _ in tts.synthesize_streaming("   "):
                pass

        asyncio.run(consume())


def test_synthesize_streaming_raises_runtime_error_when_edge_tts_missing():
    from robot_waiter_ai.speech.tts import TextToSpeech

    tts = TextToSpeech()

    with patch.object(
        tts,
        "_import_edge_tts",
        side_effect=RuntimeError("edge-tts gerekli: pip install edge-tts"),
    ):
        with pytest.raises(RuntimeError, match="edge-tts"):
            async def consume():
                async for _ in tts.synthesize_streaming("Merhaba"):
                    pass

            asyncio.run(consume())
