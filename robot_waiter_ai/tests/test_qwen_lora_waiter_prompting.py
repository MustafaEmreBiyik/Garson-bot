from __future__ import annotations

from pathlib import Path

import pytest

from robot_waiter_ai.inference.qwen_lora_waiter import QwenLoraWaiterBackend, _parse_args


def test_qwen_prompt_includes_do_not_invent_guardrails() -> None:
    backend = object.__new__(QwenLoraWaiterBackend)

    messages = backend._build_messages(
        "2 ayran istiyorum",
        menu_context="İçecek: Ayran (45.00 TL).",
    )

    system_prompt = messages[0]["content"]
    assert "uydurma" in system_prompt
    assert "Yalnızca aşağıda verilen menü ve restoran bağlamını kullan" in system_prompt
    assert "stok veya alerji güvenliği uydurma" in system_prompt


def test_qwen_prompt_rejects_empty_user_message() -> None:
    backend = object.__new__(QwenLoraWaiterBackend)

    try:
        backend._build_messages("   ")
    except ValueError as exc:
        assert "must not be empty" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected ValueError for empty user message")


def test_base_model_path_accepts_existing_local_folder(tmp_path: Path) -> None:
    base_model_dir = tmp_path / "Qwen2.5-3B-Instruct"
    base_model_dir.mkdir()
    (base_model_dir / "config.json").write_text("{}", encoding="utf-8")

    resolved = QwenLoraWaiterBackend._resolve_base_model_source(str(base_model_dir))

    assert resolved == str(base_model_dir)


def test_parse_args_supports_local_base_model_path_and_no_4bit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "qwen_lora_waiter",
            "--adapter-path",
            "robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora",
            "--base-model-path",
            "robot_waiter_ai/models/Qwen2.5-3B-Instruct",
            "--message",
            "2 ayran istiyorum",
            "--no-4bit",
        ],
    )

    args = _parse_args()

    assert args.base_model_path == "robot_waiter_ai/models/Qwen2.5-3B-Instruct"
    assert args.no_4bit is True
