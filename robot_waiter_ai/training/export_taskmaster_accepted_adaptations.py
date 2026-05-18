"""
Export accepted-only Taskmaster food-ordering manual adaptations.

This script produces a clean intermediate JSONL file for later reviewed steps.
It does not generate training data, assistant responses, or canonical outputs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

_BASE = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "taskmaster_food_ordering_adaptation_pilot_30.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "taskmaster_food_ordering_adaptation_pilot_accepted.jsonl"
)


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


def export_accepted_adaptations(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Dict[str, Any]:
    input_records_read = 0
    skipped_records = 0
    warnings: List[str] = []
    exported_records: List[Dict[str, Any]] = []

    for record in _iter_jsonl(input_path):
        input_records_read += 1

        if record.get("source_domain") != "food_ordering":
            skipped_records += 1
            warnings.append(
                "Skipped non-food_ordering record: "
                f"{record.get('conversation_id')} / {record.get('turn_index')}"
            )
            continue

        if record.get("adaptation_status") != "accepted_adapted":
            skipped_records += 1
            continue

        if record.get("include_for_future_grounded_generation") is not True:
            skipped_records += 1
            warnings.append(
                "Skipped accepted record with include_for_future_grounded_generation != true: "
                f"{record.get('conversation_id')} / {record.get('turn_index')}"
            )
            continue

        turkish_message = record.get("turkish_adapted_user_message", "")
        if not isinstance(turkish_message, str) or not turkish_message.strip():
            skipped_records += 1
            warnings.append(
                "Skipped accepted record with empty Turkish adaptation: "
                f"{record.get('conversation_id')} / {record.get('turn_index')}"
            )
            continue

        exported_records.append(
            {
                "source_dataset": record.get("source_dataset"),
                "source_domain": record.get("source_domain"),
                "conversation_id": record.get("conversation_id"),
                "turn_index": record.get("turn_index"),
                "original_text": record.get("original_text"),
                "candidate_category": record.get("candidate_category"),
                "turkish_adapted_user_message": turkish_message,
                "adaptation_status": record.get("adaptation_status"),
                "adaptation_notes": record.get("adaptation_notes"),
                "include_for_future_grounded_generation": record.get(
                    "include_for_future_grounded_generation"
                ),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in exported_records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "input_records_read": input_records_read,
        "accepted_records_exported": len(exported_records),
        "rejected_or_skipped_records": skipped_records,
        "warnings": warnings,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export accepted-only Taskmaster manual adaptation rows."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Pilot worksheet input path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Accepted-only output path (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not Path(args.input).exists():
        print("Taskmaster accepted export failed. Missing input file:", file=sys.stderr)
        print(f"- {Path(args.input)}", file=sys.stderr)
        return 1

    try:
        summary = export_accepted_adaptations(
            input_path=Path(args.input),
            output_path=Path(args.output),
        )
    except Exception as exc:
        print(f"Taskmaster accepted export failed: {exc}", file=sys.stderr)
        return 1

    for warning in summary["warnings"]:
        print(f"Warning: {warning}")

    print("Taskmaster accepted adaptation export complete.")
    print(f"Input records read: {summary['input_records_read']}")
    print(f"Accepted records exported: {summary['accepted_records_exported']}")
    print(f"Rejected/skipped records: {summary['rejected_or_skipped_records']}")
    print(f"Output path: {summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
