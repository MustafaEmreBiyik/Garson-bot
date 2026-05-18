"""
Refine the menu-grounded Turkish user-message seed worksheet into a smaller,
more balanced review-only worksheet.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

_BASE = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = (
    _BASE / "datasets" / "intermediate" / "menu_grounded_user_message_seed_review.jsonl"
)
DEFAULT_OUTPUT_PATH = (
    _BASE
    / "datasets"
    / "intermediate"
    / "menu_grounded_user_message_seed_review_refined.jsonl"
)

CATEGORY_LIMITS = {
    "order_item": 8,
    "ask_price": 8,
    "ask_ingredient": 6,
    "ask_allergy": 6,
    "ask_menu": 4,
    "modify_order": 4,
    "remove_item": 3,
    "confirm_order": 3,
    "unsupported_item_probe": 4,
    "off_topic_rejection_probe": 2,
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


def _refine_message(record: Dict[str, Any]) -> str:
    message = str(record.get("turkish_user_message", "")).strip()
    item = record.get("menu_item_name")
    category = record.get("intent_category")

    custom_map = {
        ("ask_menu", "Menüde neler var?"): "Menüde neler var?",
        ("ask_menu", "İçecek seçenekleriniz neler?"): "Menüde hangi içecekler var?",
        ("ask_menu", "Çorba çeşitleriniz neler?"): "Hangi çorbalar var?",
        ("ask_menu", "Ana yemeklerde neler önerirsiniz?"): "Ana yemeklerde neler var?",
        ("confirm_order", "Siparişimi onaylamak istiyorum."): "Siparişimi onaylamak istiyorum.",
        ("confirm_order", "Evet, siparişimi onaylıyorum."): "Evet, siparişi onaylıyorum.",
        ("confirm_order", "Bu sipariş doğru, devam edelim."): "Bu kadar, siparişi onaylayabiliriz.",
    }
    if (category, message) in custom_map:
        return custom_map[(category, message)]

    if category == "modify_order" and item == "Mercimek Çorbası":
        return "Mercimek Çorbası soğansız olsun."
    if category == "modify_order" and item == "Domates Çorbası":
        return "Domates Çorbası için ekstra sos ekleyebilir miyim?"
    if category == "modify_order" and item == "Ayran":
        return "Ayran yerine Limonata alabilir miyim?"
    if category == "modify_order" and item == "Limonata":
        return "Limonata şekersiz hazırlanabilir mi?"

    if category == "remove_item" and item:
        return f"Siparişimden {item}'ı çıkarabilir misiniz?"

    if category == "ask_allergy" and item == "Ayran":
        return "Ayran süt ürünü içeriyor mu?"

    return message


def _category_sort_key(record: Dict[str, Any]) -> tuple[int, str]:
    item = record.get("menu_item_name") or ""
    message = str(record.get("turkish_user_message", ""))
    return (0 if item else 1, message)


def refine_menu_grounded_user_message_seed(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Dict[str, Any]:
    grouped: dict[str, List[Dict[str, Any]]] = defaultdict(list)
    input_records_read = 0

    for record in _iter_jsonl(input_path):
        input_records_read += 1
        grouped[str(record.get("intent_category"))].append(record)

    selected: List[Dict[str, Any]] = []
    for category, limit in CATEGORY_LIMITS.items():
        candidates = sorted(grouped.get(category, []), key=_category_sort_key)
        for record in candidates[:limit]:
            refined = dict(record)
            refined["turkish_user_message"] = _refine_message(record)
            refined["seed_status"] = "needs_review"
            refined["include_for_canonical_preview"] = False
            selected.append(refined)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in selected:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    category_counts = Counter(record["intent_category"] for record in selected)
    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "input_records_read": input_records_read,
        "records_written": len(selected),
        "category_counts": dict(sorted(category_counts.items())),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refine the menu-grounded Turkish user-message seed worksheet."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Input review JSONL path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Refined output JSONL path (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        summary = refine_menu_grounded_user_message_seed(
            input_path=Path(args.input),
            output_path=Path(args.output),
        )
    except Exception as exc:
        print(f"Menu-grounded seed refinement failed: {exc}")
        return 1

    print("Menu-grounded user-message seed refinement complete.")
    print(f"Input records read: {summary['input_records_read']}")
    print(f"Records written: {summary['records_written']}")
    print("Intent category distribution:")
    for category, count in summary["category_counts"].items():
        print(f"- {category}: {count}")
    print(f"Output path: {summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
