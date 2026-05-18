"""
Build a review-only menu-grounded Turkish user-message seed worksheet.

This script generates small deterministic template-based user-message seeds from
the project's own supported menu. The output is an intermediate review artifact,
not training data.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Sequence

import yaml

_BASE = Path(__file__).resolve().parents[1]
MENU_PATH = _BASE / "data" / "menu.yaml"
RESTAURANT_INFO_PATH = _BASE / "data" / "restaurant_info.yaml"
DEFAULT_OUTPUT_PATH = (
    _BASE / "datasets" / "intermediate" / "menu_grounded_user_message_seed_review.jsonl"
)

UNSUPPORTED_ITEM_PROBES = [
    "Pizza sipariş etmek istiyorum.",
    "Hamburger var mı?",
    "Sushi sipariş edebilir miyim?",
    "Taco menünüzde var mı?",
]

OFF_TOPIC_PROBES = [
    "Bana hava durumunu söyler misiniz?",
    "Kripto para hakkında bilgi verir misiniz?",
]


def _load_menu(menu_path: Path) -> List[Dict[str, Any]]:
    data = yaml.safe_load(menu_path.read_text(encoding="utf-8")) or {}
    items = data.get("menu", [])
    if not isinstance(items, list) or not items:
        raise ValueError(f"No menu items found in {menu_path}")
    return [item for item in items if item.get("availability", True)]


def _build_seed_records(menu_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    seen_messages: set[tuple[str, str]] = set()

    def add_record(intent_category: str, turkish_user_message: str, menu_item_name: str | None) -> None:
        key = (intent_category, turkish_user_message)
        if key in seen_messages:
            return
        seen_messages.add(key)
        records.append(
            {
                "source": "menu_grounded_seed",
                "intent_category": intent_category,
                "menu_item_name": menu_item_name,
                "turkish_user_message": turkish_user_message,
                "seed_status": "needs_review",
                "seed_notes": "",
                "include_for_canonical_preview": False,
            }
        )

    for item in menu_items:
        name = str(item["name"])
        add_record("order_item", f"{name} sipariş etmek istiyorum.", name)
        add_record("order_item", f"Bir {name} alabilir miyim?", name)
        add_record("ask_price", f"{name} ne kadar?", name)
        add_record("ask_price", f"{name} fiyatı nedir?", name)

    for item in menu_items[:4]:
        name = str(item["name"])
        add_record("ask_ingredient", f"{name} içinde ne var?", name)
        add_record("ask_ingredient", f"{name} hangi malzemelerle hazırlanıyor?", name)
        add_record("ask_allergy", f"{name} içinde süt ürünü var mı?", name)
        add_record("ask_allergy", f"{name} fındık veya fıstık içeriyor mu?", name)

    modify_templates = [
        "{item} soğansız olsun.",
        "{item} için ekstra sos ekleyebilir miyim?",
        "{item} içine sos eklemeyin.",
        "{item} yerine başka bir içecek seçebilir miyim?",
    ]
    modify_items = menu_items[:2] + menu_items[-2:]
    for template, item in zip(modify_templates, modify_items):
        name = str(item["name"])
        add_record("modify_order", template.format(item=name), name)

    for item in menu_items[:4]:
        name = str(item["name"])
        add_record("remove_item", f"{name} siparişimden çıkarılsın.", name)

    add_record("ask_menu", "Menüde neler var?", None)
    add_record("ask_menu", "İçecek seçenekleriniz neler?", None)
    add_record("ask_menu", "Çorba çeşitleriniz neler?", None)
    add_record("ask_menu", "Ana yemeklerde neler önerirsiniz?", None)

    add_record("confirm_order", "Siparişimi onaylamak istiyorum.", None)
    add_record("confirm_order", "Evet, siparişimi onaylıyorum.", None)
    add_record("confirm_order", "Bu sipariş doğru, devam edelim.", None)

    for probe in OFF_TOPIC_PROBES:
        add_record("off_topic_rejection_probe", probe, None)

    for probe in UNSUPPORTED_ITEM_PROBES:
        add_record("unsupported_item_probe", probe, None)

    return records


def build_menu_grounded_user_message_seed(
    *,
    menu_path: Path = MENU_PATH,
    restaurant_info_path: Path = RESTAURANT_INFO_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Dict[str, Any]:
    del restaurant_info_path  # reserved for future extension; not needed in this seed pass

    menu_items = _load_menu(menu_path)
    records = _build_seed_records(menu_items)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    category_counts = Counter(record["intent_category"] for record in records)
    return {
        "output_path": str(output_path),
        "records_written": len(records),
        "category_counts": dict(sorted(category_counts.items())),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a review-only menu-grounded Turkish user-message seed worksheet."
    )
    parser.add_argument(
        "--menu",
        type=Path,
        default=MENU_PATH,
        help=f"Menu YAML path (default: {MENU_PATH})",
    )
    parser.add_argument(
        "--restaurant-info",
        type=Path,
        default=RESTAURANT_INFO_PATH,
        help=f"Restaurant info YAML path (default: {RESTAURANT_INFO_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output JSONL path (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        summary = build_menu_grounded_user_message_seed(
            menu_path=Path(args.menu),
            restaurant_info_path=Path(args.restaurant_info),
            output_path=Path(args.output),
        )
    except Exception as exc:
        print(f"Menu-grounded seed build failed: {exc}")
        return 1

    print("Menu-grounded user-message seed build complete.")
    print(f"Records written: {summary['records_written']}")
    print("Intent category distribution:")
    for category, count in summary["category_counts"].items():
        print(f"- {category}: {count}")
    print(f"Output path: {summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
