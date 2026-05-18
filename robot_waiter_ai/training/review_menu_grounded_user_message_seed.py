"""
Add conservative manual-review metadata to the refined menu-grounded Turkish
user-message seed worksheet without generating any canonical responses.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Sequence

_BASE = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "menu_grounded_user_message_seed_review_refined.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "menu_grounded_user_message_seed_reviewed.jsonl"
)

SUPPORTED_CATEGORIES = {
    "order_item",
    "ask_price",
    "ask_ingredient",
    "ask_allergy",
    "ask_menu",
    "modify_order",
    "remove_item",
    "confirm_order",
}
PROBE_CATEGORIES = {"unsupported_item_probe", "off_topic_rejection_probe"}
ITEM_OPTIONAL_CATEGORIES = {"ask_menu", "confirm_order"}


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


def _review_record(record: Dict[str, Any]) -> Dict[str, Any]:
    reviewed = dict(record)
    category = str(record.get("intent_category") or "").strip()
    message = str(record.get("turkish_user_message") or "").strip()
    menu_item_name = record.get("menu_item_name")

    reviewed["include_for_canonical_preview"] = False

    if not category:
        reviewed["seed_status"] = "rejected_seed"
        reviewed["seed_notes"] = "Missing intent_category; row is not safe for canonical preview."
        return reviewed

    if not message:
        reviewed["seed_status"] = "rejected_seed"
        reviewed["seed_notes"] = "Empty Turkish user message; row is not safe for canonical preview."
        return reviewed

    if category in SUPPORTED_CATEGORIES:
        if (
            category not in ITEM_OPTIONAL_CATEGORIES
            and not str(menu_item_name or "").strip()
        ):
            reviewed["seed_status"] = "rejected_seed"
            reviewed["seed_notes"] = (
                "Missing supported menu_item_name for a menu-grounded seed row."
            )
            return reviewed

        reviewed["seed_status"] = "approved_seed"
        reviewed["include_for_canonical_preview"] = True
        reviewed["seed_notes"] = (
            "Supported menu-grounded user message; safe to review with deterministic "
            "canonical preview."
        )
        return reviewed

    if category == "unsupported_item_probe":
        reviewed["seed_status"] = "approved_probe"
        reviewed["include_for_canonical_preview"] = True
        reviewed["seed_notes"] = (
            "Unsupported item probe; intended to test deterministic rejection behavior, "
            "not supported ordering."
        )
        return reviewed

    if category == "off_topic_rejection_probe":
        reviewed["seed_status"] = "approved_probe"
        reviewed["include_for_canonical_preview"] = True
        reviewed["seed_notes"] = (
            "Off-topic probe; intended to test deterministic off-topic rejection behavior."
        )
        return reviewed

    reviewed["seed_status"] = "rejected_seed"
    reviewed["seed_notes"] = (
        f"Unsupported or ambiguous intent_category '{category}'; row requires manual rewrite."
    )
    return reviewed


def review_menu_grounded_user_message_seed(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Dict[str, Any]:
    reviewed_records = []
    input_records_read = 0

    for record in _iter_jsonl(input_path):
        input_records_read += 1
        reviewed_records.append(_review_record(record))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in reviewed_records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    status_counts = Counter(record["seed_status"] for record in reviewed_records)
    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "input_records_read": input_records_read,
        "records_written": len(reviewed_records),
        "status_counts": dict(sorted(status_counts.items())),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review the refined menu-grounded Turkish user-message seed worksheet."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Input refined review JSONL path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Reviewed output JSONL path (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        summary = review_menu_grounded_user_message_seed(
            input_path=Path(args.input),
            output_path=Path(args.output),
        )
    except Exception as exc:
        print(f"Menu-grounded seed review failed: {exc}")
        return 1

    print("Menu-grounded user-message seed review complete.")
    print(f"Input records read: {summary['input_records_read']}")
    print(f"Records written: {summary['records_written']}")
    print("Seed status counts:")
    for status, count in summary["status_counts"].items():
        print(f"- {status}: {count}")
    print(f"Output path: {summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
