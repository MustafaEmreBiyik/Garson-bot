"""
Apply a semantic review gate to manually written menu-grounded paraphrase pilot
rows without promoting them into processed datasets.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Sequence

_BASE = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "menu_grounded_paraphrase_manual_pilot_10.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "menu_grounded_paraphrase_manual_pilot_10_reviewed.jsonl"
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


def _norm_text(value: Any) -> str:
    return str(value or "").casefold().strip()


def _contains_forbidden_fact(paraphrase: str, forbidden_terms: Iterable[Any]) -> bool:
    text = _norm_text(paraphrase)
    for term in forbidden_terms:
        normalized = _norm_text(term)
        if not normalized:
            continue
        if normalized in text:
            return True
        if normalized == "discounts" and any(token in text for token in ("indirim", "kampanya")):
            return True
        if normalized == "allergy safety guarantees" and any(
            token in text for token in ("tamamen güvenli", "kesinlikle güvenli", "hiç sorun yok")
        ):
            return True
    return False


def _missing_preserve_term(paraphrase: str, preserve_terms: Iterable[Any]) -> bool:
    text = _norm_text(paraphrase)
    for term in preserve_terms:
        normalized = _norm_text(term)
        if normalized and normalized not in text:
            return True
    return False


def _changes_order_state(record: Dict[str, Any], paraphrase: str) -> bool:
    if str(record.get("intent_category") or "") != "confirm_order":
        return False
    canonical = _norm_text(record.get("canonical_response"))
    text = _norm_text(paraphrase)
    if "onaylıyorum" in canonical and "onaylandı" in text:
        return True
    return False


def review_menu_grounded_paraphrase_manual_pilot(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Dict[str, Any]:
    input_records = list(_iter_jsonl(input_path))
    reviewed_records: list[Dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for record in input_records:
        reviewed = dict(record)
        paraphrase = str(reviewed.get("safe_paraphrase") or "").strip()
        preserve_terms = reviewed.get("must_preserve_terms") or []
        forbidden_terms = reviewed.get("must_not_introduce") or []
        pair = (
            str(reviewed.get("canonical_response") or "").strip(),
            paraphrase,
        )

        if not paraphrase:
            status = "rejected_missing_safe_paraphrase"
            notes = "Safe paraphrase is empty."
            approved = False
        elif _missing_preserve_term(paraphrase, preserve_terms):
            status = "rejected_missing_preserve_term"
            notes = "Safe paraphrase does not preserve all required grounded terms."
            approved = False
        elif _contains_forbidden_fact(paraphrase, forbidden_terms):
            status = "rejected_introduces_forbidden_fact"
            notes = "Safe paraphrase introduces a forbidden fact or unsupported claim."
            approved = False
        elif _changes_order_state(reviewed, paraphrase):
            status = "rejected_changes_order_state"
            notes = "Confirm-order paraphrase changes the order state beyond the canonical response."
            approved = False
        elif pair in seen_pairs:
            status = "rejected_low_value_duplicate"
            notes = "Duplicate canonical_response + safe_paraphrase pair; low additional dataset value."
            approved = False
        else:
            status = "approved_semantic_review"
            notes = "Safe paraphrase preserves required grounded terms without introducing forbidden facts."
            approved = True

        reviewed["semantic_review_status"] = status
        reviewed["semantic_review_notes"] = notes
        reviewed["approved_for_processed_candidate"] = approved
        reviewed["include_for_processed_dataset"] = False
        reviewed_records.append(reviewed)
        seen_pairs.add(pair)

    _write_jsonl(output_path, reviewed_records)

    status_counts = Counter(str(record.get("semantic_review_status") or "") for record in reviewed_records)
    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "input_records_read": len(input_records),
        "records_written": len(reviewed_records),
        "status_counts": dict(sorted(status_counts.items())),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply semantic review labels to menu-grounded manual paraphrase pilot rows."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Manual pilot input path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Reviewed output path (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not Path(args.input).exists():
        print(
            "Menu-grounded paraphrase semantic review failed. Missing input file:",
            file=sys.stderr,
        )
        print(f"- {Path(args.input)}", file=sys.stderr)
        return 1

    try:
        summary = review_menu_grounded_paraphrase_manual_pilot(
            input_path=Path(args.input),
            output_path=Path(args.output),
        )
    except Exception as exc:
        print(f"Menu-grounded paraphrase semantic review failed: {exc}", file=sys.stderr)
        return 1

    print("Menu-grounded paraphrase semantic review complete.")
    print(f"Input records read: {summary['input_records_read']}")
    print(f"Reviewed records written: {summary['records_written']}")
    for status, count in summary["status_counts"].items():
        print(f"{status}: {count}")
    print(f"Output path: {summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
