from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from robot_waiter_ai.assistant.menu_knowledge import normalize_text


SUPPORTED_GROUNDED_INTENTS = {
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


@dataclass
class GroundedAction:
    intent: str
    user_message: str
    normalized_user_message: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: Optional[float] = None
    requires_safety_response: bool = False
    is_supported: bool = True
    reason: Optional[str] = None


@dataclass
class MenuGrounding:
    matched_items: List[Dict[str, Any]] = field(default_factory=list)
    unavailable_items: List[str] = field(default_factory=list)
    prices: Dict[str, float] = field(default_factory=dict)
    categories: List[str] = field(default_factory=list)
    source: str = "menu.yaml"


@dataclass
class OrderGrounding:
    action_type: str = ""
    items: List[Dict[str, Any]] = field(default_factory=list)
    total_price: Optional[float] = None
    order_is_empty: bool = False
    order_summary: Optional[str] = None
    is_demo_confirmation: bool = False


@dataclass
class SafetyGrounding:
    safety_type: Optional[str] = None
    must_include_terms: List[str] = field(default_factory=list)
    forbidden_claims: List[str] = field(default_factory=list)
    requires_staff_confirmation: bool = False


@dataclass
class GroundedResult:
    action: GroundedAction
    menu: MenuGrounding
    order: OrderGrounding
    safety: SafetyGrounding
    canonical_response: str
    allowed_paraphrase: bool = False
    must_preserve_terms: List[str] = field(default_factory=list)
    must_not_introduce: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


def validate_grounded_result(result: GroundedResult) -> List[str]:
    errors: List[str] = []

    if result.action.intent not in SUPPORTED_GROUNDED_INTENTS:
        errors.append(f"Unsupported grounded intent: {result.action.intent}")

    if not result.action.user_message.strip():
        errors.append("GroundedAction.user_message must be non-empty.")

    if result.action.confidence is not None and not 0.0 <= result.action.confidence <= 1.0:
        errors.append("GroundedAction.confidence must be between 0.0 and 1.0.")

    if not result.canonical_response.strip():
        errors.append("GroundedResult.canonical_response must be non-empty.")

    if result.order.total_price is not None and result.order.total_price < 0:
        errors.append("OrderGrounding.total_price cannot be negative.")

    if result.menu.source.strip() == "":
        errors.append("MenuGrounding.source must be non-empty.")

    if result.action.intent == "allergen_question":
        if "Alerji" not in result.safety.must_include_terms:
            errors.append("Allergen results must preserve 'Alerji'.")
        if "teyit" not in result.safety.must_include_terms:
            errors.append("Allergen results must preserve 'teyit'.")

    if result.action.intent == "off_topic" and not result.safety.must_include_terms:
        errors.append("Off-topic results must define refusal-preserving terms.")

    if result.action.intent == "confirm_order" and result.order.is_demo_confirmation:
        if "MVP/demo" not in result.must_preserve_terms:
            errors.append("Demo confirmations must preserve 'MVP/demo'.")

    return errors


def ensure_required_terms(response: str, terms: List[str]) -> List[str]:
    normalized_response = normalize_text(response)
    missing_terms: List[str] = []
    for term in terms:
        if normalize_text(term) not in normalized_response:
            missing_terms.append(term)
    return missing_terms


def ensure_forbidden_terms_absent(response: str, forbidden_terms: List[str]) -> List[str]:
    normalized_response = normalize_text(response)
    present_terms: List[str] = []
    for term in forbidden_terms:
        if normalize_text(term) in normalized_response:
            present_terms.append(term)
    return present_terms


def _expected_order_terms(result: GroundedResult) -> List[str]:
    terms: List[str] = []
    for item in result.order.items:
        name = str(item.get("name", "")).strip()
        if name:
            terms.append(name)

        quantity = item.get("quantity")
        if quantity is not None:
            terms.append(str(quantity))

        unit_price = item.get("unit_price")
        if unit_price is not None:
            terms.append(_format_price(unit_price))

        line_total = item.get("line_total")
        if line_total is not None:
            terms.append(_format_price(line_total))

    if result.order.total_price is not None:
        terms.append(_format_price(result.order.total_price))

    return terms


def _format_price(price: Any) -> str:
    return f"{float(price):.2f}"


def check_paraphrase_safety(original_result: GroundedResult, paraphrased_text: str) -> List[str]:
    errors = validate_grounded_result(original_result)
    if errors:
        return errors

    missing_required = ensure_required_terms(
        paraphrased_text,
        original_result.must_preserve_terms
        + original_result.safety.must_include_terms
        + _expected_order_terms(original_result),
    )
    if missing_required:
        errors.extend(f"Missing required term: {term}" for term in missing_required)

    present_forbidden = ensure_forbidden_terms_absent(
        paraphrased_text,
        original_result.must_not_introduce + original_result.safety.forbidden_claims,
    )
    if present_forbidden:
        errors.extend(f"Forbidden term present: {term}" for term in present_forbidden)

    if not original_result.allowed_paraphrase and normalize_text(
        paraphrased_text
    ) != normalize_text(original_result.canonical_response):
        errors.append("Paraphrase not allowed for this grounded result.")

    return errors
