from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from robot_waiter_ai.demo import voice_web_demo
from robot_waiter_ai.demo.voice_web_demo import build_chat_response, handle_chat_request


class DummyQwenBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def generate_reply(self, user_message: str, menu_context: str | None = None) -> str:
        self.calls.append((user_message, menu_context))
        return "Deneme yaniti"


def test_deterministic_backend_is_default() -> None:
    response = build_chat_response("Ayran sipariş etmek istiyorum.")

    assert response["intent"] == "add_item"
    assert "Ayran" in response["response"]


def test_qwen_backend_is_opt_in() -> None:
    backend = DummyQwenBackend()
    response = build_chat_response(
        "Merhaba",
        backend="qwen",
        qwen_backend=backend,
        menu_context="Menü: Ayran (45.00 TL).",
    )

    assert response["response"] == "Deneme yaniti"
    assert response["intent"] == "llm_response"
    assert backend.calls == [("Merhaba", "Menü: Ayran (45.00 TL).")]


def test_chat_request_returns_compatible_json_shape_in_qwen_mode() -> None:
    backend = DummyQwenBackend()

    status_code, payload = handle_chat_request(
        json.dumps({"message": "2 ayran istiyorum"}).encode("utf-8"),
        backend="qwen",
        qwen_backend=backend,
        menu_context="Menü: Ayran (45.00 TL).",
    )

    assert status_code == 200
    assert payload["response"] == "Deneme yaniti"


def test_run_server_does_not_load_qwen_when_backend_is_default(monkeypatch) -> None:
    calls: list[str] = []

    import uvicorn as _uvicorn
    monkeypatch.setattr(_uvicorn, "run", lambda *_a, **_kw: None)
    monkeypatch.setattr(voice_web_demo, "_load_qwen_backend", lambda *_args, **_kwargs: calls.append("qwen"))
    monkeypatch.setattr(voice_web_demo, "build_menu_context", lambda: calls.append("context"))

    voice_web_demo.run_server(port=8005)

    assert calls == []


def test_run_server_passes_base_model_path_and_no_4bit_to_qwen_loader(monkeypatch) -> None:
    calls: list[tuple[str, str, bool]] = []

    import uvicorn as _uvicorn
    monkeypatch.setattr(_uvicorn, "run", lambda *_a, **_kw: None)
    monkeypatch.setattr(voice_web_demo, "build_menu_context", lambda: "menu")
    monkeypatch.setattr(
        voice_web_demo,
        "_load_qwen_backend",
        lambda adapter_path, base_model_path, load_in_4bit: calls.append(
            (str(adapter_path), base_model_path, load_in_4bit)
        ) or DummyQwenBackend(),
    )

    voice_web_demo.run_server(
        port=8006,
        backend="qwen",
        qwen_base_model_path="robot_waiter_ai/models/Qwen2.5-3B-Instruct",
        qwen_adapter_path="robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora",
        load_in_4bit=False,
    )

    assert calls == [
        (
            str(Path("robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora")),
            "robot_waiter_ai/models/Qwen2.5-3B-Instruct",
            False,
        )
    ]


def test_parse_args_keeps_deterministic_default_and_qwen_opt_in(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["voice_web_demo"])

    args = voice_web_demo._parse_args()

    assert isinstance(args, Namespace)
    assert args.backend == "deterministic"
    assert args.no_4bit is False


def test_parse_args_accepts_qwen_base_model_path_and_no_4bit(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "voice_web_demo",
            "--backend",
            "qwen",
            "--qwen-base-model-path",
            "robot_waiter_ai/models/Qwen2.5-3B-Instruct",
            "--no-4bit",
        ],
    )

    args = voice_web_demo._parse_args()

    assert args.backend == "qwen"
    assert args.qwen_base_model_path == "robot_waiter_ai/models/Qwen2.5-3B-Instruct"
    assert args.no_4bit is True
