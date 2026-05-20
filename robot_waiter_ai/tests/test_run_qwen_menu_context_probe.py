from __future__ import annotations

import json
from pathlib import Path

import pytest

from robot_waiter_ai.evals.run_qwen_menu_context_probe import _parse_args, run_menu_context_probe


class _FakeBackend:
    def __init__(self, *_args, **_kwargs) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_reply(
        self,
        user_message: str,
        menu_context: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        system_prompt_override: str | None = None,
    ) -> str:
        self.calls.append(
            {
                "user_message": user_message,
                "menu_context": menu_context,
                "conversation_history": conversation_history or [],
                "system_prompt_override": system_prompt_override,
            }
        )
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


def test_run_menu_context_probe_writes_multiturn_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    menu_context_path = tmp_path / "menu.json"
    dialogues_path = tmp_path / "dialogues.jsonl"
    output_path = tmp_path / "outputs.jsonl"

    menu_context_path.write_text(
        json.dumps(
            {
                "restaurant_name": "Garson Bot Bistro",
                "currency": "TL",
                "items": [{"name": "Ayran", "category": "İçecek", "price": 35}],
                "rules": ["Sadece bu menüdeki ürünler hakkında konuş."],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    dialogues_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "dialogue_1",
                        "scenario": "supported_order_with_total",
                        "turns": [{"user": "Merhaba"}, {"user": "1 ayran ekle"}],
                        "expected_observations": ["Ayranı kabul etmeli."],
                        "risk_level": "high",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "id": "dialogue_2",
                        "scenario": "off_topic_rejection",
                        "turns": [{"user": "Bana bir şiir yaz"}],
                        "expected_observations": ["Kibarca reddetmeli."],
                        "risk_level": "medium",
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "robot_waiter_ai.evals.run_qwen_menu_context_probe.QwenLoraWaiterBackend",
        _FakeBackend,
    )
    monkeypatch.setattr(
        "robot_waiter_ai.evals.run_qwen_menu_context_probe._get_torch_cuda_available",
        lambda: True,
    )

    summary = run_menu_context_probe(
        base_model_path="robot_waiter_ai/models/Qwen2.5-3B-Instruct",
        adapter_path="robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora",
        menu_context_path=menu_context_path,
        dialogues_path=dialogues_path,
        output_path=output_path,
        device="cuda",
        limit_dialogues=1,
    )

    assert summary["dialogue_count"] == 1
    assert summary["turn_count"] == 2
    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["dialogue_id"] == "dialogue_1"
    assert rows[1]["turn_index"] == 1
    assert rows[1]["metadata"]["device_used"] == "cuda:0"
    assert rows[1]["metadata"]["base_model_path"] == "robot_waiter_ai/models/Qwen2.5-3B-Instruct"
    assert rows[1]["metadata"]["menu_context_file"] == str(menu_context_path)


def test_run_menu_context_probe_rejects_cuda_when_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    menu_context_path = tmp_path / "menu.json"
    dialogues_path = tmp_path / "dialogues.jsonl"

    menu_context_path.write_text('{"restaurant_name":"x","currency":"TL","items":[],"rules":[]}', encoding="utf-8")
    dialogues_path.write_text(
        json.dumps(
            {
                "id": "dialogue_1",
                "scenario": "supported_order_with_total",
                "turns": [{"user": "Merhaba"}],
                "expected_observations": ["Selam vermeli."],
                "risk_level": "low",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "robot_waiter_ai.evals.run_qwen_menu_context_probe._get_torch_cuda_available",
        lambda: False,
    )

    with pytest.raises(RuntimeError, match="CUDA device was requested"):
        run_menu_context_probe(
            base_model_path="base",
            adapter_path="adapter",
            menu_context_path=menu_context_path,
            dialogues_path=dialogues_path,
            output_path=tmp_path / "outputs.jsonl",
            device="cuda",
        )


def test_parse_args_supports_probe_specific_flags() -> None:
    args = _parse_args(
        [
            "--base-model-path",
            "base",
            "--adapter-path",
            "adapter",
            "--menu-context-path",
            "menu.json",
            "--dialogues-path",
            "dialogues.jsonl",
            "--output-path",
            "outputs.jsonl",
            "--device",
            "cpu",
            "--limit-dialogues",
            "3",
            "--no-4bit",
        ]
    )

    assert args.base_model_path == "base"
    assert args.adapter_path == "adapter"
    assert args.menu_context_path == "menu.json"
    assert args.dialogues_path == "dialogues.jsonl"
    assert args.output_path == "outputs.jsonl"
    assert args.device == "cpu"
    assert args.limit_dialogues == 3
    assert args.no_4bit is True
