"""
dataset_validator.py

Validates every example in datasets/raw/seed_dialogues.yaml.

Checks:
  - Required fields are present.
  - expected_intent is from the allowed intent list.
  - assistant_response is non-empty.
  - Order-related intents carry expected_entities when required.

Usage (from project root):
  .venv\\Scripts\\python.exe -m robot_waiter_ai.training.dataset_validator
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

_BASE = Path(__file__).resolve().parents[1]
RAW_PATH = _BASE / "datasets" / "raw" / "seed_dialogues.yaml"

REQUIRED_FIELDS = {"id", "user", "expected_intent", "assistant_response"}

ALLOWED_INTENTS = {
    "greeting",
    "menu_question",
    "recommendation",
    "price_question",
    "allergen_question",
    "add_item",
    "remove_item",
    "clear_order",
    "summarize_order",
    "confirm_order",
    "off_topic",
    "unavailable_item",
}

ENTITY_REQUIRED_INTENTS = {
    "add_item",
    "remove_item",
    "price_question",
    "allergen_question",
    "unavailable_item",
}


def _validate_example(ex: Dict[str, Any], idx: int) -> List[str]:
    errors: List[str] = []
    ex_id = ex.get("id", f"<index {idx}>")

    for field in REQUIRED_FIELDS:
        if field not in ex:
            errors.append(f"[{ex_id}] Missing required field: '{field}'")

    intent = ex.get("expected_intent", "")
    if intent and intent not in ALLOWED_INTENTS:
        errors.append(f"[{ex_id}] Unknown intent: '{intent}'")

    response = ex.get("assistant_response", "")
    if not str(response).strip():
        errors.append(f"[{ex_id}] assistant_response is empty")

    if intent in ENTITY_REQUIRED_INTENTS:
        entities = ex.get("expected_entities", {})
        if not entities:
            errors.append(
                f"[{ex_id}] Intent '{intent}' should include expected_entities but none found"
            )

    return errors


def validate(raw_path: Path = RAW_PATH) -> Tuple[int, int, List[str]]:
    """Return (total, error_count, error_messages)."""
    if not raw_path.exists():
        raise FileNotFoundError(f"Seed file not found: {raw_path}")

    data = yaml.safe_load(raw_path.read_text(encoding="utf-8"))
    examples: List[Dict] = data.get("dialogues", [])

    all_errors: List[str] = []
    for idx, ex in enumerate(examples):
        all_errors.extend(_validate_example(ex, idx))

    return len(examples), len(all_errors), all_errors


def main() -> None:
    total, error_count, errors = validate()
    print(f"Validated {total} examples.")
    if errors:
        print(f"\n{error_count} error(s) found:")
        for error in errors:
            print(f"  x {error}")
    else:
        print("All examples passed validation.")


if __name__ == "__main__":
    main()
