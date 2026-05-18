"""
Build a deterministic canonical response preview for accepted Taskmaster adaptations.

This produces a review-only intermediate JSONL file. It does not create training
data, paraphrases, or runtime behavior changes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from robot_waiter_ai.inference.grounded_result_builder import GroundedResultBuilder

_BASE = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "taskmaster_food_ordering_adaptation_pilot_accepted.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "taskmaster_food_ordering_adaptation_pilot_canonical_preview.jsonl"
)
MENU_PATH = _BASE / "data" / "menu.yaml"
RESTAURANT_INFO_PATH = _BASE / "data" / "restaurant_info.yaml"


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


def build_canonical_preview(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    menu_path: Path = MENU_PATH,
    restaurant_info_path: Path = RESTAURANT_INFO_PATH,
) -> Dict[str, Any]:
    input_records_read = 0
    preview_records: List[Dict[str, Any]] = []
    skipped_records = 0
    warnings: List[str] = []

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
            warnings.append(
                "Skipped non-accepted record: "
                f"{record.get('conversation_id')} / {record.get('turn_index')}"
            )
            continue

        if record.get("include_for_future_grounded_generation") is not True:
            skipped_records += 1
            warnings.append(
                "Skipped accepted record with include_for_future_grounded_generation != true: "
                f"{record.get('conversation_id')} / {record.get('turn_index')}"
            )
            continue

        user_message = record.get("turkish_adapted_user_message", "")
        if not isinstance(user_message, str) or not user_message.strip():
            skipped_records += 1
            warnings.append(
                "Skipped accepted record with empty Turkish adaptation: "
                f"{record.get('conversation_id')} / {record.get('turn_index')}"
            )
            continue

        canonical_response_preview = ""
        deterministic_status = "error"
        preview_notes = "Deterministic çıktı üretilemedi; manuel inceleme gerekli."

        try:
            builder = GroundedResultBuilder(
                menu_path=menu_path,
                restaurant_info_path=restaurant_info_path,
            )
            result = builder.build(user_message)
            canonical_response_preview = result.canonical_response
            deterministic_status = result.action.intent
            preview_notes = (
                "Deterministic canonical preview oluşturuldu; insan incelemesi olmadan "
                "onaylanmamalı."
            )
            if not canonical_response_preview.strip():
                preview_notes = (
                    "Deterministic çıktı boş döndü; manuel inceleme gerekli."
                )
        except Exception as exc:
            warnings.append(
                "Deterministic preview failed for "
                f"{record.get('conversation_id')} / {record.get('turn_index')}: {exc}"
            )

        preview_records.append(
            {
                "source_dataset": record.get("source_dataset"),
                "source_domain": record.get("source_domain"),
                "conversation_id": record.get("conversation_id"),
                "turn_index": record.get("turn_index"),
                "original_text": record.get("original_text"),
                "candidate_category": record.get("candidate_category"),
                "turkish_adapted_user_message": user_message,
                "adaptation_notes": record.get("adaptation_notes", ""),
                "canonical_response_preview": canonical_response_preview,
                "deterministic_status": deterministic_status,
                "preview_status": "needs_review",
                "include_for_grounded_paraphrase_dataset": False,
                "preview_notes": preview_notes,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in preview_records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "input_records_read": input_records_read,
        "preview_records_written": len(preview_records),
        "rejected_or_skipped_records": skipped_records,
        "warnings": warnings,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build deterministic canonical preview rows for accepted Taskmaster adaptations."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Accepted adaptation input path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Canonical preview output path (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not Path(args.input).exists():
        print("Taskmaster canonical preview build failed. Missing input file:", file=sys.stderr)
        print(f"- {Path(args.input)}", file=sys.stderr)
        return 1

    try:
        summary = build_canonical_preview(
            input_path=Path(args.input),
            output_path=Path(args.output),
        )
    except Exception as exc:
        print(f"Taskmaster canonical preview build failed: {exc}", file=sys.stderr)
        return 1

    for warning in summary["warnings"]:
        print(f"Warning: {warning}")

    print("Taskmaster canonical preview build complete.")
    print(f"Input records read: {summary['input_records_read']}")
    print(f"Preview records written: {summary['preview_records_written']}")
    print(f"Rejected/skipped records: {summary['rejected_or_skipped_records']}")
    print(f"Output path: {summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
