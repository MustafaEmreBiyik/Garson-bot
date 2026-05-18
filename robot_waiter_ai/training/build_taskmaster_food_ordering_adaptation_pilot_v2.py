"""
Build a second, more targeted manual adaptation pilot from food-ordering candidates.

This remains a review-only intermediate worksheet. It does not generate training
data, assistant responses, or deterministic previews.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

_BASE = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = (
    _BASE / "datasets" / "intermediate" / "taskmaster_food_ordering_candidates.jsonl"
)
DEFAULT_PREVIOUS_PILOT_PATH = (
    _BASE / "datasets" / "intermediate" / "taskmaster_food_ordering_adaptation_pilot_30.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "taskmaster_food_ordering_adaptation_pilot_50_v2.jsonl"
)
DEFAULT_MAX_RECORDS = 50

PREFERRED_CATEGORY_ORDER = [
    "ask_menu",
    "ask_price",
    "ask_ingredient",
    "ask_allergy",
    "ask_recommendation",
    "modify_order",
    "remove_item",
    "confirm_order",
    "order_item",
]

DOWNRANK_KEYWORDS = [
    "pizza",
    "pizz",
    "burger",
    "hamburger",
    "burrito",
    "hot dog",
    "sandwich",
    "sandwiches",
    "poke",
    "sushi",
    "gyros",
    "greek",
    "mexican",
    "indian",
    "thai",
    "italian",
    "barbecue",
    "bbq",
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


def _normalize_text(text: str) -> str:
    normalized = text.replace("\xa0", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip().lower()


def _load_previous_pilot_keys(path: Path) -> set[tuple[str, Any]]:
    if not path.exists():
        return set()
    keys: set[tuple[str, Any]] = set()
    for record in _iter_jsonl(path):
        keys.add((str(record.get("conversation_id")), record.get("turn_index")))
    return keys


def _contains_downrank_keyword(text: str) -> bool:
    normalized = _normalize_text(text)
    return any(keyword in normalized for keyword in DOWNRANK_KEYWORDS)


def _category_rank(category: str) -> int:
    try:
        return PREFERRED_CATEGORY_ORDER.index(category)
    except ValueError:
        return len(PREFERRED_CATEGORY_ORDER)


def _candidate_sort_key(record: Dict[str, Any]) -> tuple[int, int, int, int, str]:
    category = str(record.get("candidate_category", ""))
    text = str(record.get("original_text", ""))
    keyword_penalty = 1 if _contains_downrank_keyword(text) else 0
    normalized = _normalize_text(text)
    generic_order_starter_bonus = 0
    if category == "order_item" and any(
        phrase in normalized
        for phrase in (
            "order takeout",
            "place an order",
            "order for one",
            "order for two",
            "order for three",
            "i want to order",
            "i'd like to order",
        )
    ):
        generic_order_starter_bonus = -1

    return (
        _category_rank(category),
        keyword_penalty,
        generic_order_starter_bonus,
        len(text),
        normalized,
    )


def _pilot_record(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source_dataset": record.get("source_dataset"),
        "source_domain": record.get("source_domain"),
        "conversation_id": record.get("conversation_id"),
        "turn_index": record.get("turn_index"),
        "original_text": record.get("original_text"),
        "candidate_category": record.get("candidate_category"),
        "turkish_adapted_user_message": "",
        "adaptation_status": "needs_manual_review",
        "adaptation_notes": "",
        "include_for_future_grounded_generation": False,
        "pilot_version": "v2_menu_aware",
    }


def build_adaptation_pilot_v2(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    previous_pilot_path: Path = DEFAULT_PREVIOUS_PILOT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    max_records: int = DEFAULT_MAX_RECORDS,
) -> Dict[str, Any]:
    previous_keys = _load_previous_pilot_keys(previous_pilot_path)

    eligible_candidates: List[Dict[str, Any]] = []
    excluded_previous_pilot = 0
    records_read = 0

    for record in _iter_jsonl(input_path):
        records_read += 1
        if record.get("source_domain") != "food_ordering":
            continue
        if record.get("keep_candidate") is not True:
            continue

        key = (str(record.get("conversation_id")), record.get("turn_index"))
        if key in previous_keys:
            excluded_previous_pilot += 1
            continue

        eligible_candidates.append(record)

    selected_candidates = sorted(eligible_candidates, key=_candidate_sort_key)[:max_records]
    pilot_records = [_pilot_record(record) for record in selected_candidates]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in pilot_records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    category_counts = Counter(record["candidate_category"] for record in pilot_records)
    return {
        "input_path": str(input_path),
        "previous_pilot_path": str(previous_pilot_path),
        "output_path": str(output_path),
        "records_read": records_read,
        "records_written": len(pilot_records),
        "excluded_previous_pilot": excluded_previous_pilot,
        "category_counts": dict(sorted(category_counts.items())),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a second menu-aware manual adaptation pilot from food-ordering candidates."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Food-ordering candidate input path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--previous-pilot",
        type=Path,
        default=DEFAULT_PREVIOUS_PILOT_PATH,
        help=f"Existing pilot path to exclude (default: {DEFAULT_PREVIOUS_PILOT_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Pilot v2 output path (default: {DEFAULT_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=DEFAULT_MAX_RECORDS,
        help="Maximum number of review rows to write.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not Path(args.input).exists():
        print("Taskmaster pilot v2 build failed. Missing input file:", file=sys.stderr)
        print(f"- {Path(args.input)}", file=sys.stderr)
        return 1

    try:
        summary = build_adaptation_pilot_v2(
            input_path=Path(args.input),
            previous_pilot_path=Path(args.previous_pilot),
            output_path=Path(args.output),
            max_records=args.max_records,
        )
    except Exception as exc:
        print(f"Taskmaster pilot v2 build failed: {exc}", file=sys.stderr)
        return 1

    print("Taskmaster food-ordering adaptation pilot v2 build complete.")
    print(f"Records read: {summary['records_read']}")
    print(f"Records written: {summary['records_written']}")
    print(f"Excluded first-pilot records: {summary['excluded_previous_pilot']}")
    print("Category distribution:")
    for category, count in summary["category_counts"].items():
        print(f"- {category}: {count}")
    print(f"Output path: {summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
