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
            "--device",
            "cuda",
        ],
    )

    args = _parse_args()

    assert args.base_model_path == "robot_waiter_ai/models/Qwen2.5-3B-Instruct"
    assert args.no_4bit is True
    assert args.device == "cuda"


def test_runtime_metadata_reports_required_fields() -> None:
    backend = object.__new__(QwenLoraWaiterBackend)
    backend.backend_name = "qwen_lora_waiter"
    backend.device_used = "cuda:0"
    backend.torch_cuda_available = True
    backend.base_model_source = "robot_waiter_ai/models/Qwen2.5-3B-Instruct"
    backend.adapter_path = Path("robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora")
    backend.runtime_torch_dtype = "float16"
    backend.load_in_4bit_effective = True
    backend.load_in_4bit_disabled_reason = None

    metadata = backend.runtime_metadata()

    assert metadata["backend_name"] == "qwen_lora_waiter"
    assert metadata["device_used"] == "cuda:0"
    assert metadata["torch_cuda_available"] is True
    assert metadata["model_path"] == "robot_waiter_ai/models/Qwen2.5-3B-Instruct"
    assert metadata["adapter_path"].endswith("qwen25_3b_waiter_v1_1_lora")
    assert metadata["load_in_4bit_disabled_reason"] is None


def test_default_4bit_disable_reason_is_set_on_windows_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Windows")

    reason = QwenLoraWaiterBackend._default_4bit_disable_reason(use_cuda=True)

    assert reason is not None
    assert "Windows" in reason


def test_default_4bit_disable_reason_is_not_set_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Linux")

    reason = QwenLoraWaiterBackend._default_4bit_disable_reason(use_cuda=True)

    assert reason is None


def test_qwen_prompt_includes_conversation_history_in_order() -> None:
    backend = object.__new__(QwenLoraWaiterBackend)

    messages = backend._build_messages(
        "Toplam ne kadar oldu?",
        conversation_history=[
            {"role": "user", "content": "2 iskender yaz."},
            {"role": "assistant", "content": "2 İskender ekledim."},
        ],
    )

    assert messages[1] == {"role": "user", "content": "2 iskender yaz."}
    assert messages[2] == {"role": "assistant", "content": "2 İskender ekledim."}
    assert messages[3] == {"role": "user", "content": "Toplam ne kadar oldu?"}


def test_qwen_prompt_accepts_system_prompt_override() -> None:
    backend = object.__new__(QwenLoraWaiterBackend)

    messages = backend._build_messages(
        "Merhaba",
        menu_context="Bu baglam gormezden gelinmeli.",
        system_prompt_override="Ozel sistem promptu",
    )

    assert messages[0]["content"] == "Ozel sistem promptu"
