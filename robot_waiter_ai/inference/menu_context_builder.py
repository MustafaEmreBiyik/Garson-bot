from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MENU_PATH = BASE_DIR / "data" / "menu.yaml"
DEFAULT_RESTAURANT_INFO_PATH = BASE_DIR / "data" / "restaurant_info.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return loaded if isinstance(loaded, dict) else {}


def _as_clean_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _format_price(value: Any) -> str:
    try:
        return f"{float(value):.2f} TL"
    except (TypeError, ValueError):
        return _as_clean_text(value)


def _format_list(label: str, values: Any) -> str:
    if isinstance(values, str):
        cleaned = values.strip()
        return f"{label}: {cleaned}." if cleaned else ""
    if isinstance(values, list):
        items = [_as_clean_text(item) for item in values if _as_clean_text(item)]
        if items:
            return f"{label}: {', '.join(items)}."
    return ""


def build_menu_context(
    menu_path: Path | None = None,
    restaurant_info_path: Path | None = None,
) -> str:
    menu_data = _load_yaml(menu_path or DEFAULT_MENU_PATH)
    info_data = _load_yaml(restaurant_info_path or DEFAULT_RESTAURANT_INFO_PATH)

    lines: list[str] = []

    menu_items = menu_data.get("menu")
    if isinstance(menu_items, list):
        categories: dict[str, list[str]] = {}
        for item in menu_items:
            if not isinstance(item, dict):
                continue
            name = _as_clean_text(item.get("name"))
            if not name:
                continue
            category = _as_clean_text(item.get("category")) or "Diğer"
            price = item.get("price")
            item_text = name
            if price not in (None, ""):
                formatted_price = _format_price(price)
                if formatted_price:
                    item_text = f"{name} ({formatted_price})"
            categories.setdefault(category, []).append(item_text)

        if categories:
            lines.append("Menü kategorileri: " + ", ".join(sorted(categories)) + ".")
            for category in sorted(categories):
                lines.append(f"{category}: {', '.join(categories[category])}.")

    restaurant = info_data.get("restaurant")
    if isinstance(restaurant, dict):
        opening_hours = _as_clean_text(restaurant.get("opening_hours"))
        if opening_hours:
            lines.append(f"Çalışma saatleri: {opening_hours}.")

        payment_methods_line = _format_list("Ödeme yöntemleri", restaurant.get("payment_methods"))
        if payment_methods_line:
            lines.append(payment_methods_line)

        allergy_policy_line = _format_list("Alerji politikası", restaurant.get("allergy_policy"))
        if allergy_policy_line:
            lines.append(allergy_policy_line)

    return "\n".join(lines).strip()
