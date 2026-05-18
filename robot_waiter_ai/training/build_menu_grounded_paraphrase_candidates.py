"""
Build a review-only grounded paraphrase candidate worksheet from approved
menu-grounded canonical review rows.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

_BASE = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "menu_grounded_user_message_canonical_reviewed.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "menu_grounded_grounded_paraphrase_candidates.jsonl"
)
ALLOWED_STATUSES = {"approved_canonical_preview", "approved_rejection_probe"}
PRICE_PATTERN = re.compile(r"\b\d+\.\d{2}\s*TL\b")
QUANTITY_PATTERN = re.compile(r"\b\d+\s*x\s+([^\.\n]+)")
BASE_MUST_NOT_INTRODUCE = [
    "unsupported menu items",
    "new prices",
    "discounts",
    "stock claims",
    "preparation time",
    "delivery/pickup promises",
    "allergy safety guarantees",
    "ingredients not present in canonical_response",
    "order state changes not present in canonical_response",
]


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


def _dedupe_preserve_terms(terms: List[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for term in terms:
        normalized = term.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(normalized)
    return ordered


def _extract_preserve_terms(record: Dict[str, Any]) -> List[str]:
    canonical_response = str(
        record.get("canonical_response") or record.get("canonical_response_preview") or ""
    )
    preserve_terms: List[str] = []

    menu_item_name = str(record.get("menu_item_name") or "").strip()
    if menu_item_name:
        preserve_terms.append(menu_item_name)

    for match in PRICE_PATTERN.findall(canonical_response):
        preserve_terms.append(match.strip())

    if "Lütfen mutfakla teyit ediniz." in canonical_response:
        preserve_terms.append("Lütfen mutfakla teyit ediniz.")
    elif "teyit" in canonical_response.casefold():
        preserve_terms.append("teyit")

    quantity_match = QUANTITY_PATTERN.search(canonical_response)
    if quantity_match:
        preserve_terms.append(quantity_match.group(0).strip())

    if record.get("candidate_type") == "rejection_probe_response":
        if "menümüzde bulunmuyor" in canonical_response:
            preserve_terms.append("menümüzde bulunmuyor")
        elif "yardımcı olamıyorum" in canonical_response:
            preserve_terms.append("yardımcı olamıyorum")
        elif "menü veya siparişle ilgili" in canonical_response:
            preserve_terms.append("menü veya siparişle ilgili")

    return _dedupe_preserve_terms(preserve_terms)


def _candidate_type_for(status: str) -> str:
    if status == "approved_rejection_probe":
        return "rejection_probe_response"
    return "supported_menu_response"


def build_menu_grounded_paraphrase_candidates(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Dict[str, Any]:
    input_records_read = 0
    candidate_records: List[Dict[str, Any]] = []
    skipped_records = 0
    type_counts: Counter[str] = Counter()

    for record in _iter_jsonl(input_path):
        input_records_read += 1

        canonical_review_status = str(record.get("canonical_review_status") or "")
        if canonical_review_status not in ALLOWED_STATUSES:
            skipped_records += 1
            continue

        if record.get("include_for_grounded_paraphrase_dataset") is not True:
            skipped_records += 1
            continue

        candidate_type = _candidate_type_for(canonical_review_status)
        candidate = {
            "id": f"mgp_{len(candidate_records) + 1:03d}",
            "source": "menu_grounded_seed",
            "intent_category": record.get("intent_category"),
            "menu_item_name": record.get("menu_item_name"),
            "user_message": record.get("turkish_user_message"),
            "canonical_response": record.get("canonical_response_preview"),
            "candidate_type": candidate_type,
            "canonical_review_status": canonical_review_status,
            "canonical_review_notes": record.get("canonical_review_notes", ""),
            "must_preserve_terms": [],
            "must_not_introduce": list(BASE_MUST_NOT_INTRODUCE),
            "safe_paraphrase": "",
            "paraphrase_status": "needs_manual_review",
            "include_for_processed_dataset": False,
        }
        candidate["must_preserve_terms"] = _extract_preserve_terms(candidate)
        candidate_records.append(candidate)
        type_counts[candidate_type] += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in candidate_records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "input_records_read": input_records_read,
        "candidate_records_written": len(candidate_records),
        "skipped_records": skipped_records,
        "candidate_type_counts": dict(sorted(type_counts.items())),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build review-only menu-grounded grounded paraphrase candidates."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Reviewed canonical input path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Candidate output path (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not Path(args.input).exists():
        print(
            "Menu-grounded grounded paraphrase candidate build failed. Missing input file:",
            file=sys.stderr,
        )
        print(f"- {Path(args.input)}", file=sys.stderr)
        return 1

    try:
        summary = build_menu_grounded_paraphrase_candidates(
            input_path=Path(args.input),
            output_path=Path(args.output),
        )
    except Exception as exc:
        print(
            f"Menu-grounded grounded paraphrase candidate build failed: {exc}",
            file=sys.stderr,
        )
        return 1

    print("Menu-grounded grounded paraphrase candidate build complete.")
    print(f"Input records read: {summary['input_records_read']}")
    print(f"Candidate records written: {summary['candidate_records_written']}")
    print(f"Skipped records: {summary['skipped_records']}")
    print("Candidate type distribution:")
    for candidate_type, count in summary["candidate_type_counts"].items():
        print(f"- {candidate_type}: {count}")
    print(f"Output path: {summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
