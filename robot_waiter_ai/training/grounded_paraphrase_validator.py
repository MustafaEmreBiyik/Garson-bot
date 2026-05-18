"""
grounded_paraphrase_validator.py

Validates the grounded paraphrase seed dataset used for future grounded paraphraser work.

Checks:
  - Required fields are present.
  - intent is from the allowed intent list.
  - canonical_response and safe_paraphrase are non-empty.
  - IDs are unique.
  - safe_paraphrase preserves required terms.
  - safe_paraphrase does not contain forbidden terms.

Usage (from project root):
  .venv\\Scripts\\python.exe -m robot_waiter_ai.training.grounded_paraphrase_validator
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from robot_waiter_ai.assistant.menu_knowledge import normalize_text
from robot_waiter_ai.inference.structured_result import SUPPORTED_GROUNDED_INTENTS

_BASE = Path(__file__).resolve().parents[1]
RAW_PATH = _BASE / "datasets" / "raw" / "grounded_paraphrase_seed.yaml"

REQUIRED_FIELDS = {
    "id",
    "user_message",
    "intent",
    "canonical_response",
    "safe_paraphrase",
    "must_preserve_terms",
    "must_not_introduce",
    "notes",
}


def _contains_term(text: str, term: str) -> bool:
    return normalize_text(term) in normalize_text(text)


def _validate_example(ex: Dict[str, Any], idx: int, seen_ids: set[str]) -> List[str]:
    errors: List[str] = []
    ex_id = str(ex.get("id", f"<index {idx}>"))

    for field in REQUIRED_FIELDS:
        if field not in ex:
            errors.append(f"[{ex_id}] Missing required field: '{field}'")

    if ex_id in seen_ids:
        errors.append(f"[{ex_id}] Duplicate id detected")
    else:
        seen_ids.add(ex_id)

    intent = str(ex.get("intent", ""))
    if intent and intent not in SUPPORTED_GROUNDED_INTENTS:
        errors.append(f"[{ex_id}] Unknown intent: '{intent}'")

    canonical_response = str(ex.get("canonical_response", ""))
    safe_paraphrase = str(ex.get("safe_paraphrase", ""))
    if not canonical_response.strip():
        errors.append(f"[{ex_id}] canonical_response is empty")
    if not safe_paraphrase.strip():
        errors.append(f"[{ex_id}] safe_paraphrase is empty")

    preserve_terms = ex.get("must_preserve_terms", [])
    forbidden_terms = ex.get("must_not_introduce", [])
    if not isinstance(preserve_terms, list):
        errors.append(f"[{ex_id}] must_preserve_terms must be a list")
    if not isinstance(forbidden_terms, list):
        errors.append(f"[{ex_id}] must_not_introduce must be a list")

    if isinstance(preserve_terms, list):
        for term in preserve_terms:
            if not _contains_term(safe_paraphrase, str(term)):
                errors.append(f"[{ex_id}] safe_paraphrase missing preserve term: '{term}'")

    if isinstance(forbidden_terms, list):
        for term in forbidden_terms:
            if _contains_term(safe_paraphrase, str(term)):
                errors.append(f"[{ex_id}] safe_paraphrase contains forbidden term: '{term}'")

    return errors


def validate(raw_path: Path = RAW_PATH) -> Tuple[int, int, List[str]]:
    if not raw_path.exists():
        raise FileNotFoundError(f"Grounded paraphrase seed file not found: {raw_path}")

    data = yaml.safe_load(raw_path.read_text(encoding="utf-8")) or {}
    examples: List[Dict[str, Any]] = data.get("examples", [])

    all_errors: List[str] = []
    seen_ids: set[str] = set()
    for idx, ex in enumerate(examples):
        all_errors.extend(_validate_example(ex, idx, seen_ids))

    return len(examples), len(all_errors), all_errors


def main() -> None:
    total, error_count, errors = validate()
    print(f"Validated {total} grounded paraphrase examples.")
    if errors:
        print(f"\n{error_count} error(s) found:")
        for error in errors:
            print(f"  x {error}")
    else:
        print("All grounded paraphrase examples passed validation.")


if __name__ == "__main__":
    main()
