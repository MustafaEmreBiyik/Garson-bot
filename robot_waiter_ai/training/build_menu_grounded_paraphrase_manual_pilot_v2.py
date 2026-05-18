"""
Build a second 10-row manual safe-paraphrase pilot from remaining
menu-grounded grounded paraphrase candidates.
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
DEFAULT_USED_PILOT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "menu_grounded_paraphrase_manual_pilot_10.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "menu_grounded_paraphrase_manual_pilot_10_v2.jsonl"
)
TARGET_SIZE = 10
PILOT_VERSION = "v2_10"


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
    preserve_terms = record.get("must_preserve_terms") or []
    response = str(record.get("canonical_response") or "")
    caution_bonus = 0 if "teyit" in response.casefold() else 1
    return (-len(preserve_terms), caution_bonus, str(record.get("id") or ""))


def _used_ids(path: Path) -> set[str]:
    return {
        str(record.get("id") or "")
        for record in _iter_jsonl(path)
        if str(record.get("id") or "").strip()
    }


def build_menu_grounded_paraphrase_manual_pilot_v2(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    used_pilot_path: Path = DEFAULT_USED_PILOT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Dict[str, Any]:
    records = list(_iter_jsonl(input_path))
    previously_used_ids = _used_ids(used_pilot_path)

    eligible = [
        record
        for record in records
        if str(record.get("paraphrase_status") or "") == "needs_manual_review"
        and record.get("include_for_processed_dataset") is False
        and str(record.get("id") or "") not in previously_used_ids
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

    ask_ingredient = [
        record for record in eligible if record.get("intent_category") == "ask_ingredient"
    ]
    ask_allergy = [
        record for record in eligible if record.get("intent_category") == "ask_allergy"
    ]
    ask_menu = [
        record for record in eligible if record.get("intent_category") == "ask_menu"
    ]
    remove_item = [
        record for record in eligible if record.get("intent_category") == "remove_item"
    ]
    probes = [
        record
        for record in eligible
        if record.get("candidate_type") == "rejection_probe_response"
    ]
    fallback_info = [
        record for record in eligible if record.get("intent_category") == "ask_price"
    ]
    fallback_confirm = [
        record for record in eligible if record.get("intent_category") == "confirm_order"
    ]

    add_records(ask_ingredient, 3)
    add_records(ask_allergy, 2)
    add_records(ask_menu, 1)
    add_records(remove_item, 2)
    add_records(probes, 2)
    add_records(fallback_info, TARGET_SIZE - len(selected))
    add_records(fallback_confirm, TARGET_SIZE - len(selected))

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
        "used_pilot_path": str(used_pilot_path),
        "output_path": str(output_path),
        "input_records_read": len(records),
        "excluded_used_ids": len(previously_used_ids),
        "records_written": len(selected),
        "intent_counts": dict(sorted(intent_counts.items())),
        "candidate_type_counts": dict(sorted(type_counts.items())),
        "selected_ids": [str(record.get("id") or "") for record in selected],
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a second 10-row manual safe-paraphrase pilot from remaining candidates."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Candidate input path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--used-pilot",
        type=Path,
        default=DEFAULT_USED_PILOT_PATH,
        help=f"Previously used pilot path (default: {DEFAULT_USED_PILOT_PATH})",
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
    missing_paths = [
        path for path in (Path(args.input), Path(args.used_pilot)) if not path.exists()
    ]
    if missing_paths:
        print(
            "Menu-grounded paraphrase manual pilot v2 build failed. Missing input file(s):",
            file=sys.stderr,
        )
        for path in missing_paths:
            print(f"- {path}", file=sys.stderr)
        return 1

    try:
        summary = build_menu_grounded_paraphrase_manual_pilot_v2(
            input_path=Path(args.input),
            used_pilot_path=Path(args.used_pilot),
            output_path=Path(args.output),
        )
    except Exception as exc:
        print(
            f"Menu-grounded paraphrase manual pilot v2 build failed: {exc}",
            file=sys.stderr,
        )
        return 1

    print("Menu-grounded paraphrase manual pilot v2 build complete.")
    print(f"Input records read: {summary['input_records_read']}")
    print(f"Excluded first-pilot IDs: {summary['excluded_used_ids']}")
    print(f"Pilot records written: {summary['records_written']}")
    print("Candidate type distribution:")
    for candidate_type, count in summary["candidate_type_counts"].items():
        print(f"- {candidate_type}: {count}")
    print("Intent distribution:")
    for intent, count in summary["intent_counts"].items():
        print(f"- {intent}: {count}")
    print("Selected IDs:")
    for record_id in summary["selected_ids"]:
        print(f"- {record_id}")
    print(f"Output path: {summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
