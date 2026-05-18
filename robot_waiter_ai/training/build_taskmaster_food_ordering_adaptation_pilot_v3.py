"""
Build a third, more targeted manual adaptation pilot from raw Taskmaster food-ordering utterances.

This remains a review-only intermediate worksheet. It does not generate training
data, assistant responses, deterministic previews, or paraphrases.
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
    _BASE / "datasets" / "intermediate" / "taskmaster_user_utterances_raw.jsonl"
)
DEFAULT_PILOT_V1_PATH = (
    _BASE / "datasets" / "intermediate" / "taskmaster_food_ordering_adaptation_pilot_30.jsonl"
)
DEFAULT_PILOT_V2_PATH = (
    _BASE / "datasets" / "intermediate" / "taskmaster_food_ordering_adaptation_pilot_50_v2.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "taskmaster_food_ordering_adaptation_pilot_50_v3.jsonl"
)
DEFAULT_MAX_RECORDS = 50
MAX_GENERIC_ORDER_STARTS = 5

NOISE_PHRASES = [
    "what was i doing",
    "step away",
    "continue the order",
    "reorder",
    "re-order",
    "same thing i ordered",
    "last week",
    "last weekend",
]

UNSUPPORTED_KEYWORDS = [
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
    "gyro",
    "gyros",
    "greek",
    "mexican",
    "indian",
    "thai",
    "italian",
    "barbecue",
    "bbq",
    "taco",
    "tacos",
]

PREFERRED_CATEGORY_ORDER = [
    "ask_menu",
    "ask_price",
    "ask_ingredient",
    "ask_allergy",
    "modify_order",
    "confirm_order",
    "ask_recommendation",
    "generic_order_start",
    "order_item",
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


def _load_excluded_keys(paths: Sequence[Path]) -> set[tuple[str, Any]]:
    keys: set[tuple[str, Any]] = set()
    for path in paths:
        if not path.exists():
            continue
        for record in _iter_jsonl(path):
            keys.add((str(record.get("conversation_id")), record.get("turn_index")))
    return keys


def _normalize_text(text: str) -> str:
    normalized = text.lower().replace("\xa0", " ")
    normalized = normalized.replace("i'd", "i would")
    normalized = normalized.replace("can't", "cannot")
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\b(hi|hello|hey|assistant|please|yeah|oh|okay|ok)\b", " ", normalized)
    normalized = re.sub(r"\b(i would like to|i want to|i need to|can you help me with|can you help me)\b", " ", normalized)
    normalized = re.sub(r"\b(take out)\b", "takeout", normalized)
    normalized = re.sub(r"\b(pick up)\b", "pickup", normalized)
    normalized = re.sub(
        r"\bfor\s+(one|two|three|\d+)\s+(person|people)\b",
        " for qty people ",
        normalized,
    )
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _contains_any(text: str, phrases: Sequence[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _contains_noise_phrase(text: str) -> bool:
    normalized = _normalize_text(text)
    return _contains_any(normalized, NOISE_PHRASES) or " again" in f" {normalized}"


def _contains_unsupported_keyword(text: str) -> bool:
    normalized = _normalize_text(text)
    return _contains_any(normalized, UNSUPPORTED_KEYWORDS)


def _infer_category(text: str) -> str:
    normalized = _normalize_text(text)

    if _contains_any(
        normalized,
        ["menu", "what do you have", "what are the options", "what can i order"],
    ):
        return "ask_menu"
    if _contains_any(normalized, ["price", "cost", "how much"]):
        return "ask_price"
    if _contains_any(
        normalized,
        ["ingredient", "comes with", "what is in", "include", "included"],
    ):
        return "ask_ingredient"
    if _contains_any(
        normalized,
        ["allergic", "allergy", "gluten", "dairy", "nuts", "peanut"],
    ):
        return "ask_allergy"
    if _contains_any(normalized, ["without", "no ", "extra", "add ", "remove "]):
        return "modify_order"
    if _contains_any(normalized, ["confirm", "is that all", "that s it", "that is it", "correct"]):
        return "confirm_order"
    if _contains_any(normalized, ["recommend", "suggest", "best", "favorite"]):
        return "ask_recommendation"
    if _is_generic_order_start(text):
        return "generic_order_start"
    return "order_item"


def _is_generic_order_start(text: str) -> bool:
    normalized = _normalize_text(text)
    if not _contains_any(
        normalized,
        [
            "order",
            "takeout",
            "pickup",
        ],
    ):
        return False

    if _contains_any(
        normalized,
        [
            "menu",
            "price",
            "cost",
            "how much",
            "ingredient",
            "comes with",
            "what is in",
            "include",
            "allergy",
            "allergic",
            "gluten",
            "dairy",
            "nuts",
            "peanut",
            "without",
            "extra",
            "remove",
            "recommend",
            "suggest",
            "best",
            "favorite",
            "confirm",
            "correct",
        ],
    ):
        return False

    return True


def _category_rank(category: str) -> int:
    try:
        return PREFERRED_CATEGORY_ORDER.index(category)
    except ValueError:
        return len(PREFERRED_CATEGORY_ORDER)


def _sort_key(record: Dict[str, Any]) -> tuple[int, int, str]:
    category = str(record["candidate_category"])
    text = str(record["original_text"])
    return (_category_rank(category), len(text), _normalize_text(text))


def _pilot_record(record: Dict[str, Any], category: str) -> Dict[str, Any]:
    return {
        "source_dataset": record.get("source_dataset"),
        "source_domain": record.get("source_domain"),
        "conversation_id": record.get("conversation_id"),
        "turn_index": record.get("turn_index"),
        "original_text": record.get("original_text"),
        "candidate_category": category,
        "turkish_adapted_user_message": "",
        "adaptation_status": "needs_manual_review",
        "adaptation_notes": "",
        "include_for_future_grounded_generation": False,
        "pilot_version": "v3_targeted_deduped",
    }


def build_adaptation_pilot_v3(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    pilot_v1_path: Path = DEFAULT_PILOT_V1_PATH,
    pilot_v2_path: Path = DEFAULT_PILOT_V2_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    max_records: int = DEFAULT_MAX_RECORDS,
) -> Dict[str, Any]:
    excluded_keys = _load_excluded_keys([pilot_v1_path, pilot_v2_path])
    raw_records_read = 0
    excluded_prior_pilots = 0
    after_filtering_records = 0
    duplicates_removed = 0

    deduped_records: List[Dict[str, Any]] = []
    seen_normalized_texts: set[str] = set()

    for record in _iter_jsonl(input_path):
        raw_records_read += 1
        if record.get("source_domain") != "food_ordering":
            continue

        key = (str(record.get("conversation_id")), record.get("turn_index"))
        if key in excluded_keys:
            excluded_prior_pilots += 1
            continue

        text = str(record.get("original_text", ""))
        if not text.strip():
            continue

        if _contains_noise_phrase(text):
            continue
        if _contains_unsupported_keyword(text):
            continue

        category = _infer_category(text)
        candidate = dict(record)
        candidate["candidate_category"] = category
        after_filtering_records += 1

        dedupe_key = _normalize_text(text)
        if dedupe_key in seen_normalized_texts:
            duplicates_removed += 1
            continue
        seen_normalized_texts.add(dedupe_key)
        deduped_records.append(candidate)

    ordered_records = sorted(deduped_records, key=_sort_key)

    selected: List[Dict[str, Any]] = []
    generic_count = 0
    for record in ordered_records:
        if len(selected) >= max_records:
            break
        if record["candidate_category"] == "generic_order_start":
            if generic_count >= MAX_GENERIC_ORDER_STARTS:
                continue
            generic_count += 1
        selected.append(_pilot_record(record, record["candidate_category"]))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in selected:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    category_counts = Counter(record["candidate_category"] for record in selected)
    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "raw_records_read": raw_records_read,
        "excluded_prior_pilots": excluded_prior_pilots,
        "after_filtering_records": after_filtering_records,
        "duplicates_removed": duplicates_removed,
        "generic_order_start_included": generic_count,
        "records_written": len(selected),
        "category_counts": dict(sorted(category_counts.items())),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a third targeted and deduped food-ordering adaptation pilot."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Raw input path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--pilot-v1",
        type=Path,
        default=DEFAULT_PILOT_V1_PATH,
        help=f"First pilot path to exclude (default: {DEFAULT_PILOT_V1_PATH})",
    )
    parser.add_argument(
        "--pilot-v2",
        type=Path,
        default=DEFAULT_PILOT_V2_PATH,
        help=f"Second pilot path to exclude (default: {DEFAULT_PILOT_V2_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Pilot v3 output path (default: {DEFAULT_OUTPUT_PATH})",
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
        print("Taskmaster pilot v3 build failed. Missing input file:", file=sys.stderr)
        print(f"- {Path(args.input)}", file=sys.stderr)
        return 1

    try:
        summary = build_adaptation_pilot_v3(
            input_path=Path(args.input),
            pilot_v1_path=Path(args.pilot_v1),
            pilot_v2_path=Path(args.pilot_v2),
            output_path=Path(args.output),
            max_records=args.max_records,
        )
    except Exception as exc:
        print(f"Taskmaster pilot v3 build failed: {exc}", file=sys.stderr)
        return 1

    print("Taskmaster food-ordering adaptation pilot v3 build complete.")
    print(f"Raw/input records read: {summary['raw_records_read']}")
    print(f"First/v2 pilot records excluded: {summary['excluded_prior_pilots']}")
    print(f"Records after noise/unsupported filtering: {summary['after_filtering_records']}")
    print(f"Normalized duplicates removed: {summary['duplicates_removed']}")
    print(f"Generic order-start records included: {summary['generic_order_start_included']}")
    print(f"Records written: {summary['records_written']}")
    print("Category distribution:")
    for category, count in summary["category_counts"].items():
        print(f"- {category}: {count}")
    print(f"Output path: {summary['output_path']}")
    print("Inspect the first 15 rows with:")
    print(
        "Get-Content "
        "robot_waiter_ai\\datasets\\intermediate\\taskmaster_food_ordering_adaptation_pilot_50_v3.jsonl "
        "-TotalCount 15"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
