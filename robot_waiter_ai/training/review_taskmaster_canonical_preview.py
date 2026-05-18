"""
Apply manual review metadata to Taskmaster canonical preview rows.

This keeps the preview as an intermediate audit trail and does not create
training data or modify deterministic runtime behavior.
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
    / "taskmaster_food_ordering_adaptation_pilot_canonical_preview.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "taskmaster_food_ordering_adaptation_pilot_canonical_reviewed.jsonl"
)

APPROVED_USER_MESSAGE = "Sipariş vermek istiyorum."
APPROVED_CANONICAL_RESPONSE = "Siparişe eklemek istediğiniz ürünü yazar mısınız?"


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


def review_canonical_preview(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Dict[str, Any]:
    records: List[Dict[str, Any]] = []
    status_counts = Counter()
    input_records_read = 0
    approved_pairs: set[tuple[str, str]] = set()

    for record in _iter_jsonl(input_path):
        input_records_read += 1

        user_message = record.get("turkish_adapted_user_message", "")
        canonical_response = record.get("canonical_response_preview", "")
        deterministic_status = record.get("deterministic_status", "")

        reviewed = dict(record)
        reviewed["include_for_grounded_paraphrase_dataset"] = False
        reviewed["canonical_review_status"] = "needs_manual_review"
        reviewed["canonical_review_notes"] = ""

        if (
            user_message == "Bir kişilik sipariş vermek istiyorum."
            and deterministic_status == "remove_item"
        ):
            reviewed["canonical_review_status"] = "rejected_bad_deterministic_match"
            reviewed["canonical_review_notes"] = (
                "The deterministic route interpreted a one-person order-start message as "
                "remove_item, so this preview is not safe for grounded paraphrase generation."
            )
        elif (
            user_message == APPROVED_USER_MESSAGE
            and canonical_response == APPROVED_CANONICAL_RESPONSE
        ):
            pair_key = (user_message, canonical_response)
            if pair_key not in approved_pairs:
                reviewed["canonical_review_status"] = "approved_canonical_preview"
                reviewed["include_for_grounded_paraphrase_dataset"] = True
                reviewed["canonical_review_notes"] = (
                    "Generic order-start message correctly prompts the user to specify an item."
                )
                approved_pairs.add(pair_key)
            else:
                reviewed["canonical_review_status"] = "rejected_duplicate_low_value"
                reviewed["canonical_review_notes"] = (
                    "Duplicate of an already approved generic order-start preview; low "
                    "additional dataset value."
                )

        status_counts[reviewed["canonical_review_status"]] += 1
        records.append(reviewed)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "input_records_read": input_records_read,
        "status_counts": dict(status_counts),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply manual review metadata to Taskmaster canonical preview rows."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Canonical preview input path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Reviewed preview output path (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not Path(args.input).exists():
        print("Taskmaster canonical review failed. Missing input file:", file=sys.stderr)
        print(f"- {Path(args.input)}", file=sys.stderr)
        return 1

    try:
        summary = review_canonical_preview(
            input_path=Path(args.input),
            output_path=Path(args.output),
        )
    except Exception as exc:
        print(f"Taskmaster canonical review failed: {exc}", file=sys.stderr)
        return 1

    print("Taskmaster canonical review complete.")
    print(f"Input records read: {summary['input_records_read']}")
    for status, count in sorted(summary["status_counts"].items()):
        print(f"{status}: {count}")
    print(f"Output path: {summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
