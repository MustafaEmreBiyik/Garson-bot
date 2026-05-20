from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import unicodedata
from typing import Dict, Iterable, List, Optional

import yaml


@dataclass
class MenuItem:
    id: str
    name: str
    category: str
    price: float
    description: str
    allergens: List[str]
    availability: bool
    tags: List[str]
    aliases: List[str] = field(default_factory=list)


def _repair_text(text: str) -> str:
    try:
        return text.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def normalize_text(text: str) -> str:
    repaired = _repair_text(text or "")
    translated = repaired.translate(
        str.maketrans(
            {
                "ı": "i",
                "İ": "I",
                "ş": "s",
                "Ş": "S",
                "ğ": "g",
                "Ğ": "G",
                "ç": "c",
                "Ç": "C",
                "ö": "o",
                "Ö": "O",
                "ü": "u",
                "Ü": "U",
            }
        )
    )
    decomposed = unicodedata.normalize("NFKD", translated.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


class MenuKnowledge:
    def __init__(self, menu_path: Path):
        self.menu_path = menu_path
        self.items: List[MenuItem] = []

    def load(self) -> None:
        if not self.menu_path.exists():
            raise FileNotFoundError(f"Menu file not found: {self.menu_path}")
        raw = yaml.safe_load(self.menu_path.read_text(encoding="utf-8")) or {}
        self.items = [self._to_item(entry) for entry in raw.get("menu", [])]

    def _to_item(self, entry: Dict) -> MenuItem:
        return MenuItem(
            id=str(entry.get("id", "")),
            name=str(entry.get("name", "")),
            category=str(entry.get("category", "")),
            price=float(entry.get("price", 0)),
            description=str(entry.get("description", "")),
            allergens=list(entry.get("allergens", []) or []),
            availability=bool(entry.get("availability", False)),
            tags=list(entry.get("tags", []) or []),
            aliases=list(entry.get("aliases", []) or []),
        )

    def list_categories(self) -> List[str]:
        return sorted({item.category for item in self.items if item.category})

    def list_available_items(self, category: Optional[str] = None) -> List[MenuItem]:
        items = [item for item in self.items if item.availability]
        if category:
            category_key = normalize_text(category)
            items = [item for item in items if normalize_text(item.category) == category_key]
        return items

    def find_items(self, query: str) -> List[MenuItem]:
        q = normalize_text(query).strip()
        if not q:
            return []
        results = []
        for item in self.items:
            if q in normalize_text(item.name):
                results.append(item)
            elif any(q in normalize_text(alias) for alias in item.aliases):
                results.append(item)
        return results

    def get_item_by_name(self, name: str) -> Optional[MenuItem]:
        q = normalize_text(name).strip()
        for item in self.items:
            if normalize_text(item.name) == q:
                return item
        for item in self.items:
            if any(normalize_text(alias) == q for alias in item.aliases):
                return item
        return None

    def get_item_by_id(self, item_id: str) -> Optional[MenuItem]:
        q = item_id.lower().strip()
        for item in self.items:
            if item.id.lower() == q:
                return item
        return None

    def get_allergens(self, name: str) -> List[str]:
        item = self.get_item_by_name(name)
        return item.allergens if item else []

    def recommend_by_tag(self, tags: Iterable[str], limit: int = 3) -> List[MenuItem]:
        tag_set = {t.lower() for t in tags}
        results = [item for item in self.items if tag_set.intersection({t.lower() for t in item.tags})]
        return results[:limit]

    def find_mentions(self, text: str) -> List[MenuItem]:
        normalized_text = normalize_text(text)
        matched_items: List[MenuItem] = []
        for item in self.items:
            if normalize_text(item.name) in normalized_text:
                matched_items.append(item)
                continue
            for alias in item.aliases:
                if normalize_text(alias) in normalized_text:
                    matched_items.append(item)
                    break
        return matched_items
