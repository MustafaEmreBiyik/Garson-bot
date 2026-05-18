"""
Export only semantically approved menu-grounded paraphrase pilot rows into a
clean approved-candidates intermediate JSONL file.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Sequence

_BASE = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "menu_grounded_paraphrase_manual_pilot_10_reviewed.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "menu_grounded_paraphrase_approved_candidates_v1.jsonl"
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


def _write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def export_approved_grounded_paraphrase_candidates(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Dict[str, Any]:
    input_records = list(_iter_jsonl(input_path))
    approved_records: list[Dict[str, Any]] = []

    for record in input_records:
        if str(record.get("semantic_review_status") or "") != "approved_semantic_review":
            continue
        if record.get("approved_for_processed_candidate") is not True:
            continue
        if not str(record.get("safe_paraphrase") or "").strip():
            continue

        exported = {
            "id": record.get("id"),
            "source": record.get("source"),
            "intent_category": record.get("intent_category"),
            "menu_item_name": record.get("menu_item_name"),
            "user_message": record.get("user_message"),
            "canonical_response": record.get("canonical_response"),
            "safe_paraphrase": record.get("safe_paraphrase"),
            "candidate_type": record.get("candidate_type"),
            "must_preserve_terms": record.get("must_preserve_terms") or [],
            "must_not_introduce": record.get("must_not_introduce") or [],
            "semantic_review_status": record.get("semantic_review_status"),
            "semantic_review_notes": record.get("semantic_review_notes"),
            "approved_for_processed_candidate": True,
            "export_status": "approved_intermediate_candidate",
            "include_for_processed_dataset": False,
        }
        approved_records.append(exported)

    _write_jsonl(output_path, approved_records)

    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "input_records_read": len(input_records),
        "approved_records_exported": len(approved_records),
        "skipped_records": len(input_records) - len(approved_records),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export semantically approved grounded paraphrase candidates."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Reviewed input path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Approved-candidate output path (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not Path(args.input).exists():
        print(
            "Approved grounded paraphrase candidate export failed. Missing input file:",
            file=sys.stderr,
        )
        print(f"- {Path(args.input)}", file=sys.stderr)
        return 1

    try:
        summary = export_approved_grounded_paraphrase_candidates(
            input_path=Path(args.input),
            output_path=Path(args.output),
        )
    except Exception as exc:
        print(
            f"Approved grounded paraphrase candidate export failed: {exc}",
            file=sys.stderr,
        )
        return 1

    print("Approved grounded paraphrase candidate export complete.")
    print(f"Input records read: {summary['input_records_read']}")
    print(f"Approved records exported: {summary['approved_records_exported']}")
    print(f"Skipped records: {summary['skipped_records']}")
    print(f"Output path: {summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
