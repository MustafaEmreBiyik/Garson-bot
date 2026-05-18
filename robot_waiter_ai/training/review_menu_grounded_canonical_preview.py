"""
Apply human-style review metadata to menu-grounded deterministic canonical
preview rows.

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
    / "menu_grounded_user_message_canonical_preview.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "menu_grounded_user_message_canonical_reviewed.jsonl"
)

SUPPORTED_CATEGORIES = {
    "order_item",
    "ask_price",
    "ask_ingredient",
    "ask_allergy",
    "ask_menu",
    "modify_order",
    "remove_item",
    "confirm_order",
}


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


def _normalized(value: Any) -> str:
    return str(value or "").strip().lower()


def _contains_any(text: str, phrases: Sequence[str]) -> bool:
    normalized = _normalized(text)
    return any(phrase in normalized for phrase in phrases)


def _is_rejection_response(canonical_response: str) -> bool:
    return _contains_any(
        canonical_response,
        [
            "menümüzde bulunmuyor",
            "yardımcı olamıyorum",
            "menü veya siparişle ilgili",
        ],
    )


def _has_price_info(canonical_response: str) -> bool:
    return _contains_any(
        canonical_response,
        [
            "fiyat:",
            " tl",
            "tl.",
        ],
    )


def _has_allergy_caution(canonical_response: str) -> bool:
    return _contains_any(
        canonical_response,
        [
            "lütfen mutfakla teyit ediniz",
            "alerjen bilgisi bulunamadı",
        ],
    )


def _guarantees_allergy_safety(canonical_response: str) -> bool:
    return _contains_any(
        canonical_response,
        [
            "tamamen güvenli",
            "kesinlikle güvenli",
            "alerjen içermez",
            "hiç içermez",
        ],
    )


def _approve(reviewed: Dict[str, Any], note: str, *, probe: bool = False) -> None:
    reviewed["canonical_review_status"] = (
        "approved_rejection_probe" if probe else "approved_canonical_preview"
    )
    reviewed["canonical_review_notes"] = note
    reviewed["include_for_grounded_paraphrase_dataset"] = True


def _reject(reviewed: Dict[str, Any], note: str, *, duplicate: bool = False) -> None:
    reviewed["canonical_review_status"] = (
        "rejected_low_value_or_duplicate"
        if duplicate
        else "rejected_bad_deterministic_match"
    )
    reviewed["canonical_review_notes"] = note
    reviewed["include_for_grounded_paraphrase_dataset"] = False


def review_menu_grounded_canonical_preview(
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

        reviewed = dict(record)
        reviewed["canonical_review_status"] = "needs_manual_review"
        reviewed["canonical_review_notes"] = ""
        reviewed["include_for_grounded_paraphrase_dataset"] = False

        category = str(record.get("intent_category") or "").strip()
        user_message = str(record.get("turkish_user_message") or "").strip()
        canonical_response = str(record.get("canonical_response_preview") or "").strip()
        deterministic_status = str(record.get("deterministic_status") or "").strip()
        menu_item_name = str(record.get("menu_item_name") or "").strip()

        pair_key = (user_message, canonical_response)
        if pair_key in approved_pairs:
            _reject(
                reviewed,
                "Duplicate of an already approved canonical preview pair; low additional dataset value.",
                duplicate=True,
            )
            status_counts[reviewed["canonical_review_status"]] += 1
            records.append(reviewed)
            continue

        if not user_message or not canonical_response or not category:
            reviewed["canonical_review_notes"] = (
                "Missing required preview fields; row needs manual inspection."
            )
            status_counts[reviewed["canonical_review_status"]] += 1
            records.append(reviewed)
            continue

        if category == "unsupported_item_probe":
            if _contains_any(canonical_response, ["menümüzde bulunmuyor"]):
                _approve(
                    reviewed,
                    "Unsupported item probe correctly rejected as unavailable on the menu.",
                    probe=True,
                )
                approved_pairs.add(pair_key)
            else:
                _reject(
                    reviewed,
                    "Unsupported item probe did not receive a clear unsupported-menu rejection.",
                )
        elif category == "off_topic_rejection_probe":
            if _contains_any(
                canonical_response,
                ["yardımcı olamıyorum", "menü veya siparişle ilgili"],
            ):
                _approve(
                    reviewed,
                    "Off-topic probe correctly redirected back to restaurant/menu scope.",
                    probe=True,
                )
                approved_pairs.add(pair_key)
            else:
                _reject(
                    reviewed,
                    "Off-topic probe did not receive a clear refusal or scope redirect.",
                )
        elif category == "order_item":
            if deterministic_status == "add_item" and _contains_any(
                canonical_response, ["ekledim:"]
            ) and (not menu_item_name or _normalized(menu_item_name) in _normalized(canonical_response)):
                _approve(
                    reviewed,
                    "Supported order-item request correctly adds the requested menu item.",
                )
                approved_pairs.add(pair_key)
            else:
                _reject(
                    reviewed,
                    "Order-item request did not receive a clear add-item canonical response.",
                )
        elif category == "ask_price":
            if _has_price_info(canonical_response) and deterministic_status in {
                "price_question",
                "menu_question",
            }:
                note = "Grounded price response is relevant to the user question."
                if deterministic_status == "menu_question":
                    note = (
                        "Response contains grounded price information despite broader deterministic status."
                    )
                _approve(reviewed, note)
                approved_pairs.add(pair_key)
            else:
                _reject(
                    reviewed,
                    "Price question did not receive a grounded price-bearing canonical response.",
                )
        elif category == "ask_ingredient":
            if deterministic_status == "menu_question" and not _is_rejection_response(
                canonical_response
            ) and (
                (menu_item_name and _normalized(menu_item_name) in _normalized(canonical_response))
                or _has_price_info(canonical_response)
            ):
                _approve(
                    reviewed,
                    "Ingredient question received a grounded item-description response suitable for review.",
                )
                approved_pairs.add(pair_key)
            else:
                _reject(
                    reviewed,
                    "Ingredient question did not receive a grounded item-description response.",
                )
        elif category == "ask_allergy":
            if _guarantees_allergy_safety(canonical_response):
                _reject(
                    reviewed,
                    "Allergy response makes an unsafe definitive safety guarantee.",
                )
            elif deterministic_status == "menu_question" and _has_allergy_caution(
                canonical_response
            ):
                _approve(
                    reviewed,
                    "Allergy question received a cautious grounded response without a safety guarantee.",
                )
                approved_pairs.add(pair_key)
            else:
                _reject(
                    reviewed,
                    "Allergy question did not preserve enough caution for later grounded use.",
                )
        elif category == "ask_menu":
            if deterministic_status == "menu_question" and not _is_rejection_response(
                canonical_response
            ) and _contains_any(canonical_response, ["kategoriler:", ":", "fiyat:"]):
                _approve(
                    reviewed,
                    "Menu question received a grounded menu-oriented response.",
                )
                approved_pairs.add(pair_key)
            else:
                _reject(
                    reviewed,
                    "Menu question did not receive a clearly relevant menu-oriented response.",
                )
        elif category == "modify_order":
            if deterministic_status == "modify_item":
                _approve(
                    reviewed,
                    "Modification request received an explicit modification-aware response.",
                )
                approved_pairs.add(pair_key)
            else:
                _reject(
                    reviewed,
                    "Modification request routed to a non-modification deterministic response.",
                )
        elif category == "remove_item":
            if deterministic_status == "remove_item" and _contains_any(
                canonical_response, ["çıkardım:"]
            ):
                _approve(
                    reviewed,
                    "Remove-item request correctly produced a removal response.",
                )
                approved_pairs.add(pair_key)
            else:
                _reject(
                    reviewed,
                    "Remove-item request did not receive a clear removal response.",
                )
        elif category == "confirm_order":
            if deterministic_status == "confirm_order" and _contains_any(
                canonical_response, ["siparişinizi onaylıyorum", "toplam:"]
            ):
                _approve(
                    reviewed,
                    "Confirm-order request received a grounded confirmation summary.",
                )
                approved_pairs.add(pair_key)
            else:
                _reject(
                    reviewed,
                    "Confirm-order request did not receive a clear confirmation summary.",
                )
        else:
            reviewed["canonical_review_notes"] = (
                f"Unhandled intent_category '{category}'; row needs manual review."
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
        "status_counts": dict(sorted(status_counts.items())),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply review metadata to menu-grounded deterministic canonical preview rows."
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
        print("Menu-grounded canonical review failed. Missing input file:", file=sys.stderr)
        print(f"- {Path(args.input)}", file=sys.stderr)
        return 1

    try:
        summary = review_menu_grounded_canonical_preview(
            input_path=Path(args.input),
            output_path=Path(args.output),
        )
    except Exception as exc:
        print(f"Menu-grounded canonical review failed: {exc}", file=sys.stderr)
        return 1

    print("Menu-grounded canonical review complete.")
    print(f"Input records read: {summary['input_records_read']}")
    for status, count in summary["status_counts"].items():
        print(f"{status}: {count}")
    print(f"Output path: {summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
