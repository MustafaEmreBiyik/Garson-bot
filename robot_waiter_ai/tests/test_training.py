"""
Tests for dataset_builder.py and dataset_validator.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from robot_waiter_ai.training.dataset_builder import build, _to_chat_record
from robot_waiter_ai.training.dataset_validator import validate, ALLOWED_INTENTS

_BASE = Path(__file__).resolve().parents[1]
RAW_PATH = _BASE / "datasets" / "raw" / "seed_dialogues.yaml"


def test_seed_file_exists():
    assert RAW_PATH.exists(), "seed_dialogues.yaml must exist"


def test_seed_has_at_least_30_examples():
    data = yaml.safe_load(RAW_PATH.read_text(encoding="utf-8"))
    assert len(data.get("dialogues", [])) >= 30


def test_all_intents_are_allowed():
    data = yaml.safe_load(RAW_PATH.read_text(encoding="utf-8"))
    for ex in data.get("dialogues", []):
        intent = ex.get("expected_intent", "")
        assert intent in ALLOWED_INTENTS, f"Unknown intent in {ex['id']}: {intent}"


def test_no_empty_responses():
    data = yaml.safe_load(RAW_PATH.read_text(encoding="utf-8"))
    for ex in data.get("dialogues", []):
        assert ex.get("assistant_response", "").strip(), f"Empty response in {ex['id']}"


def test_validator_returns_no_errors():
    total, error_count, errors = validate(RAW_PATH)
    assert total >= 30
    assert error_count == 0, f"Validator found errors:\n" + "\n".join(errors)


def test_chat_record_structure():
    example = {
        "id": "test_001",
        "user": "Merhaba",
        "expected_intent": "greeting",
        "expected_entities": {},
        "assistant_response": "Hoş geldiniz!",
    }
    rec = _to_chat_record(example)
    assert "messages" in rec
    assert len(rec["messages"]) == 3
    roles = [m["role"] for m in rec["messages"]]
    assert roles == ["system", "user", "assistant"]
    assert rec["messages"][1]["content"] == "Merhaba"
    assert rec["messages"][2]["content"] == "Hoş geldiniz!"
    assert rec["metadata"]["intent"] == "greeting"


def test_build_creates_jsonl_files(tmp_path):
    out_dir = tmp_path / "processed"
    build(raw_path=RAW_PATH, out_dir=out_dir)

    train_file = out_dir / "waiter_sft_train.jsonl"
    valid_file = out_dir / "waiter_sft_valid.jsonl"
    assert train_file.exists()
    assert valid_file.exists()

    train_lines = train_file.read_text(encoding="utf-8").strip().splitlines()
    valid_lines = valid_file.read_text(encoding="utf-8").strip().splitlines()

    assert len(train_lines) > 0
    assert len(valid_lines) > 0
    data = yaml.safe_load(RAW_PATH.read_text(encoding="utf-8"))
    assert len(train_lines) + len(valid_lines) == len(data["dialogues"])

    for line in train_lines + valid_lines:
        obj = json.loads(line)
        assert "messages" in obj
