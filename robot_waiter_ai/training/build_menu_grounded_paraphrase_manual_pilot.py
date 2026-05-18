"""
Build a small manual safe-paraphrase pilot worksheet from menu-grounded
grounded paraphrase candidates.
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
    / "menu_grounded_grounded_paraphrase_candidates.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "menu_grounded_paraphrase_manual_pilot_10.jsonl"
)
TARGET_SIZE = 10
PILOT_VERSION = "v1_10"


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


def _selection_score(record: Dict[str, Any]) -> tuple[int, int, str]:
    response = str(record.get("canonical_response") or "")
    preserve_terms = record.get("must_preserve_terms") or []
    caution_bonus = 0 if "teyit" in response.casefold() else 1
    richness_bonus = -len(preserve_terms)
    return (caution_bonus, richness_bonus, str(record.get("id") or ""))


def build_menu_grounded_paraphrase_manual_pilot(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Dict[str, Any]:
    records = list(_iter_jsonl(input_path))
    input_records_read = len(records)

    eligible = [
        record
        for record in records
        if str(record.get("paraphrase_status") or "") == "needs_manual_review"
        and record.get("include_for_processed_dataset") is False
    ]

    selected: List[Dict[str, Any]] = []
    selected_ids: set[str] = set()
    used_pairs: set[tuple[str, str]] = set()

    def add_records(candidates: List[Dict[str, Any]], limit: int) -> None:
        for record in sorted(candidates, key=_selection_score):
            if len(selected) >= TARGET_SIZE or limit <= 0:
                return
            record_id = str(record.get("id") or "")
            pair = (
                str(record.get("user_message") or "").strip(),
                str(record.get("canonical_response") or "").strip(),
            )
            if record_id in selected_ids or pair in used_pairs:
                continue
            chosen = dict(record)
            chosen["safe_paraphrase"] = ""
            chosen["paraphrase_status"] = "needs_manual_review"
            chosen["include_for_processed_dataset"] = False
            chosen["manual_pilot_version"] = PILOT_VERSION
            selected.append(chosen)
            selected_ids.add(record_id)
            used_pairs.add(pair)
            limit -= 1

    order_candidates = [
        record for record in eligible if record.get("intent_category") == "order_item"
    ]
    info_candidates = [
        record
        for record in eligible
        if record.get("intent_category") in {"ask_price", "ask_menu", "ask_ingredient"}
    ]
    allergy_candidates = [
        record for record in eligible if record.get("intent_category") == "ask_allergy"
    ]
    probe_candidates = [
        record
        for record in eligible
        if record.get("candidate_type") == "rejection_probe_response"
    ]
    other_candidates = [
        record
        for record in eligible
        if record.get("intent_category") in {"remove_item", "confirm_order"}
    ]

    add_records(order_candidates, 2)
    add_records(info_candidates, 3)
    add_records(allergy_candidates, 2)
    add_records(probe_candidates, 1)
    add_records(other_candidates, 2)

    if len(selected) < TARGET_SIZE:
        remaining = [
            record
            for record in eligible
            if str(record.get("id") or "") not in selected_ids
        ]
        add_records(remaining, TARGET_SIZE - len(selected))

    if len(selected) != TARGET_SIZE:
        raise ValueError(
            f"Expected to select exactly {TARGET_SIZE} records, but selected {len(selected)}."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in selected:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    intent_counts = Counter(str(record.get("intent_category")) for record in selected)
    type_counts = Counter(str(record.get("candidate_type")) for record in selected)
    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "input_records_read": input_records_read,
        "records_written": len(selected),
        "intent_counts": dict(sorted(intent_counts.items())),
        "candidate_type_counts": dict(sorted(type_counts.items())),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a 10-row manual safe-paraphrase pilot from menu-grounded candidates."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Candidate input path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Manual pilot output path (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not Path(args.input).exists():
        print(
            "Menu-grounded paraphrase manual pilot build failed. Missing input file:",
            file=sys.stderr,
        )
        print(f"- {Path(args.input)}", file=sys.stderr)
        return 1

    try:
        summary = build_menu_grounded_paraphrase_manual_pilot(
            input_path=Path(args.input),
            output_path=Path(args.output),
        )
    except Exception as exc:
        print(
            f"Menu-grounded paraphrase manual pilot build failed: {exc}",
            file=sys.stderr,
        )
        return 1

    print("Menu-grounded paraphrase manual pilot build complete.")
    print(f"Input records read: {summary['input_records_read']}")
    print(f"Pilot records written: {summary['records_written']}")
    print("Candidate type distribution:")
    for candidate_type, count in summary["candidate_type_counts"].items():
        print(f"- {candidate_type}: {count}")
    print("Intent distribution:")
    for intent, count in summary["intent_counts"].items():
        print(f"- {intent}: {count}")
    print(f"Output path: {summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
