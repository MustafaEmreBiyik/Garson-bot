"""
Build a small manual adaptation pilot from the food-ordering adaptation template.

This utility creates a capped review-only worksheet. It does not translate text,
create training data, or modify processed train/valid datasets.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

_BASE = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "taskmaster_food_ordering_adaptation_template.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "taskmaster_food_ordering_adaptation_pilot_30.jsonl"
)
DEFAULT_MAX_RECORDS = 30

PREFERRED_CATEGORY_ORDER = [
    "order_item",
    "ask_menu",
    "ask_price",
    "modify_order",
    "remove_item",
    "confirm_order",
    "ask_ingredient",
    "ask_allergy",
    "ask_recommendation",
]


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"Expected JSON object at {path}:{line_number}")
            yield payload


def _normalized_pilot_record(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source_dataset": record.get("source_dataset"),
        "source_domain": record.get("source_domain"),
        "conversation_id": record.get("conversation_id"),
        "turn_index": record.get("turn_index"),
        "original_text": record.get("original_text", ""),
        "candidate_category": record.get("candidate_category", "unclear"),
        "turkish_adapted_user_message": "",
        "adaptation_status": "needs_manual_review",
        "adaptation_notes": record.get("adaptation_notes", ""),
        "include_for_future_grounded_generation": False,
    }


def build_adaptation_pilot(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    max_records: int = DEFAULT_MAX_RECORDS,
) -> Dict[str, Any]:
    records = [_normalized_pilot_record(record) for record in _iter_jsonl(input_path)]
    records = [record for record in records if record["source_domain"] == "food_ordering"]

    selected: List[Dict[str, Any]] = []
    seen_keys: set[tuple[Any, Any, Any]] = set()

    for category in PREFERRED_CATEGORY_ORDER:
        if len(selected) >= max_records:
            break
        for record in records:
            if record["candidate_category"] != category:
                continue
            key = (
                record["conversation_id"],
                record["turn_index"],
                record["original_text"],
            )
            if key in seen_keys:
                continue
            selected.append(record)
            seen_keys.add(key)
            break

    for record in records:
        if len(selected) >= max_records:
            break
        key = (
            record["conversation_id"],
            record["turn_index"],
            record["original_text"],
        )
        if key in seen_keys:
            continue
        selected.append(record)
        seen_keys.add(key)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in selected:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    category_counts = Counter(record["candidate_category"] for record in selected)
    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "records_read": len(records),
        "records_written": len(selected),
        "category_counts": dict(category_counts),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a small manual pilot worksheet from the food-ordering adaptation template."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Food-ordering adaptation template path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Pilot worksheet output path (default: {DEFAULT_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=DEFAULT_MAX_RECORDS,
        help="Maximum number of pilot worksheet rows to write.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not Path(args.input).exists():
        print("Taskmaster pilot build failed. Missing input file:", file=sys.stderr)
        print(f"- {Path(args.input)}", file=sys.stderr)
        return 1

    try:
        summary = build_adaptation_pilot(
            input_path=Path(args.input),
            output_path=Path(args.output),
            max_records=args.max_records,
        )
    except Exception as exc:
        print(f"Taskmaster pilot build failed: {exc}", file=sys.stderr)
        return 1

    print("Taskmaster food-ordering adaptation pilot build complete.")
    print(f"Input path: {summary['input_path']}")
    print(f"Records read: {summary['records_read']}")
    print(f"Pilot records written: {summary['records_written']}")
    print("Pilot category distribution:")
    for category, count in sorted(summary["category_counts"].items()):
        print(f"- {category}: {count}")
    print(f"Output path: {summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
