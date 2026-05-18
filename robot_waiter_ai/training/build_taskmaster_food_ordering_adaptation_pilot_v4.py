"""
Build a fourth, tightened manual adaptation pilot from raw Taskmaster food-ordering utterances.

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
DEFAULT_PILOT_V3_PATH = (
    _BASE / "datasets" / "intermediate" / "taskmaster_food_ordering_adaptation_pilot_50_v3.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "taskmaster_food_ordering_adaptation_pilot_50_v4.jsonl"
)
DEFAULT_MAX_RECORDS = 50

NOISE_PHRASES = [
    "what was i doing",
    "step away",
    "continue the order",
    "reorder",
    "re order",
    "same thing i ordered",
    "last week",
    "last weekend",
    "again",
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

TRIVIAL_FRAGMENT_PHRASES = {
    "no thanks",
    "no it s okay",
    "no it is okay",
    "okay",
    "yes",
    "no",
    "that s all",
    "that is all",
    "thank you",
    "thanks",
    "sure",
    "correct",
    "alright",
    "all right",
    "no thank you",
    "no that s it",
    "no that is it",
    "that s it",
    "that is it",
}

PRICE_EXCLUSION_PHRASES = [
    "price range",
    "price rating",
    "moderate",
    "location",
    "spend a ton",
]

ALLERGY_STRONG_PHRASES = [
    "allergy",
    "allergic",
    "gluten",
    "dairy",
    "peanut allergy",
    "nut allergy",
    "contains nuts",
    "without nuts because allergy",
]

INGREDIENT_STRONG_PHRASES = [
    "what is in",
    "what s in",
    "ingredients",
    "comes with",
    "does it include",
    "contains",
]

MODIFICATION_STRONG_PATTERNS = [
    r"\bwithout\s+\w+",
    r"\bno\s+\w+",
    r"\bextra\s+\w+",
    r"\badd\s+\w+",
    r"\bremove\s+\w+",
    r"\bhold\s+\w+",
    r"\binstead of\b",
]

PRICE_STRONG_PATTERNS = [
    r"\bhow much\b",
    r"\bcost\b",
    r"\bprice\b",
    r"\btotal\b",
    r"\bcharge\b",
]

MENU_STRONG_PATTERNS = [
    r"\bmenu\b",
    r"\bwhat do you have\b",
    r"\bwhat are the options\b",
    r"\bwhat can i order\b",
]

CONFIRM_STRONG_PATTERNS = [
    r"\bconfirm\b",
    r"\bis that all\b",
    r"\bthat s it\b",
    r"\bthat is it\b",
    r"\bcorrect\b",
]

PREFERRED_CATEGORY_ORDER = [
    "ask_menu",
    "ask_price",
    "ask_ingredient",
    "ask_allergy",
    "modify_order",
    "confirm_order",
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
    normalized = normalized.replace("what's", "what is")
    normalized = normalized.replace("it's", "it is")
    normalized = normalized.replace("that's", "that is")
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\b(take out)\b", "takeout", normalized)
    normalized = re.sub(r"\b(pick up)\b", "pickup", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _normalize_for_dedupe(text: str) -> str:
    normalized = _normalize_text(text)
    normalized = re.sub(r"\b(hi|hello|hey|assistant|please|yeah|oh|okay|ok|thanks|thank you)\b", " ", normalized)
    normalized = re.sub(
        r"\b(i would like to|i want to|i need to|can you help me with|can you help me|i am looking to)\b",
        " ",
        normalized,
    )
    normalized = re.sub(
        r"\bfor\s+(one|two|three|\d+)\s+(person|people)\b",
        " for qty people ",
        normalized,
    )
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _meaningful_word_count(text: str) -> int:
    tokens = [
        token
        for token in _normalize_text(text).split()
        if token not in {"hi", "hello", "hey", "please", "okay", "ok", "thanks", "thank", "you"}
    ]
    return len(tokens)


def _contains_any(text: str, phrases: Sequence[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _matches_any(text: str, patterns: Sequence[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _contains_noise_phrase(text: str) -> bool:
    return _contains_any(_normalize_text(text), NOISE_PHRASES)


def _contains_unsupported_keyword(text: str) -> bool:
    return _contains_any(_normalize_text(text), UNSUPPORTED_KEYWORDS)


def _is_trivial_fragment(text: str) -> bool:
    normalized = _normalize_text(text)
    return normalized in TRIVIAL_FRAGMENT_PHRASES


def _is_strong_modify_order(text: str) -> bool:
    normalized = _normalize_text(text)
    if _matches_any(normalized, MODIFICATION_STRONG_PATTERNS):
        return True

    # Treat "with ..." as a modification only when there is clear order/request context,
    # not when the utterance is just a bare ingredient phrase.
    if re.search(r"\bwith\s+\w+", normalized) and _contains_any(
        normalized,
        [
            "i want",
            "i would like",
            "i will have",
            "i ll have",
            "can i get",
            "could i get",
            "order",
            "get me",
            "make that",
            "i need",
        ],
    ):
        return True

    return False


def _is_strong_price_question(text: str) -> bool:
    normalized = _normalize_text(text)
    if _contains_any(normalized, PRICE_EXCLUSION_PHRASES):
        return False
    return _matches_any(normalized, PRICE_STRONG_PATTERNS)


def _is_strong_allergy_question(text: str) -> bool:
    normalized = _normalize_text(text)
    return _contains_any(normalized, ALLERGY_STRONG_PHRASES)


def _is_strong_ingredient_question(text: str) -> bool:
    return _contains_any(_normalize_text(text), INGREDIENT_STRONG_PHRASES)


def _is_strong_menu_question(text: str) -> bool:
    return _matches_any(_normalize_text(text), MENU_STRONG_PATTERNS)


def _is_strong_confirm(text: str) -> bool:
    return _matches_any(_normalize_text(text), CONFIRM_STRONG_PATTERNS)


def _passes_fragment_filter(text: str) -> bool:
    normalized = _normalize_text(text)
    if _is_trivial_fragment(text):
        return False

    if _meaningful_word_count(text) >= 4:
        return True

    if _is_strong_modify_order(text):
        return True
    if _is_strong_price_question(text):
        return True
    if _is_strong_ingredient_question(text):
        return True
    if _is_strong_allergy_question(text):
        return True
    if _is_strong_menu_question(text):
        return True
    if _is_strong_confirm(text):
        return True

    return False


def _infer_category(text: str) -> str | None:
    if _is_strong_menu_question(text):
        return "ask_menu"
    if _is_strong_price_question(text):
        return "ask_price"
    if _is_strong_ingredient_question(text):
        return "ask_ingredient"
    if _is_strong_allergy_question(text):
        return "ask_allergy"
    if _is_strong_modify_order(text):
        return "modify_order"
    if _is_strong_confirm(text):
        return "confirm_order"
    return None


def _category_rank(category: str) -> int:
    try:
        return PREFERRED_CATEGORY_ORDER.index(category)
    except ValueError:
        return len(PREFERRED_CATEGORY_ORDER)


def _sort_key(record: Dict[str, Any]) -> tuple[int, int, str]:
    category = str(record["candidate_category"])
    text = str(record["original_text"])
    return (_category_rank(category), len(text), _normalize_for_dedupe(text))


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
        "pilot_version": "v4_tightened_high_precision",
    }


def build_adaptation_pilot_v4(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    pilot_v1_path: Path = DEFAULT_PILOT_V1_PATH,
    pilot_v2_path: Path = DEFAULT_PILOT_V2_PATH,
    pilot_v3_path: Path = DEFAULT_PILOT_V3_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    max_records: int = DEFAULT_MAX_RECORDS,
) -> Dict[str, Any]:
    excluded_keys = _load_excluded_keys([pilot_v1_path, pilot_v2_path, pilot_v3_path])
    raw_records_read = 0
    excluded_prior_pilots = 0
    after_noise_unsupported = 0
    fragment_noisy_excluded = 0
    duplicates_removed = 0

    deduped_records: List[Dict[str, Any]] = []
    seen_dedupe_keys: set[str] = set()

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
            fragment_noisy_excluded += 1
            continue
        if _contains_unsupported_keyword(text):
            fragment_noisy_excluded += 1
            continue

        after_noise_unsupported += 1

        if not _passes_fragment_filter(text):
            fragment_noisy_excluded += 1
            continue

        category = _infer_category(text)
        if category is None:
            fragment_noisy_excluded += 1
            continue

        dedupe_key = _normalize_for_dedupe(text)
        if dedupe_key in seen_dedupe_keys:
            duplicates_removed += 1
            continue
        seen_dedupe_keys.add(dedupe_key)

        candidate = dict(record)
        candidate["candidate_category"] = category
        deduped_records.append(candidate)

    selected_candidates = sorted(deduped_records, key=_sort_key)[:max_records]
    pilot_records = [_pilot_record(record, record["candidate_category"]) for record in selected_candidates]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in pilot_records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    category_counts = Counter(record["candidate_category"] for record in pilot_records)
    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "raw_records_read": raw_records_read,
        "excluded_prior_pilots": excluded_prior_pilots,
        "after_noise_unsupported": after_noise_unsupported,
        "fragment_noisy_excluded": fragment_noisy_excluded,
        "duplicates_removed": duplicates_removed,
        "records_written": len(pilot_records),
        "category_counts": dict(sorted(category_counts.items())),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a fourth tightened and high-precision food-ordering adaptation pilot."
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
        "--pilot-v3",
        type=Path,
        default=DEFAULT_PILOT_V3_PATH,
        help=f"Third pilot path to exclude (default: {DEFAULT_PILOT_V3_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Pilot v4 output path (default: {DEFAULT_OUTPUT_PATH})",
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
        print("Taskmaster pilot v4 build failed. Missing input file:", file=sys.stderr)
        print(f"- {Path(args.input)}", file=sys.stderr)
        return 1

    try:
        summary = build_adaptation_pilot_v4(
            input_path=Path(args.input),
            pilot_v1_path=Path(args.pilot_v1),
            pilot_v2_path=Path(args.pilot_v2),
            pilot_v3_path=Path(args.pilot_v3),
            output_path=Path(args.output),
            max_records=args.max_records,
        )
    except Exception as exc:
        print(f"Taskmaster pilot v4 build failed: {exc}", file=sys.stderr)
        return 1

    print("Taskmaster food-ordering adaptation pilot v4 build complete.")
    print(f"Raw/input records read: {summary['raw_records_read']}")
    print(f"Prior pilot records excluded: {summary['excluded_prior_pilots']}")
    print(f"Records after noise/unsupported filtering: {summary['after_noise_unsupported']}")
    print(f"Fragment/noisy records excluded: {summary['fragment_noisy_excluded']}")
    print(f"Duplicates removed: {summary['duplicates_removed']}")
    print(f"Records written: {summary['records_written']}")
    print("Category distribution:")
    for category, count in summary["category_counts"].items():
        print(f"- {category}: {count}")
    print(f"Output path: {summary['output_path']}")
    print("Inspect the first 20 rows with:")
    print(
        "Get-Content "
        "robot_waiter_ai\\datasets\\intermediate\\taskmaster_food_ordering_adaptation_pilot_50_v4.jsonl "
        "-TotalCount 20"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
