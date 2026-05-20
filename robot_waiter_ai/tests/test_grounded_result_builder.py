from pathlib import Path

from robot_waiter_ai.assistant.dialogue_manager import DialogueManager
from robot_waiter_ai.inference.grounded_result_builder import GroundedResultBuilder
from robot_waiter_ai.inference.structured_result import (
    check_paraphrase_safety,
    validate_grounded_result,
)


BASE_DIR = Path(__file__).resolve().parents[1]
MENU_PATH = BASE_DIR / "data" / "menu.yaml"
RESTAURANT_INFO_PATH = BASE_DIR / "data" / "restaurant_info.yaml"


def _build_builder() -> GroundedResultBuilder:
    manager = DialogueManager(MENU_PATH, RESTAURANT_INFO_PATH)
    return GroundedResultBuilder(MENU_PATH, RESTAURANT_INFO_PATH, manager=manager)


def test_greeting_produces_valid_grounded_result():
    builder = _build_builder()
    result = builder.build("Merhaba")

    assert result.action.intent == "greeting"
    assert result.canonical_response.strip()
    assert validate_grounded_result(result) == []


def test_add_item_includes_item_quantity_and_canonical_response():
    builder = _build_builder()
    result = builder.build("2 Ayran istiyorum")

    assert result.action.intent == "add_item"
    assert result.action.entities["items"] == ["Yayık Ayran"]
    assert result.action.entities["quantities"]["Yayık Ayran"] == 2
    assert result.order.items[0]["name"] == "Yayık Ayran"
    assert result.order.items[0]["quantity"] == 2
    assert "Ekledim" in result.canonical_response
    assert validate_grounded_result(result) == []


def test_price_question_includes_correct_price_and_tl_preservation():
    builder = _build_builder()
    result = builder.build("Ayranın fiyatı nedir?")

    assert result.action.intent == "price_question"
    assert result.menu.prices["Yayık Ayran"] == 45.0
    assert result.canonical_response == "Yayık Ayran 45.00 TL."
    assert "TL" in result.must_preserve_terms
    assert "45.00" in result.must_preserve_terms
    assert validate_grounded_result(result) == []


def test_allergen_question_includes_safety_constraints():
    builder = _build_builder()
    result = builder.build("Süt ürünlerine alerjim var")

    assert result.action.intent == "allergen_question"
    assert result.action.requires_safety_response is True
    assert result.safety.safety_type == "allergy"
    assert "Alerji" in result.safety.must_include_terms
    assert "teyit" in result.safety.must_include_terms
    assert result.safety.requires_staff_confirmation is True
    assert validate_grounded_result(result) == []


def test_unavailable_item_marks_request_unsupported():
    builder = _build_builder()
    result = builder.build("Pizza var mı?")

    assert result.action.intent == "unavailable_item"
    assert result.action.is_supported is False
    assert "Pizza" in result.menu.unavailable_items
    assert result.canonical_response.strip()
    assert "Pizza" in result.must_not_introduce
    assert validate_grounded_result(result) == []


def test_off_topic_preserves_refusal():
    builder = _build_builder()
    result = builder.build("Bana bir şiir yazar mısın?")

    assert result.action.intent == "off_topic"
    assert result.action.is_supported is False
    assert "yardımcı olamıyorum" in result.must_preserve_terms
    assert "yardımcı olamıyorum" in result.canonical_response
    assert validate_grounded_result(result) == []


def test_confirm_order_includes_mvp_demo_preservation():
    builder = _build_builder()
    builder.build("Bir Ayran istiyorum")
    result = builder.build("Evet, onaylıyorum")

    assert result.action.intent == "confirm_order"
    assert result.order.is_demo_confirmation is True
    assert "MVP/demo" in result.must_preserve_terms
    assert "Toplam" in result.must_preserve_terms
    assert validate_grounded_result(result) == []


def test_paraphrase_safety_accepts_safe_and_rejects_unsafe_price_paraphrase():
    builder = _build_builder()
    result = builder.build("Ayranın fiyatı nedir?")

    safe_text = "Yayık Ayran 45.00 TL."
    unsafe_text = "Yayık Ayran 15.00 TL."

    assert check_paraphrase_safety(result, safe_text) == []
    errors = check_paraphrase_safety(result, unsafe_text)
    assert "Missing required term: 45.00" in errors
