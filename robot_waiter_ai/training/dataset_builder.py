"""
dataset_builder.py

Loads datasets/raw/seed_dialogues.yaml and converts each example into
chat-training format for supervised fine-tuning (SFT).

Produces two JSONL files:
  datasets/processed/waiter_sft_train.jsonl
  datasets/processed/waiter_sft_valid.jsonl

Usage (from project root):
  .venv\\Scripts\\python.exe -m robot_waiter_ai.training.dataset_builder
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List

import yaml

_BASE = Path(__file__).resolve().parents[1]
RAW_PATH = _BASE / "datasets" / "raw" / "seed_dialogues.yaml"
OUT_DIR = _BASE / "datasets" / "processed"

SYSTEM_PROMPT = (
    "Sen Garson Bot Bistro restoranının saygılı, yardımsever ve nazik bir garson "
    "asistanısın. Yalnızca menüde mevcut olan ürünler hakkında bilgi verir, "
    "sipariş alır ve müşterilere yardımcı olursun. Menüde olmayan konularda "
    "kibarca yönlendirirsin."
)

TRAIN_RATIO = 0.85
SPLIT_SEED = 42


def _to_chat_record(example: Dict[str, Any]) -> Dict[str, Any]:
    """Convert one seed example to a chat-format dict."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": example["user"]},
            {"role": "assistant", "content": example["assistant_response"]},
        ],
        "metadata": {
            "id": example["id"],
            "intent": example["expected_intent"],
            "entities": example.get("expected_entities", {}),
        },
    }


def _write_jsonl(records: List[Dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} records -> {path}")


def build(raw_path: Path = RAW_PATH, out_dir: Path = OUT_DIR) -> None:
    if not raw_path.exists():
        raise FileNotFoundError(f"Seed dialogues not found: {raw_path}")

    data = yaml.safe_load(raw_path.read_text(encoding="utf-8"))
    examples: List[Dict] = data.get("dialogues", [])
    if not examples:
        raise ValueError("No dialogues found in seed file.")

    records = [_to_chat_record(ex) for ex in examples]
    random.Random(SPLIT_SEED).shuffle(records)

    split_idx = math.ceil(len(records) * TRAIN_RATIO)
    train_records = records[:split_idx]
    valid_records = records[split_idx:]

    _write_jsonl(train_records, out_dir / "waiter_sft_train.jsonl")
    _write_jsonl(valid_records, out_dir / "waiter_sft_valid.jsonl")

    print(
        f"\nDataset build complete. "
        f"Total: {len(records)} | Train: {len(train_records)} | Valid: {len(valid_records)}"
    )


if __name__ == "__main__":
    build()
