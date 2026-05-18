from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from robot_waiter_ai.assistant.dialogue_manager import DialogueManager
from robot_waiter_ai.assistant.menu_knowledge import MenuItem, normalize_text
from robot_waiter_ai.assistant.order_state import OrderItem

from .structured_result import (
    GroundedAction,
    GroundedResult,
    MenuGrounding,
    OrderGrounding,
    SafetyGrounding,
)


KNOWN_UNAVAILABLE_ITEMS = [
    "pizza",
    "hamburger",
    "sushi",
    "taco",
    "kola",
    "tavuk burger",
    "patates kizartmasi",
    "patates kızartması",
]


class GroundedResultBuilder:
    def __init__(
        self,
        menu_path: Path,
        restaurant_info_path: Path,
        manager: Optional[DialogueManager] = None,
    ) -> None:
        self.manager = manager or DialogueManager(menu_path, restaurant_info_path)

    def build(self, user_message: str) -> GroundedResult:
        before_order = self._snapshot_order_items()
        normalized = normalize_text(user_message.strip())
        matched_items = self.manager.menu.find_mentions(user_message)
        intent = self._classify_intent(normalized, matched_items)
        unavailable_items = self._extract_unavailable_items(normalized, matched_items, intent)

        if intent == "unavailable_item":
            canonical_response = (
                "Bu ürün menümüzde bulunmuyor. İsterseniz mevcut kategorilerden öneri sunabilirim."
            )
        else:
            canonical_response = self.manager.handle_message(user_message)

        after_order = self._snapshot_order_items()

        return GroundedResult(
            action=self._build_action(
                intent=intent,
                user_message=user_message,
                normalized=normalized,
                matched_items=matched_items,
                unavailable_items=unavailable_items,
            ),
            menu=self._build_menu_grounding(intent, matched_items, unavailable_items),
            order=self._build_order_grounding(
                intent=intent,
                matched_items=matched_items,
                before_order=before_order,
                after_order=after_order,
                user_message=user_message,
                canonical_response=canonical_response,
            ),
            safety=self._build_safety_grounding(intent),
            canonical_response=canonical_response,
            allowed_paraphrase=self._is_paraphrase_allowed(intent),
            must_preserve_terms=self._build_must_preserve_terms(
                intent=intent,
                matched_items=matched_items,
                unavailable_items=unavailable_items,
                before_order=before_order,
                after_order=after_order,
                canonical_response=canonical_response,
            ),
            must_not_introduce=self._build_must_not_introduce(
                intent=intent,
                unavailable_items=unavailable_items,
            ),
            metadata={
                "builder": "grounded_result_builder_v1",
                "canonical_source": "dialogue_manager" if intent != "unavailable_item" else "builder_rule",
            },
        )

    def _classify_intent(self, normalized: str, matched_items: List[MenuItem]) -> str:
        if self.manager._is_greeting(normalized):
            return "greeting"
        if self.manager._is_ask_hours(normalized) or self.manager._is_restaurant_info_question(normalized):
            return "restaurant_info"
        if self.manager._is_recommendation(normalized):
            return "recommendation"
        if self.manager._is_allergy(normalized):
            return "allergen_question"
        if self.manager._is_confirm_order(normalized):
            return "confirm_order"
        if self.manager._is_summary(normalized):
            return "summarize_order"
        if self.manager._is_clear_order(normalized):
            return "clear_order"
        if self.manager._is_remove_order(normalized):
            return "remove_item"
        if self._is_unavailable_item_request(normalized, matched_items):
            return "unavailable_item"
        if self.manager._is_add_order(normalized):
            return "add_item"
        if self.manager._is_category_listing_question(normalized) or self.manager._is_ask_categories(normalized):
            return "menu_question"
        if self.manager._is_price_question(normalized):
            return "price_question"
        if self.manager._is_menu_question(normalized) and not matched_items:
            return "menu_question"
        if self.manager._is_menu_question(normalized) and matched_items:
            return "menu_question"
        return "off_topic"

    def _build_action(
        self,
        intent: str,
        user_message: str,
        normalized: str,
        matched_items: List[MenuItem],
        unavailable_items: List[str],
    ) -> GroundedAction:
        entities: Dict[str, Any] = {}
        if matched_items:
            entities["items"] = [item.name for item in matched_items]
            if intent in {"add_item", "remove_item"}:
                entities["quantities"] = {
                    item.name: self.manager._extract_quantity(user_message, item.name)
                    for item in matched_items
                }
        if unavailable_items:
            entities["unavailable_items"] = list(unavailable_items)

        return GroundedAction(
            intent=intent,
            user_message=user_message,
            normalized_user_message=normalized,
            entities=entities,
            confidence=1.0,
            requires_safety_response=intent in {"allergen_question", "off_topic"},
            is_supported=intent not in {"unavailable_item", "off_topic"},
            reason=self._build_reason(intent, unavailable_items),
        )

    def _build_menu_grounding(
        self,
        intent: str,
        matched_items: List[MenuItem],
        unavailable_items: List[str],
    ) -> MenuGrounding:
        prices = {item.name: item.price for item in matched_items}
        categories = self.manager.menu.list_categories() if intent in {"menu_question", "restaurant_info"} else []
        return MenuGrounding(
            matched_items=[self._menu_item_to_dict(item) for item in matched_items],
            unavailable_items=unavailable_items,
            prices=prices,
            categories=categories,
            source="menu.yaml",
        )

    def _build_order_grounding(
        self,
        intent: str,
        matched_items: List[MenuItem],
        before_order: Dict[str, OrderItem],
        after_order: Dict[str, OrderItem],
        user_message: str,
        canonical_response: str,
    ) -> OrderGrounding:
        action_type = intent
        order_items: List[Dict[str, Any]] = []

        if intent == "add_item":
            for item in matched_items:
                quantity = self.manager._extract_quantity(user_message, item.name)
                order_items.append(
                    {
                        "id": item.id,
                        "name": item.name,
                        "quantity": quantity,
                        "unit_price": item.price,
                        "line_total": item.price * quantity,
                    }
                )
        elif intent == "remove_item":
            for item in matched_items:
                previous = before_order.get(item.id)
                if previous:
                    order_items.append(
                        {
                            "id": previous.id,
                            "name": previous.name,
                            "quantity": previous.quantity,
                            "unit_price": previous.price,
                            "line_total": previous.price * previous.quantity,
                        }
                    )
        else:
            order_items = [self._order_item_to_dict(item) for item in after_order.values()]

        total_price = None
        order_summary = None
        if intent in {"add_item", "remove_item", "clear_order", "summarize_order", "confirm_order"}:
            total_price = sum(item.price * item.quantity for item in after_order.values())
            order_summary = self.manager.order.summarize()
        if intent == "confirm_order" and not after_order:
            total_price = 0.0
            order_summary = canonical_response

        return OrderGrounding(
            action_type=action_type,
            items=order_items,
            total_price=total_price,
            order_is_empty=not bool(after_order),
            order_summary=order_summary,
            is_demo_confirmation=intent == "confirm_order" and "MVP/demo" in canonical_response,
        )

    def _build_safety_grounding(self, intent: str) -> SafetyGrounding:
        if intent == "allergen_question":
            return SafetyGrounding(
                safety_type="allergy",
                must_include_terms=["Alerji", "teyit"],
                forbidden_claims=["kesinlikle güvenli", "hiç sorun yok"],
                requires_staff_confirmation=True,
            )
        if intent == "off_topic":
            return SafetyGrounding(
                safety_type="scope_refusal",
                must_include_terms=["yardımcı olamıyorum"],
                forbidden_claims=[],
                requires_staff_confirmation=False,
            )
        return SafetyGrounding()

    def _is_paraphrase_allowed(self, intent: str) -> bool:
        return intent in {
            "greeting",
            "restaurant_info",
            "menu_question",
            "recommendation",
            "price_question",
            "allergen_question",
            "add_item",
            "remove_item",
            "clear_order",
            "summarize_order",
            "confirm_order",
            "unavailable_item",
            "off_topic",
        }

    def _build_must_preserve_terms(
        self,
        intent: str,
        matched_items: List[MenuItem],
        unavailable_items: List[str],
        before_order: Dict[str, OrderItem],
        after_order: Dict[str, OrderItem],
        canonical_response: str,
    ) -> List[str]:
        terms: List[str] = []
        if intent == "greeting":
            terms.extend(["Merhaba"])
        if intent == "restaurant_info":
            for marker in [
                "Garson Bot Bistro",
                "10:00",
                "22:00",
                "nakit",
                "kredi kartı",
                "temassız ödeme",
                "teyit",
                "Vejetaryen",
                "demo",
            ]:
                if marker in canonical_response:
                    terms.append(marker)
        if intent == "menu_question":
            terms.extend(["Kategoriler"] if "Kategoriler" in canonical_response else ["Kategori"])
        if intent == "recommendation":
            terms.append("Öneri")
            terms.extend(
                item.name
                for item in self.manager.menu.list_available_items()
                if item.name in canonical_response
            )
        if intent == "price_question":
            terms.append("TL")
            for item in matched_items:
                terms.extend([item.name, f"{item.price:.2f}"])
        if intent == "allergen_question":
            terms.extend(["Alerji", "teyit"])
        if intent == "add_item":
            terms.append("Ekledim")
            for item in matched_items:
                terms.append(item.name)
        if intent == "remove_item":
            terms.append("Çıkardım")
            for item in matched_items:
                terms.append(item.name)
        if intent == "clear_order":
            terms.append("temizlendi")
        if intent == "summarize_order":
            if after_order:
                terms.extend(["Toplam", "TL"])
        if intent == "confirm_order":
            if after_order:
                terms.extend(["Toplam", "MVP/demo"])
            else:
                terms.extend(["aktif bir siparişiniz görünmüyor", "Önce"])
        if intent == "unavailable_item":
            terms.append("bulunmuyor")
        if intent == "off_topic":
            terms.append("yardımcı olamıyorum")

        if intent in {"add_item", "confirm_order", "summarize_order"}:
            for order_item in after_order.values():
                terms.extend(
                    [
                        order_item.name,
                        str(order_item.quantity),
                        f"{order_item.price:.2f}",
                        f"{order_item.price * order_item.quantity:.2f}",
                    ]
                )
        if intent == "remove_item":
            for order_item in before_order.values():
                if order_item.id not in after_order:
                    terms.extend(
                        [
                            order_item.name,
                            str(order_item.quantity),
                            f"{order_item.price:.2f}",
                        ]
                    )
        if intent == "unavailable_item":
            terms.extend(unavailable_items)

        seen: List[str] = []
        for term in terms:
            if term and term not in seen:
                seen.append(term)
        return seen

    def _build_must_not_introduce(self, intent: str, unavailable_items: List[str]) -> List[str]:
        if intent == "unavailable_item":
            return unavailable_items + ["eklendi", "fiyatı", "fiyati", "MVP/demo"]
        if intent == "off_topic":
            return ["şiir hazırladım", "şiir yazdım", "iste bir siir", "işte bir şiir"]
        if intent == "allergen_question":
            return ["kesinlikle güvenli", "hiç sorun yok"]
        return []

    def _build_reason(self, intent: str, unavailable_items: List[str]) -> Optional[str]:
        if intent == "unavailable_item" and unavailable_items:
            return "menu_item_not_found"
        if intent == "off_topic":
            return "restaurant_scope_only"
        if intent == "allergen_question":
            return "safety_caution_required"
        return None

    def _snapshot_order_items(self) -> Dict[str, OrderItem]:
        return {
            item_id: OrderItem(
                id=item.id,
                name=item.name,
                price=item.price,
                quantity=item.quantity,
            )
            for item_id, item in self.manager.order.items.items()
        }

    def _extract_unavailable_items(
        self,
        normalized: str,
        matched_items: List[MenuItem],
        intent: str,
    ) -> List[str]:
        if intent != "unavailable_item":
            return []

        found: List[str] = []
        for candidate in KNOWN_UNAVAILABLE_ITEMS:
            if candidate in normalized:
                found.append(self._display_item_name(candidate))

        if not found and not matched_items:
            found.append("Bilinmeyen ürün")

        return found

    def _is_unavailable_item_request(self, normalized: str, matched_items: List[MenuItem]) -> bool:
        if matched_items:
            return False

        if not any(candidate in normalized for candidate in KNOWN_UNAVAILABLE_ITEMS):
            return False

        return any(
            marker in normalized
            for marker in ["var mi", "istiyorum", "ekle", "siparis", "fiyat", "nedir", "edebilir miyim"]
        )

    def _menu_item_to_dict(self, item: MenuItem) -> Dict[str, Any]:
        return {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "price": item.price,
            "availability": item.availability,
            "allergens": list(item.allergens),
            "tags": list(item.tags),
        }

    def _order_item_to_dict(self, item: OrderItem) -> Dict[str, Any]:
        return {
            "id": item.id,
            "name": item.name,
            "quantity": item.quantity,
            "unit_price": item.price,
            "line_total": item.price * item.quantity,
        }

    def _display_item_name(self, candidate: str) -> str:
        mapping = {
            "pizza": "Pizza",
            "hamburger": "Hamburger",
            "sushi": "Sushi",
            "taco": "Taco",
            "kola": "Kola",
            "tavuk burger": "Tavuk Burger",
            "patates kizartmasi": "Patates Kızartması",
            "patates kızartması": "Patates Kızartması",
        }
        return mapping.get(candidate, candidate.title())


def build_grounded_result(
    user_message: str,
    menu_path: Path,
    restaurant_info_path: Path,
    manager: Optional[DialogueManager] = None,
) -> GroundedResult:
    builder = GroundedResultBuilder(
        menu_path=menu_path,
        restaurant_info_path=restaurant_info_path,
        manager=manager,
    )
    return builder.build(user_message)
