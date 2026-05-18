from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


SupportedIntent = Literal[
    "order_item",
    "ask_price",
    "ask_category",
    "ask_menu",
    "ask_ingredient",
    "ask_allergy",
    "ask_recommendation",
    "remove_item",
    "modify_order",
    "confirm_order",
    "order_summary",
    "restaurant_info",
    "unsupported_item",
    "off_topic",
    "unclear",
]


SUPPORTED_INTENTS: set[str] = {
    "order_item",
    "ask_price",
    "ask_category",
    "ask_menu",
    "ask_ingredient",
    "ask_allergy",
    "ask_recommendation",
    "remove_item",
    "modify_order",
    "confirm_order",
    "order_summary",
    "restaurant_info",
    "unsupported_item",
    "off_topic",
    "unclear",
}


@dataclass(slots=True)
class ParsedUserIntent:
    intent: SupportedIntent
    item_name: str | None = None
    category: str | None = None
    quantity: int | None = None
    constraints: list[str] = field(default_factory=list)
    confidence: float = 0.0
    needs_clarification: bool = False
    raw_text: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.intent not in SUPPORTED_INTENTS:
            raise ValueError(f"Unsupported intent: {self.intent}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.quantity is not None and self.quantity <= 0:
            raise ValueError("quantity must be positive when provided")
        self.constraints = [str(value).strip() for value in self.constraints if str(value).strip()]
        self.notes = [str(value).strip() for value in self.notes if str(value).strip()]
        self.raw_text = str(self.raw_text)
        self.item_name = self._clean_optional_text(self.item_name)
        self.category = self._clean_optional_text(self.category)

    def is_low_confidence(self, threshold: float = 0.6) -> bool:
        return self.confidence < threshold

    @staticmethod
    def _clean_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None
