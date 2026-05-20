from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_menu_context(menu_context_path: Path | str) -> dict[str, Any]:
    path = Path(menu_context_path)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Menu context must be a JSON object.")
    return loaded


def build_menu_context_system_prompt(menu_context: dict[str, Any]) -> str:
    restaurant_name = str(menu_context.get("restaurant_name", "")).strip() or "Garson Bot Bistro"
    currency = str(menu_context.get("currency", "")).strip() or "TL"
    items = menu_context.get("items")
    rules = menu_context.get("rules")

    if not isinstance(items, list) or not items:
        raise ValueError("Menu context must include a non-empty 'items' list.")
    if rules is not None and not isinstance(rules, list):
        raise ValueError("Menu context 'rules' must be a list when provided.")

    item_lines: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each menu item must be a JSON object.")
        name = str(item.get("name", "")).strip()
        category = str(item.get("category", "")).strip()
        price = item.get("price")
        if not name or not category or price in (None, ""):
            raise ValueError("Each menu item must include name, category, and price.")
        item_lines.append(f"- {name} | {category} | {price} {currency}")

    rule_lines = [f"- {str(rule).strip()}" for rule in rules or [] if str(rule).strip()]

    prompt_lines = [
        f"Sen {restaurant_name} için çalışan Türkçe konuşan kibar bir garsonsun.",
        "Her zaman garson rolünde kal.",
        "Cevapların kısa, doğal ve nazik olsun.",
        "Sipariş ekleme, çıkarma, onaylama ve toplam tutar konuşmasını sürdürebil.",
        "Menü dışı ürünleri kibarca reddet.",
        "Fiyat uydurma; sadece aşağıdaki menü fiyatlarını kullan.",
        "Alerjen konusunda kesin güvence verme; mutfak veya personel teyidi öner.",
        "Restoran dışı konuları kibarca reddet ve konuşmayı menüye geri getir.",
        f"Para birimi: {currency}",
        "",
        "Menü:",
        *item_lines,
    ]
    if rule_lines:
        prompt_lines.extend(["", "Ek kurallar:", *rule_lines])
    return "\n".join(prompt_lines).strip()
