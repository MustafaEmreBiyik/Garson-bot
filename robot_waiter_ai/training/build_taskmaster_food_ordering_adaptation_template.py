"""
Build a manual adaptation worksheet from Taskmaster food-ordering candidates only.

This script does not generate Turkish text, training data, or canonical responses.
It writes a review-only template for human adaptation work.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

_BASE = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = (
    _BASE / "datasets" / "intermediate" / "taskmaster_food_ordering_candidates.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "taskmaster_food_ordering_adaptation_template.jsonl"
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


def build_adaptation_template(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Dict[str, Any]:
    template_records: List[Dict[str, Any]] = []
    records_read = 0
    records_written = 0

    for record in _iter_jsonl(input_path):
        records_read += 1

        if record.get("source_domain") != "food_ordering":
            continue
        if record.get("keep_candidate") is not True:
            continue
        if record.get("adaptation_eligible") is False:
            continue

        template_records.append(
            {
                "source_dataset": record.get("source_dataset"),
                "source_domain": record.get("source_domain"),
                "conversation_id": record.get("conversation_id"),
                "turn_index": record.get("turn_index"),
                "original_text": record.get("original_text"),
                "candidate_category": record.get("candidate_category"),
                "turkish_adapted_user_message": "",
                "adaptation_status": "needs_manual_review",
                "adaptation_notes": "",
                "include_for_future_grounded_generation": False,
            }
        )
        records_written += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in template_records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "records_read": records_read,
        "records_written": records_written,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a manual adaptation template from food-ordering Taskmaster candidates."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Food-ordering candidate JSONL path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Adaptation template JSONL path (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not Path(args.input).exists():
        print("Taskmaster adaptation template build failed. Missing input file:", file=sys.stderr)
        print(f"- {Path(args.input)}", file=sys.stderr)
        return 1

    try:
        summary = build_adaptation_template(
            input_path=Path(args.input),
            output_path=Path(args.output),
        )
    except Exception as exc:
        print(f"Taskmaster adaptation template build failed: {exc}", file=sys.stderr)
        return 1

    print("Taskmaster food-ordering adaptation template build complete.")
    print(f"Input path: {summary['input_path']}")
    print(f"Records read: {summary['records_read']}")
    print(f"Template records written: {summary['records_written']}")
    print(f"Output path: {summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
