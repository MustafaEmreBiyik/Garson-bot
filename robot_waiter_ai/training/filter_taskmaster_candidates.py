"""
Filter extracted Taskmaster user utterances into small reviewable candidate files.

This stage is intentionally conservative and rule-based. It labels external
English user utterances for manual review without modifying runtime behavior or
any existing processed train/valid datasets.
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
DEFAULT_FOOD_OUTPUT_PATH = (
    _BASE / "datasets" / "intermediate" / "taskmaster_food_ordering_candidates.jsonl"
)
DEFAULT_RESTAURANT_OUTPUT_PATH = (
    _BASE / "datasets" / "intermediate" / "taskmaster_restaurant_search_candidates.jsonl"
)

FOOD_ORDERING_DOMAIN = "food_ordering"
RESTAURANT_SEARCH_DOMAIN = "restaurant_search"
DEFAULT_MAX_FOOD_ORDERING_CANDIDATES = 300
DEFAULT_MAX_RESTAURANT_SEARCH_CANDIDATES = 100


def _normalize_text(text: str) -> str:
    normalized = text.replace("\xa0", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _contains_any(text: str, phrases: Sequence[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _matches_pattern(text: str, patterns: Sequence[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _is_restaurant_search_discovery_or_filtering(text: str) -> bool:
    return _contains_any(
        text,
        (
            "find a restaurant",
            "find me a restaurant",
            "find a place",
            "looking for restaurant",
            "looking for a restaurant",
            "restaurant to eat",
            "restaurant to go",
            "somewhere to eat",
            "good place to eat",
            "open now",
            "closest",
            "rating",
            "reviews",
            "search",
            "outdoor seating",
            "formal atmosphere",
            "atmosphere",
            "cuisine",
            "dishes",
        ),
    ) or _matches_pattern(
        text,
        (
            r"\bfind\b",
            r"\bfinding\b",
            r"\blooking for\b",
            r"\bsearching for\b",
            r"\brestaurant in\b",
            r"\brestaurant with\b",
        ),
    )


def classify_record(record: Dict[str, Any]) -> Dict[str, Any]:
    original_text = record.get("original_text", "")
    text = _normalize_text(original_text)
    lowered = text.lower()
    source_domain = record.get("source_domain", "")

    category = "unclear"
    keep_candidate: bool | None = False
    rejection_reason = "unclear_for_menu_grounded_adaptation"
    adaptation_notes = "Needs manual review before any menu-grounded Turkish adaptation."

    if _contains_any(
        lowered,
        (
            "reserve",
            "reservation",
            "book a table",
            "book me a table",
            "book a spot",
            "table for ",
            "party of ",
            "seating for ",
        ),
    ):
        category = "off_scope_reservation"
        keep_candidate = False
        rejection_reason = "reservation_request_out_of_scope"
        adaptation_notes = (
            "Current system is single-restaurant menu grounded, not reservation handling."
        )
    elif _contains_any(
        lowered,
        (
            "credit card",
            "debit card",
            "cash",
            "apple pay",
            "google pay",
            "pay with",
            "payment",
            "visa",
            "mastercard",
            "tip",
        ),
    ):
        category = "off_scope_payment"
        keep_candidate = False
        rejection_reason = "payment_flow_out_of_scope"
        adaptation_notes = "Current system does not model external payment flow requests."
    elif _contains_any(
        lowered,
        (
            "deliver to",
            "delivery address",
            "my address",
            "to my house",
            "to my apartment",
            "what's the address",
            "where are you located",
            "where is it located",
            "directions",
            "near me",
            "nearby",
            "zip code",
        ),
    ):
        category = "off_scope_delivery_address"
        keep_candidate = False
        rejection_reason = "delivery_or_address_request_out_of_scope"
        adaptation_notes = "Current system does not support delivery or location/address handling."
    elif source_domain == RESTAURANT_SEARCH_DOMAIN and _is_restaurant_search_discovery_or_filtering(
        lowered
    ):
        category = "off_scope_restaurant_search"
        keep_candidate = False
        rejection_reason = "restaurant_discovery_or_filtering_out_of_scope"
        adaptation_notes = (
            "Current system is menu grounded for one restaurant, not restaurant "
            "discovery, location search, or external restaurant filtering."
        )
    elif _contains_any(
        lowered,
        (
            "allergy",
            "allergic",
            "gluten",
            "peanut",
            "nut",
            "dairy",
            "shellfish",
            "vegan",
            "vegetarian",
        ),
    ):
        category = "ask_allergy"
        keep_candidate = True
        rejection_reason = ""
        adaptation_notes = (
            "Adapt into a Turkish allergy or dietary check against the single-restaurant menu."
        )
    elif _contains_any(
        lowered,
        (
            "what's in",
            "what is in",
            "what are the ingredients",
            "ingredient",
            "come with",
            "comes with",
            "made of",
            "does that have",
        ),
    ):
        category = "ask_ingredient"
        keep_candidate = True
        rejection_reason = ""
        adaptation_notes = "Adapt into a menu-grounded ingredient question for a listed item."
    elif _contains_any(
        lowered,
        (
            "how much",
            "what's the price",
            "what is the price",
            "what does it cost",
            "price of",
            "cost of",
        ),
    ):
        category = "ask_price"
        keep_candidate = source_domain == FOOD_ORDERING_DOMAIN
        rejection_reason = "" if keep_candidate else "restaurant_search_price_query_not_selected"
        adaptation_notes = (
            "Adapt into a single-restaurant menu price question."
            if keep_candidate
            else "Restaurant-search price questions are lower-priority for current scope."
        )
    elif _contains_any(
        lowered,
        (
            "what do you have",
            "what kind of",
            "menu",
            "sides",
            "drinks",
            "desserts",
            "options",
            "what comes",
        ),
    ):
        category = "ask_menu"
        keep_candidate = source_domain == FOOD_ORDERING_DOMAIN
        rejection_reason = "" if keep_candidate else "restaurant_search_menu_query_not_selected"
        adaptation_notes = (
            "Adapt into a Turkish menu exploration request grounded to available items."
            if keep_candidate
            else "Restaurant-search menu queries are kept conservative for now."
        )
    elif _contains_any(
        lowered,
        (
            "recommend",
            "recommended",
            "popular",
            "best",
            "suggest",
            "favorite",
            "specialty",
        ),
    ):
        category = "ask_recommendation"
        keep_candidate = source_domain == FOOD_ORDERING_DOMAIN
        rejection_reason = "" if keep_candidate else "restaurant_search_recommendation_not_selected"
        adaptation_notes = (
            "Adapt into a single-restaurant recommendation request."
            if keep_candidate
            else "Restaurant-search recommendation prompts stay conservative for now."
        )
    elif _contains_any(
        lowered,
        (
            "remove",
            "take off",
            "take that off",
            "cancel",
            "delete",
            "hold the ",
            "without ",
            "no onions",
            "no tomatoes",
        ),
    ):
        category = "remove_item"
        keep_candidate = source_domain == FOOD_ORDERING_DOMAIN
        rejection_reason = "" if keep_candidate else "non_food_remove_request_not_selected"
        adaptation_notes = (
            "Adapt into a remove-item or hold-ingredient request in Turkish."
            if keep_candidate
            else "Only current food-ordering remove flows are kept."
        )
    elif _contains_any(
        lowered,
        (
            "change",
            "instead",
            "make that",
            "switch that",
            "with ranch",
            "extra ",
            "add ",
            "make it ",
            "substitute",
        ),
    ):
        category = "modify_order"
        keep_candidate = source_domain == FOOD_ORDERING_DOMAIN
        rejection_reason = "" if keep_candidate else "non_food_modify_request_not_selected"
        adaptation_notes = (
            "Adapt into a Turkish order-modification request constrained by the menu."
            if keep_candidate
            else "Only current food-ordering modifications are kept."
        )
    elif _contains_any(
        lowered,
        (
            "that's all",
            "that'll do",
            "that will do",
            "sounds great",
            "sounds good",
            "correct",
            "yes that's right",
            "confirm",
            "that is correct",
        ),
    ):
        category = "confirm_order"
        keep_candidate = source_domain == FOOD_ORDERING_DOMAIN
        rejection_reason = "" if keep_candidate else "restaurant_search_confirmation_not_selected"
        adaptation_notes = (
            "Adapt into a final confirmation or order-complete utterance."
            if keep_candidate
            else "Restaurant-search confirmations are not prioritized."
        )
    elif _contains_any(
        lowered,
        (
            "can i get",
            "could i get",
            "i'd like",
            "i would like",
            "i want",
            "i'll have",
            "i will have",
            "order",
            "for takeout",
            "to go",
        ),
    ):
        category = "order_item"
        keep_candidate = source_domain == FOOD_ORDERING_DOMAIN
        rejection_reason = "" if keep_candidate else "restaurant_search_order_like_text_not_selected"
        adaptation_notes = (
            "Adapt into a Turkish order request grounded to available menu items only."
            if keep_candidate
            else "Order-like text from restaurant-search is not prioritized in this pass."
        )

    return {
        "source_dataset": record.get("source_dataset"),
        "source_domain": source_domain,
        "conversation_id": record.get("conversation_id"),
        "turn_index": record.get("turn_index"),
        "original_text": text,
        "candidate_category": category,
        "keep_candidate": keep_candidate,
        "rejection_reason": rejection_reason,
        "adaptation_notes": adaptation_notes,
        "adaptation_eligible": source_domain == FOOD_ORDERING_DOMAIN and keep_candidate is True,
    }


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


def _selection_priority(record: Dict[str, Any]) -> tuple[int, int, int]:
    category = record["candidate_category"]
    keep_candidate = record["keep_candidate"]
    text = record["original_text"]

    if keep_candidate is True:
        category_rank = 0
    elif category.startswith("off_scope_"):
        category_rank = 1
    else:
        category_rank = 2

    informative_rank = 0 if len(text) >= 12 else 1
    turn_index = record.get("turn_index")
    safe_turn_index = turn_index if isinstance(turn_index, int) else 10**9
    return (category_rank, informative_rank, safe_turn_index)


def _select_review_subset(records: Sequence[Dict[str, Any]], max_records: int) -> List[Dict[str, Any]]:
    if max_records <= 0:
        return []
    ordered = sorted(records, key=_selection_priority)
    return ordered[:max_records]


def _write_jsonl(records: Sequence[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def filter_candidates(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    food_output_path: Path = DEFAULT_FOOD_OUTPUT_PATH,
    restaurant_output_path: Path = DEFAULT_RESTAURANT_OUTPUT_PATH,
    max_food_ordering_candidates: int = DEFAULT_MAX_FOOD_ORDERING_CANDIDATES,
    max_restaurant_search_candidates: int = DEFAULT_MAX_RESTAURANT_SEARCH_CANDIDATES,
) -> Dict[str, Any]:
    by_domain: dict[str, List[Dict[str, Any]]] = {
        FOOD_ORDERING_DOMAIN: [],
        RESTAURANT_SEARCH_DOMAIN: [],
    }
    reviewed_counts = Counter()
    kept_counts = Counter()
    category_counts = Counter()
    raw_records_read = 0

    for raw_record in _iter_jsonl(input_path):
        raw_records_read += 1
        classified = classify_record(raw_record)
        source_domain = classified["source_domain"]
        if source_domain not in by_domain:
            continue

        by_domain[source_domain].append(classified)
        reviewed_counts[source_domain] += 1
        category_counts[classified["candidate_category"]] += 1
        if classified["keep_candidate"] is True:
            kept_counts[source_domain] += 1

    selected_food = _select_review_subset(
        by_domain[FOOD_ORDERING_DOMAIN],
        max_food_ordering_candidates,
    )
    selected_restaurant = _select_review_subset(
        by_domain[RESTAURANT_SEARCH_DOMAIN],
        max_restaurant_search_candidates,
    )

    _write_jsonl(selected_food, food_output_path)
    _write_jsonl(selected_restaurant, restaurant_output_path)

    return {
        "input_path": str(input_path),
        "raw_records_read": raw_records_read,
        "food_ordering_records_reviewed": reviewed_counts[FOOD_ORDERING_DOMAIN],
        "food_ordering_candidates_kept": kept_counts[FOOD_ORDERING_DOMAIN],
        "restaurant_search_records_reviewed": reviewed_counts[RESTAURANT_SEARCH_DOMAIN],
        "restaurant_search_candidates_kept": kept_counts[RESTAURANT_SEARCH_DOMAIN],
        "category_counts": dict(sorted(category_counts.items())),
        "food_output_path": str(food_output_path),
        "restaurant_output_path": str(restaurant_output_path),
        "food_output_records_written": len(selected_food),
        "restaurant_output_records_written": len(selected_restaurant),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rule-based filtering for extracted Taskmaster USER utterances."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Input JSONL path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--food-output",
        type=Path,
        default=DEFAULT_FOOD_OUTPUT_PATH,
        help=f"Food-ordering review JSONL path (default: {DEFAULT_FOOD_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--restaurant-output",
        type=Path,
        default=DEFAULT_RESTAURANT_OUTPUT_PATH,
        help=(
            "Restaurant-search review JSONL path "
            f"(default: {DEFAULT_RESTAURANT_OUTPUT_PATH})"
        ),
    )
    parser.add_argument(
        "--max-food-ordering-candidates",
        type=int,
        default=DEFAULT_MAX_FOOD_ORDERING_CANDIDATES,
        help="Maximum number of food-ordering review records to write.",
    )
    parser.add_argument(
        "--max-restaurant-search-candidates",
        type=int,
        default=DEFAULT_MAX_RESTAURANT_SEARCH_CANDIDATES,
        help="Maximum number of restaurant-search review records to write.",
    )
    return parser.parse_args(argv)


def _print_summary(summary: Dict[str, Any]) -> None:
    print("Taskmaster candidate filtering complete.")
    print(f"Input path: {summary['input_path']}")
    print(f"Raw records read: {summary['raw_records_read']}")
    print(f"Food-ordering records reviewed: {summary['food_ordering_records_reviewed']}")
    print(f"Food-ordering candidates kept: {summary['food_ordering_candidates_kept']}")
    print(
        "Food-ordering review records written: "
        f"{summary['food_output_records_written']}"
    )
    print(
        "Restaurant-search records reviewed: "
        f"{summary['restaurant_search_records_reviewed']}"
    )
    print(
        "Restaurant-search candidates kept: "
        f"{summary['restaurant_search_candidates_kept']}"
    )
    print(
        "Restaurant-search review records written: "
        f"{summary['restaurant_output_records_written']}"
    )
    print("Counts per candidate_category:")
    for category, count in summary["category_counts"].items():
        print(f"- {category}: {count}")
    print(f"Food output path: {summary['food_output_path']}")
    print(f"Restaurant output path: {summary['restaurant_output_path']}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not Path(args.input).exists():
        print("Taskmaster candidate filtering failed. Missing input file:", file=sys.stderr)
        print(f"- {Path(args.input)}", file=sys.stderr)
        return 1

    try:
        summary = filter_candidates(
            input_path=Path(args.input),
            food_output_path=Path(args.food_output),
            restaurant_output_path=Path(args.restaurant_output),
            max_food_ordering_candidates=args.max_food_ordering_candidates,
            max_restaurant_search_candidates=args.max_restaurant_search_candidates,
        )
    except Exception as exc:
        print(f"Taskmaster candidate filtering failed: {exc}", file=sys.stderr)
        return 1

    _print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
