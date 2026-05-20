from __future__ import annotations

import json
from pathlib import Path

from robot_waiter_ai.evals.run_qwen_waiter_feature_probe import _parse_args, run_feature_probe


class _FakeBackend:
    def __init__(self, *_args, **_kwargs) -> None:
        self.calls: list[str] = []

    def generate_reply(self, user_message: str, menu_context: str | None = None) -> str:
        self.calls.append(user_message)
        assert menu_context == "test menu context"
        return f"yanit:{user_message}"

    def runtime_metadata(self) -> dict[str, object]:
        return {
            "backend_name": "qwen_lora_waiter",
            "device_used": "cuda:0",
            "torch_cuda_available": True,
            "model_path": "robot_waiter_ai/models/Qwen2.5-3B-Instruct",
            "adapter_path": "robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora",
            "torch_dtype": "float16",
            "load_in_4bit": True,
        }


def test_run_feature_probe_writes_required_metadata(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "probe.jsonl"

    monkeypatch.setattr(
        "robot_waiter_ai.evals.run_qwen_waiter_feature_probe.QwenLoraWaiterBackend",
        _FakeBackend,
    )
    monkeypatch.setattr(
        "robot_waiter_ai.evals.run_qwen_waiter_feature_probe.build_menu_context",
        lambda: "test menu context",
    )

    summary = run_feature_probe(
        base_model_path="robot_waiter_ai/models/Qwen2.5-3B-Instruct",
        adapter_path="robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora",
        output_path=output_path,
        device="cuda",
    )

    assert summary["device_used"] == "cuda:0"
    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert rows
    assert rows[0]["backend_name"] == "qwen_lora_waiter"
    assert rows[0]["metadata"]["device_used"] == "cuda:0"
    assert rows[0]["metadata"]["torch_cuda_available"] is True
    assert rows[0]["metadata"]["model_path"] == "robot_waiter_ai/models/Qwen2.5-3B-Instruct"
    assert rows[0]["metadata"]["adapter_path"] == "robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora"


def test_parse_args_supports_device_and_output_path() -> None:
    args = _parse_args(
        [
            "--base-model-path",
            "base",
            "--adapter-path",
            "adapter",
            "--output-path",
            "out.jsonl",
            "--device",
            "cpu",
            "--no-4bit",
        ]
    )

    assert args.base_model_path == "base"
    assert args.adapter_path == "adapter"
    assert args.output_path == "out.jsonl"
    assert args.device == "cpu"
    assert args.no_4bit is True
