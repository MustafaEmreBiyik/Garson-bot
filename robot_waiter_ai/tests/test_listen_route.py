"""
tests/test_listen_route.py — Integration tests for POST /listen.

Uses FastAPI TestClient — no real server process or hardware needed.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from robot_waiter_ai.demo.voice_web_demo import HTML_PATH, create_app

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fake dependencies
# ---------------------------------------------------------------------------

class FakeSpeechToText:
    def __init__(self) -> None:
        self.audio_calls: list[bytes] = []

    async def transcribe(self, audio_bytes, use_vad=True, initial_prompt=None):
        self.audio_calls.append(audio_bytes)
        return {
            "text": "Ayran istiyorum",
            "language": "tr",
            "language_probability": 0.99,
            "segments": [],
            "low_confidence": False,
        }


class FakeTextToSpeech:
    async def synthesize(self, _text):
        return b"mp3"


class FakeReSpeakerMic:
    def __init__(self) -> None:
        self.is_capturing = False
        self.capture_calls: list[float | None] = []

    async def capture(self, seconds=None):
        self.capture_calls.append(seconds)
        return b"fake-wav"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_listen_returns_503_when_server_mic_is_disabled():
    app = create_app(
        html_path=HTML_PATH,
        backend="deterministic",
        qwen_backend=None,
        menu_context=None,
        stt=FakeSpeechToText(),
        use_vad=False,
        stt_prompt=None,
        tts=FakeTextToSpeech(),
        mic_enabled=False,
    )
    with TestClient(app) as client:
        resp = client.post("/listen", headers={"Content-Length": "0"})

    assert resp.status_code == 503
    assert resp.json() == {"error": "Mikrofon devre dışı"}


def test_listen_captures_from_mock_respeaker_and_transcribes_wav_bytes():
    stt = FakeSpeechToText()
    mic = FakeReSpeakerMic()
    app = create_app(
        html_path=HTML_PATH,
        backend="deterministic",
        qwen_backend=None,
        menu_context=None,
        stt=stt,
        use_vad=False,
        stt_prompt=None,
        tts=FakeTextToSpeech(),
        mic_enabled=True,
        mic=mic,
        mic_seconds=4,
    )
    with TestClient(app) as client:
        resp = client.post("/listen", headers={"Content-Length": "0"})

    assert resp.status_code == 200
    assert mic.capture_calls == [4]
    assert stt.audio_calls == [b"fake-wav"]
    assert resp.json()["text"] == "Ayran istiyorum"
