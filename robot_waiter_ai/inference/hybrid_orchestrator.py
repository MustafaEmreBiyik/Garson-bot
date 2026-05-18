from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from robot_waiter_ai.assistant.dialogue_manager import DialogueManager
from robot_waiter_ai.assistant.menu_knowledge import MenuKnowledge, normalize_text
from robot_waiter_ai.assistant import safety_rules

from .nlu_adapter import BaseNLUAdapter
from .nlu_schema import ParsedUserIntent


@dataclass(slots=True)
class HybridOrchestratorResult:
    response_text: str
    parsed_intent: ParsedUserIntent
    used_deterministic_fallback: bool


class HybridOrchestrator:
    """Experimental hybrid path that preserves deterministic authority."""

    def __init__(
        self,
        menu_path: Path,
        restaurant_info_path: Path,
        nlu_adapter: BaseNLUAdapter,
        dialogue_manager: DialogueManager | None = None,
        low_confidence_threshold: float = 0.6,
    ) -> None:
        self.nlu_adapter = nlu_adapter
        self.low_confidence_threshold = low_confidence_threshold
        self.dialogue_manager = dialogue_manager or DialogueManager(menu_path, restaurant_info_path)
        self.menu: MenuKnowledge = self.dialogue_manager.menu

    def handle_message(self, message: str) -> HybridOrchestratorResult:
        parsed = self.nlu_adapter.parse(message)

        if parsed.intent == "off_topic":
            return self._result(
                "Bu konuda yardımcı olamıyorum. Menü veya siparişle ilgili sorabilir misiniz?",
                parsed,
                used_deterministic_fallback=True,
            )

        if parsed.intent == "unsupported_item":
            return self._result(
                safety_rules.no_invention_response(),
                parsed,
                used_deterministic_fallback=True,
            )

        if parsed.needs_clarification or parsed.intent == "unclear" or parsed.is_low_confidence(self.low_confidence_threshold):
            return self._result(
                self._clarification_response(parsed),
                parsed,
                used_deterministic_fallback=True,
            )

        if parsed.item_name and self.menu.get_item_by_name(parsed.item_name) is None:
            return self._result(
                safety_rules.no_invention_response(),
                parsed,
                used_deterministic_fallback=True,
            )

        if parsed.category and not self._is_known_category(parsed.category):
            return self._result(
                safety_rules.no_invention_response(),
                parsed,
                used_deterministic_fallback=True,
            )

        canonical_message = self._build_canonical_message(parsed)
        response_text = self.dialogue_manager.handle_message(canonical_message)
        return self._result(
            response_text,
            parsed,
            used_deterministic_fallback=canonical_message != message,
        )

    def _build_canonical_message(self, parsed: ParsedUserIntent) -> str:
        if parsed.intent == "ask_category" and parsed.category:
            return f"{parsed.category} seçenekleri neler?"

        if parsed.intent == "ask_recommendation":
            if parsed.category and "hafif" in {normalize_text(value) for value in parsed.constraints}:
                return f"{parsed.category} için hafif bir şey öner"
            if parsed.category:
                return f"{parsed.category} öner"
            return "Ne önerirsiniz?"

        if parsed.intent == "ask_allergy":
            if "no_dairy" in parsed.constraints or "sut urunu" in normalize_text(" ".join(parsed.constraints)):
                return "Süt ürünü istemiyorum"
            if parsed.item_name:
                return f"{parsed.item_name} alerjen bilgisi nedir?"
            return parsed.raw_text

        if parsed.intent == "ask_price" and parsed.item_name:
            return f"{parsed.item_name} fiyatı nedir?"

        if parsed.intent == "ask_menu":
            return "Menüde neler var?"

        if parsed.intent == "restaurant_info":
            return parsed.raw_text

        if parsed.intent == "order_summary":
            return "Siparişim ne?"

        if parsed.intent == "confirm_order":
            return "Siparişi onayla"

        if parsed.intent == "remove_item" and parsed.item_name:
            return f"{parsed.item_name} çıkar"

        if parsed.intent == "modify_order" and parsed.item_name and parsed.quantity is not None:
            return f"{parsed.item_name} {parsed.quantity} tane"

        if parsed.intent == "order_item" and parsed.item_name:
            qty = parsed.quantity if parsed.quantity is not None else 1
            return f"{qty} {parsed.item_name} istiyorum"

        return parsed.raw_text

    def _clarification_response(self, parsed: ParsedUserIntent) -> str:
        if parsed.intent == "off_topic":
            return "Bu konuda yardımcı olamıyorum. Menü veya siparişle ilgili sorabilir misiniz?"
        return (
            "Tam olarak ne istediğinizi netleştiremedim. "
            "Menü, kategori, fiyat veya siparişle ilgili biraz daha açık yazar mısınız?"
        )

    def _is_known_category(self, category: str) -> bool:
        category_key = normalize_text(category)
        return any(normalize_text(value) == category_key for value in self.menu.list_categories())

    @staticmethod
    def _result(
        response_text: str,
        parsed: ParsedUserIntent,
        used_deterministic_fallback: bool,
    ) -> HybridOrchestratorResult:
        return HybridOrchestratorResult(
            response_text=response_text,
            parsed_intent=parsed,
            used_deterministic_fallback=used_deterministic_fallback,
        )
