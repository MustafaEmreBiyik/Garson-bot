from __future__ import annotations

import json
from pathlib import Path

import pytest

from robot_waiter_ai.evals.run_qwen_quality_audit import _parse_args, run_audit


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
            }
        )
        if "fiyat" in user_message.lower():
            return "fiyat 100 TL"
        return f"yanit: {user_message}"

    def runtime_metadata(self) -> dict[str, object]:
        return {
            "backend_name": "qwen_lora_waiter",
            "device_used": "cuda:0",
            "torch_cuda_available": True,
            "load_in_4bit": True,
        }


def test_run_audit_dry_run(tmp_path: Path) -> None:
    eval_path = tmp_path / "eval.jsonl"
    out_path = tmp_path / "out.jsonl"

    eval_path.write_text(
        json.dumps(
            {
                "id": "1",
                "category": "test",
                "user_message": "merhaba",
                "must_include": ["yanit"]
            }
        ) + "\n",
        encoding="utf-8"
    )

    summary = run_audit(
        eval_file=eval_path,
        output_file=out_path,
        dry_run=True
    )

    assert summary["total_records"] == 1
    assert summary["passed"] == 1
    assert summary["dry_run"] is True
    assert out_path.exists()


def test_run_audit_real_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    eval_path = tmp_path / "eval.jsonl"
    out_path = tmp_path / "out.jsonl"

    eval_path.write_text(
        json.dumps(
            {
                "id": "1",
                "category": "test",
                "user_message": "fiyat nedir?",
                "must_include": ["100"]
            }
        ) + "\n" + json.dumps(
            {
                "id": "2",
                "category": "test2",
                "user_message": "fiyat nedir?",
                "must_include": ["999"]
            }
        ) + "\n",
        encoding="utf-8"
    )

    monkeypatch.setattr(
        "robot_waiter_ai.evals.run_qwen_quality_audit.QwenLoraWaiterBackend",
        _FakeBackend,
    )

    summary = run_audit(
        eval_file=eval_path,
        output_file=out_path,
        dry_run=False
    )

    assert summary["total_records"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["dry_run"] is False
    assert out_path.exists()
    
    rows = [json.loads(x) for x in out_path.read_text("utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["passed"] is True
    assert rows[1]["passed"] is False


def test_parse_args_supports_flags() -> None:
    args = _parse_args(
        [
            "--eval-file",
            "eval.jsonl",
            "--output-file",
            "out.jsonl",
            "--dry-run",
            "--no-4bit",
            "--device",
            "cpu"
        ]
    )
    
    assert args.eval_file == "eval.jsonl"
    assert args.output_file == "out.jsonl"
    assert args.dry_run is True
    assert args.no_4bit is True
    assert args.device == "cpu"
