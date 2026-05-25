"""
tests/test_transcribe_route.py — Integration tests for POST /transcribe and GET /tts.

Uses FastAPI TestClient (httpx-backed, synchronous) — no real server process needed.
faster-whisper is NOT required: empty bodies trigger the STT fast path.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from robot_waiter_ai.demo.voice_web_demo import HTML_PATH, create_app
from robot_waiter_ai.speech.stt import SpeechToText
from robot_waiter_ai.speech.tts import TextToSpeech

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Module-scoped fixture — one TestClient shared by all tests in this file
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    app = create_app(
        html_path=HTML_PATH,
        backend="deterministic",
        qwen_backend=None,
        menu_context=None,
        stt=SpeechToText(),
        use_vad=False,
        stt_prompt=None,
        tts=TextToSpeech(),
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_transcribe_empty_body_returns_200_with_empty_text(client):
    """POST /transcribe with Content-Length: 0 must hit the fast path and return 200."""
    resp = client.post(
        "/transcribe",
        content=b"",
        headers={"Content-Type": "audio/webm", "Content-Length": "0"},
    )
    payload = resp.json()

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}. Payload: {payload}"
    assert payload.get("text") == "", f"Expected text='', got: {payload.get('text')!r}"
    assert payload.get("low_confidence") is True


@pytest.mark.integration
def test_transcribe_missing_content_length_returns_400(client):
    """POST /transcribe with no Content-Length header must return 400."""
    # httpx strips Content-Length when we set it explicitly to empty.
    # We pass headers without Content-Length and let the route reject it.
    resp = client.post(
        "/transcribe",
        headers={"Content-Type": "audio/webm", "Content-Length": ""},
    )
    # FastAPI/Starlette parses "" as missing, so our guard returns 400.
    assert resp.status_code == 400
    assert "error" in resp.json()


@pytest.mark.integration
def test_transcribe_oversized_body_returns_413(client):
    """POST /transcribe with body > 10 MB must return 413."""
    eleven_mb = bytes(11 * 1024 * 1024)
    resp = client.post(
        "/transcribe",
        content=eleven_mb,
        headers={"Content-Type": "audio/webm"},
    )
    assert resp.status_code == 413, f"Expected 413, got {resp.status_code}"
    assert "error" in resp.json()


@pytest.mark.integration
def test_transcribe_json_shape(client):
    """POST /transcribe with empty body must return exactly the 5 documented keys."""
    resp = client.post(
        "/transcribe",
        content=b"",
        headers={"Content-Type": "audio/webm", "Content-Length": "0"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    required = {"text", "low_confidence", "language_probability", "segments", "language"}
    assert set(payload.keys()) == required, f"Key mismatch: {set(payload.keys())}"


@pytest.mark.integration
def test_tts_missing_param_returns_400(client):
    """GET /tts with no text param must return 400."""
    resp = client.get("/tts")
    assert resp.status_code == 400
    assert "error" in resp.json()


@pytest.mark.integration
def test_tts_empty_param_returns_400(client):
    """GET /tts?text= (empty value) must return 400."""
    resp = client.get("/tts?text=")
    assert resp.status_code == 400
    assert "error" in resp.json()


@pytest.mark.integration
def test_health_includes_tts_runtime(client):
    """GET /health must return JSON containing runtime_tts == 'edge-tts'."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json().get("runtime_tts") == "edge-tts"
