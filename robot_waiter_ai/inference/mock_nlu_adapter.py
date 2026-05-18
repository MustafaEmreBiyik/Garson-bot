from __future__ import annotations

from .nlu_adapter import BaseNLUAdapter
from .nlu_schema import ParsedUserIntent
from robot_waiter_ai.assistant.menu_knowledge import normalize_text


class MockNLUAdapter(BaseNLUAdapter):
    """Small phrase mapper used only to validate hybrid architecture seams."""

    def parse(self, message: str) -> ParsedUserIntent:
        raw_text = message.strip()
        lower = normalize_text(raw_text)

        if not raw_text:
            return ParsedUserIntent(
                intent="unclear",
                confidence=0.0,
                needs_clarification=True,
                raw_text=raw_text,
                notes=["empty_message"],
            )

        if any(term in lower for term in ["kripto", "bitcoin", "hava durumu", "python", "kod yaz"]):
            return ParsedUserIntent(
                intent="off_topic",
                confidence=0.99,
                raw_text=raw_text,
                notes=["clear_off_topic"],
            )

        if "soguk icecek var mi" in lower or "ayran disinda ne icebilirim" in lower:
            return ParsedUserIntent(
                intent="ask_category",
                category="İçecek",
                confidence=0.9,
                raw_text=raw_text,
            )

        if "hafif" in lower and any(term in lower for term in ["oner", "tavsiye"]):
            return ParsedUserIntent(
                intent="ask_recommendation",
                category="Ana Yemek",
                constraints=["hafif"],
                confidence=0.86,
                raw_text=raw_text,
            )

        if "sut urunu istemiyorum" in lower or "sut urunu olmasin" in lower:
            return ParsedUserIntent(
                intent="ask_allergy",
                constraints=["no_dairy"],
                confidence=0.82,
                raw_text=raw_text,
                notes=["dairy_avoidance"],
            )

        if "iki tane daha" in lower or "bundan iki tane daha" in lower or "sundan iki tane daha" in lower:
            return ParsedUserIntent(
                intent="unclear",
                quantity=2,
                confidence=0.3,
                needs_clarification=True,
                raw_text=raw_text,
                notes=["missing_item_context"],
            )

        if "falafel" in lower:
            return ParsedUserIntent(
                intent="unsupported_item",
                item_name="Falafel",
                confidence=0.88,
                raw_text=raw_text,
            )

        if "ayran" in lower and any(term in lower for term in ["fiyat", "ne kadar"]):
            return ParsedUserIntent(
                intent="ask_price",
                item_name="Ayran",
                confidence=0.95,
                raw_text=raw_text,
            )

        if "menude ne var" in lower or "menu de ne var" in lower:
            return ParsedUserIntent(
                intent="ask_menu",
                confidence=0.92,
                raw_text=raw_text,
            )

        return ParsedUserIntent(
            intent="unclear",
            confidence=0.35,
            needs_clarification=True,
            raw_text=raw_text,
            notes=["no_mock_mapping"],
        )
