"""
grounded_paraphrase_builder.py

Loads datasets/raw/grounded_paraphrase_seed.yaml and converts each example into
chat-training format for future grounded paraphraser supervised fine-tuning.

Produces two JSONL files:
  datasets/processed/grounded_paraphrase_train.jsonl
  datasets/processed/grounded_paraphrase_valid.jsonl

Usage (from project root):
  .venv\\Scripts\\python.exe -m robot_waiter_ai.training.grounded_paraphrase_builder
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List

import yaml

_BASE = Path(__file__).resolve().parents[1]
RAW_PATH = _BASE / "datasets" / "raw" / "grounded_paraphrase_seed.yaml"
OUT_DIR = _BASE / "datasets" / "processed"

SYSTEM_PROMPT = (
    "Sen güvenli bir Türkçe garson asistanı paraphrase modelisin. "
    "Verilen canonical cevabı ve koruma terimlerini bozmadan daha doğal ifade edersin."
)

TRAIN_RATIO = 0.85
SPLIT_SEED = 42


def _format_user_prompt(example: Dict[str, Any]) -> str:
    preserve_terms = ", ".join(str(term) for term in example["must_preserve_terms"]) or "-"
    forbidden_terms = ", ".join(str(term) for term in example["must_not_introduce"]) or "-"
    return (
        f"Kullanıcı mesajı: {example['user_message']}\n"
        f"Intent: {example['intent']}\n"
        f"Canonical cevap: {example['canonical_response']}\n"
        f"Korunacak terimler: {preserve_terms}\n"
        f"Eklenmemesi gereken terimler: {forbidden_terms}\n"
        "Görev: Canonical cevabı daha doğal Türkçe ile paraphrase et ama güvenlik ve grounding kurallarını bozma."
    )


def _to_chat_record(example: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _format_user_prompt(example)},
            {"role": "assistant", "content": example["safe_paraphrase"]},
        ],
        "metadata": {
            "id": example["id"],
            "intent": example["intent"],
            "notes": example["notes"],
        },
    }


def _write_jsonl(records: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} records -> {path}")


def build(raw_path: Path = RAW_PATH, out_dir: Path = OUT_DIR) -> None:
    if not raw_path.exists():
        raise FileNotFoundError(f"Grounded paraphrase seed file not found: {raw_path}")

    data = yaml.safe_load(raw_path.read_text(encoding="utf-8")) or {}
    examples: List[Dict[str, Any]] = data.get("examples", [])
    if not examples:
        raise ValueError("No grounded paraphrase examples found in seed file.")

    records = [_to_chat_record(ex) for ex in examples]
    random.Random(SPLIT_SEED).shuffle(records)

    split_idx = math.ceil(len(records) * TRAIN_RATIO)
    train_records = records[:split_idx]
    valid_records = records[split_idx:]

    _write_jsonl(train_records, out_dir / "grounded_paraphrase_train.jsonl")
    _write_jsonl(valid_records, out_dir / "grounded_paraphrase_valid.jsonl")

    print(
        f"\nGrounded paraphrase dataset build complete. "
        f"Total: {len(records)} | Train: {len(train_records)} | Valid: {len(valid_records)}"
    )


if __name__ == "__main__":
    build()
