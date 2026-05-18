import pytest

from robot_waiter_ai.inference.nlu_schema import ParsedUserIntent
from robot_waiter_ai.inference.mock_nlu_adapter import MockNLUAdapter


def test_parsed_user_intent_accepts_expected_fields():
    parsed = ParsedUserIntent(
        intent="ask_price",
        item_name="Ayran",
        category="İçecek",
        quantity=1,
        constraints=["cold"],
        confidence=0.91,
        needs_clarification=False,
        raw_text="Ayran ne kadar?",
        notes=["mock"],
    )

    assert parsed.intent == "ask_price"
    assert parsed.item_name == "Ayran"
    assert parsed.category == "İçecek"
    assert parsed.quantity == 1
    assert parsed.constraints == ["cold"]
    assert parsed.confidence == 0.91
    assert parsed.needs_clarification is False
    assert parsed.raw_text == "Ayran ne kadar?"
    assert parsed.notes == ["mock"]


def test_parsed_user_intent_rejects_invalid_confidence():
    with pytest.raises(ValueError, match="confidence"):
        ParsedUserIntent(intent="ask_menu", confidence=1.5, raw_text="menü")


def test_mock_adapter_maps_flexible_category_phrase():
    parsed = MockNLUAdapter().parse("Ayran dışında ne içebilirim?")

    assert parsed.intent == "ask_category"
    assert parsed.category == "İçecek"
    assert parsed.confidence >= 0.8


def test_mock_adapter_maps_light_recommendation_phrase():
    parsed = MockNLUAdapter().parse("Bana hafif bir yemek öner")

    assert parsed.intent == "ask_recommendation"
    assert parsed.category == "Ana Yemek"
    assert "hafif" in parsed.constraints


def test_mock_adapter_flags_missing_context_phrase():
    parsed = MockNLUAdapter().parse("Şundan iki tane daha")

    assert parsed.intent == "unclear"
    assert parsed.needs_clarification is True
    assert parsed.quantity == 2
