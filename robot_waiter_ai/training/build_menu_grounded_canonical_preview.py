"""
Build deterministic canonical response previews for reviewed menu-grounded
Turkish user-message seeds.

This produces a review-only intermediate JSONL file. It does not create
training data, paraphrases, or runtime behavior changes.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from robot_waiter_ai.inference.grounded_result_builder import GroundedResultBuilder

_BASE = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "menu_grounded_user_message_seed_reviewed.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "menu_grounded_user_message_canonical_preview.jsonl"
)
MENU_PATH = _BASE / "data" / "menu.yaml"
RESTAURANT_INFO_PATH = _BASE / "data" / "restaurant_info.yaml"
ALLOWED_SEED_STATUSES = {"approved_seed", "approved_probe"}


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


def build_menu_grounded_canonical_preview(
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
    category_counts: Counter[str] = Counter()

    builder = GroundedResultBuilder(
        menu_path=menu_path,
        restaurant_info_path=restaurant_info_path,
    )

    for record in _iter_jsonl(input_path):
        input_records_read += 1

        if record.get("source") != "menu_grounded_seed":
            skipped_records += 1
            warnings.append(
                "Skipped non-menu_grounded_seed record: "
                f"{record.get('intent_category')} / {record.get('turkish_user_message', '')}"
            )
            continue

        if record.get("seed_status") not in ALLOWED_SEED_STATUSES:
            skipped_records += 1
            warnings.append(
                "Skipped non-approved seed row: "
                f"{record.get('intent_category')} / {record.get('turkish_user_message', '')}"
            )
            continue

        if record.get("include_for_canonical_preview") is not True:
            skipped_records += 1
            warnings.append(
                "Skipped row with include_for_canonical_preview != true: "
                f"{record.get('intent_category')} / {record.get('turkish_user_message', '')}"
            )
            continue

        user_message = record.get("turkish_user_message", "")
        if not isinstance(user_message, str) or not user_message.strip():
            skipped_records += 1
            warnings.append(
                "Skipped approved seed row with empty Turkish message: "
                f"{record.get('intent_category')} / {record.get('menu_item_name')}"
            )
            continue

        canonical_response_preview = ""
        deterministic_status = "error"
        preview_notes = "Deterministic çıktı üretilemedi; manuel inceleme gerekli."

        try:
            result = builder.build(user_message)
            canonical_response_preview = result.canonical_response
            deterministic_status = result.action.intent
            preview_notes = (
                "Deterministic canonical preview oluşturuldu; insan incelemesi olmadan "
                "onaylanmamalı."
            )
            if not canonical_response_preview.strip():
                preview_notes = "Deterministic çıktı boş döndü; manuel inceleme gerekli."
        except Exception as exc:
            warnings.append(
                "Deterministic preview failed for "
                f"{record.get('intent_category')} / {user_message}: {exc}"
            )

        preview_records.append(
            {
                "source": record.get("source"),
                "intent_category": record.get("intent_category"),
                "menu_item_name": record.get("menu_item_name"),
                "turkish_user_message": user_message,
                "seed_status": record.get("seed_status"),
                "seed_notes": record.get("seed_notes", ""),
                "include_for_canonical_preview": record.get(
                    "include_for_canonical_preview", False
                ),
                "canonical_response_preview": canonical_response_preview,
                "deterministic_status": deterministic_status,
                "preview_status": "needs_review",
                "include_for_grounded_paraphrase_dataset": False,
                "preview_notes": preview_notes,
            }
        )
        category_counts[str(record.get("intent_category"))] += 1

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
        "category_counts": dict(sorted(category_counts.items())),
        "warnings": warnings,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build deterministic canonical preview rows for reviewed menu-grounded seeds."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Reviewed seed input path (default: {DEFAULT_INPUT_PATH})",
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
        print("Menu-grounded canonical preview build failed. Missing input file:", file=sys.stderr)
        print(f"- {Path(args.input)}", file=sys.stderr)
        return 1

    try:
        summary = build_menu_grounded_canonical_preview(
            input_path=Path(args.input),
            output_path=Path(args.output),
        )
    except Exception as exc:
        print(f"Menu-grounded canonical preview build failed: {exc}", file=sys.stderr)
        return 1

    for warning in summary["warnings"]:
        print(f"Warning: {warning}")

    print("Menu-grounded canonical preview build complete.")
    print(f"Input records read: {summary['input_records_read']}")
    print(f"Preview records written: {summary['preview_records_written']}")
    print(f"Rejected/skipped records: {summary['rejected_or_skipped_records']}")
    print("Counts by intent_category:")
    for category, count in summary["category_counts"].items():
        print(f"- {category}: {count}")
    print(f"Output path: {summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
