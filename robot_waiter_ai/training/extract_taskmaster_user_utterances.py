"""
Extract raw USER utterances from local Taskmaster-2 JSON files.

This utility is intentionally limited to a safe first-stage pipeline:
raw Taskmaster JSON -> reviewable intermediate JSONL.

It does not translate, run model inference, modify runtime behavior,
or write into any existing processed train/valid datasets.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

_BASE = Path(__file__).resolve().parents[1]
TASKMASTER_DIR = _BASE / "datasets" / "external" / "taskmaster" / "TM-2-2020"
DEFAULT_FOOD_ORDERING_PATH = TASKMASTER_DIR / "food-ordering.json"
DEFAULT_RESTAURANT_SEARCH_PATH = TASKMASTER_DIR / "restaurant-search.json"
DEFAULT_OUTPUT_PATH = (
    _BASE / "datasets" / "intermediate" / "taskmaster_user_utterances_raw.jsonl"
)

USER_SPEAKER_LABELS = {
    "USER",
    "CUSTOMER",
    "CLIENT",
    "CALLER",
    "DINER",
    "GUEST",
}


def _normalize_speaker_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^A-Z]+", "_", value.strip().upper()).strip("_")


def _is_user_speaker(turn: Dict[str, Any]) -> bool:
    candidates = [
        turn.get("speaker"),
        turn.get("role"),
        turn.get("participant"),
        turn.get("author"),
    ]
    for candidate in candidates:
        normalized = _normalize_speaker_label(candidate)
        if normalized in USER_SPEAKER_LABELS:
            return True
        if normalized.startswith("USER") or normalized.startswith("CUSTOMER"):
            return True
    return False


def _extract_text(turn: Dict[str, Any]) -> Any:
    for key in ("text", "utterance", "transcript", "content"):
        if key in turn:
            return turn[key]
    return None


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    if len(text) <= 1 and not text.isalnum():
        return None

    if not any(char.isalnum() for char in text):
        return None

    return text


def _iter_utterances(conversation: Dict[str, Any]) -> Iterable[Tuple[int, Dict[str, Any]]]:
    utterances = conversation.get("utterances")
    if isinstance(utterances, list):
        for idx, turn in enumerate(utterances):
            if isinstance(turn, dict):
                yield idx, turn


def extract_records_from_conversations(
    conversations: Sequence[Dict[str, Any]],
    *,
    source_domain: str,
) -> Tuple[List[Dict[str, Any]], int]:
    records: List[Dict[str, Any]] = []
    skipped = 0

    for conversation_idx, conversation in enumerate(conversations):
        if not isinstance(conversation, dict):
            skipped += 1
            continue

        conversation_id = (
            conversation.get("conversation_id")
            or conversation.get("id")
            or conversation.get("dialogue_id")
            or f"{source_domain}_{conversation_idx}"
        )

        for turn_index, turn in _iter_utterances(conversation):
            if not _is_user_speaker(turn):
                continue

            cleaned_text = _clean_text(_extract_text(turn))
            if cleaned_text is None:
                skipped += 1
                continue

            records.append(
                {
                    "source_dataset": "taskmaster_2",
                    "source_domain": source_domain,
                    "conversation_id": str(conversation_id),
                    "turn_index": turn.get("index", turn_index),
                    "original_text": cleaned_text,
                    "status": "raw_extracted",
                    "candidate_intent": None,
                    "keep_candidate": None,
                    "notes": "",
                }
            )

    return records, skipped


def _load_conversations(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return data


def _write_jsonl(records: Sequence[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_intermediate_dataset(
    *,
    food_ordering_path: Path = DEFAULT_FOOD_ORDERING_PATH,
    restaurant_search_path: Path = DEFAULT_RESTAURANT_SEARCH_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Dict[str, Any]:
    food_conversations = _load_conversations(food_ordering_path)
    restaurant_conversations = _load_conversations(restaurant_search_path)

    food_records, food_skipped = extract_records_from_conversations(
        food_conversations,
        source_domain="food_ordering",
    )
    restaurant_records, restaurant_skipped = extract_records_from_conversations(
        restaurant_conversations,
        source_domain="restaurant_search",
    )

    all_records = [*food_records, *restaurant_records]
    _write_jsonl(all_records, output_path)

    return {
        "food_ordering_path": str(food_ordering_path),
        "restaurant_search_path": str(restaurant_search_path),
        "food_ordering_conversations": len(food_conversations),
        "restaurant_search_conversations": len(restaurant_conversations),
        "conversations_read": len(food_conversations) + len(restaurant_conversations),
        "food_ordering_user_utterances": len(food_records),
        "restaurant_search_user_utterances": len(restaurant_records),
        "skipped": food_skipped + restaurant_skipped,
        "output_path": str(output_path),
        "records_written": len(all_records),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract only USER/customer utterances from local Taskmaster-2 JSON files."
    )
    parser.add_argument(
        "--food-ordering",
        type=Path,
        default=DEFAULT_FOOD_ORDERING_PATH,
        help=f"Path to food-ordering.json (default: {DEFAULT_FOOD_ORDERING_PATH})",
    )
    parser.add_argument(
        "--restaurant-search",
        type=Path,
        default=DEFAULT_RESTAURANT_SEARCH_PATH,
        help=f"Path to restaurant-search.json (default: {DEFAULT_RESTAURANT_SEARCH_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output JSONL path (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser.parse_args(argv)


def _print_summary(summary: Dict[str, Any]) -> None:
    print("Taskmaster extraction complete.")
    print(f"Input food-ordering path: {summary['food_ordering_path']}")
    print(f"Input restaurant-search path: {summary['restaurant_search_path']}")
    print(f"Food-ordering conversations read: {summary['food_ordering_conversations']}")
    print(
        "Food-ordering USER utterances extracted: "
        f"{summary['food_ordering_user_utterances']}"
    )
    print(
        "Restaurant-search conversations read: "
        f"{summary['restaurant_search_conversations']}"
    )
    print(
        "Restaurant-search USER utterances extracted: "
        f"{summary['restaurant_search_user_utterances']}"
    )
    print(f"Skipped utterances: {summary['skipped']}")
    print(f"Records written: {summary['records_written']}")
    print(f"Output path: {summary['output_path']}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    missing_paths = [
        path
        for path in (args.food_ordering, args.restaurant_search)
        if not Path(path).exists()
    ]
    if missing_paths:
        print("Taskmaster extraction failed. Missing input files:", file=sys.stderr)
        for path in missing_paths:
            print(f"- {Path(path)}", file=sys.stderr)
        return 1

    try:
        summary = build_intermediate_dataset(
            food_ordering_path=Path(args.food_ordering),
            restaurant_search_path=Path(args.restaurant_search),
            output_path=Path(args.output),
        )
    except Exception as exc:
        print(f"Taskmaster extraction failed: {exc}", file=sys.stderr)
        return 1

    _print_summary(summary)
    if summary["records_written"] == 0:
        print("Warning: output JSONL contains 0 extracted records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
