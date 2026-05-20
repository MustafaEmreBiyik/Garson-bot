from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from robot_waiter_ai.demo.voice_web_demo import (
    HTML_PATH,
    build_chat_response,
    handle_chat_request,
    run_server,
)


def test_build_chat_response_uses_deterministic_demo_path():
    response = build_chat_response("Ayran sipariş etmek istiyorum.")

    assert response["message"] == "Ayran sipariş etmek istiyorum."
    assert "Ayran" in response["response"]
    assert response["intent"] == "add_item"


def test_handle_chat_request_rejects_invalid_payload():
    status_code, payload = handle_chat_request(b'{"message": 123}')

    assert status_code == 400
    assert "error" in payload


def test_demo_assets_exist_and_processed_datasets_stay_untouched():
    base_dir = Path(__file__).parent.parent
    processed_paths = [
        base_dir / "datasets/processed/waiter_sft_train.jsonl",
        base_dir / "datasets/processed/waiter_sft_valid.jsonl",
        base_dir / "datasets/processed/grounded_paraphrase_train.jsonl",
        base_dir / "datasets/processed/grounded_paraphrase_valid.jsonl",
    ]
    before_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in processed_paths}

    html = HTML_PATH.read_text(encoding="utf-8")
    assert "SpeechRecognition" in html
    assert "speechSynthesis" in html
    assert "tr-TR" in html

    _ = build_chat_response("Pizza var mı?")

    after_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in processed_paths}
    assert before_hashes == after_hashes


def test_handle_chat_request_returns_json_serializable_payload():
    status_code, payload = handle_chat_request(
        json.dumps({"message": "Bana hava durumunu söyler misiniz?"}).encode("utf-8")
    )

    assert status_code == 200
    assert "yardımcı olamıyorum" in payload["response"]
    assert payload["intent"] == "off_topic"


def test_run_server_prints_friendly_message_when_port_is_unavailable(monkeypatch, capsys):
    class OccupiedPortServer:
        def __init__(self, *_args, **_kwargs):
            raise PermissionError(10013, "Permission denied")

    monkeypatch.setattr("robot_waiter_ai.demo.voice_web_demo.ThreadingHTTPServer", OccupiedPortServer)

    with pytest.raises(PermissionError):
        run_server(port=8000)

    captured = capsys.readouterr()
    assert "Port 8000 is unavailable." in captured.out
    assert "--port 8001" in captured.out
