from pathlib import Path

import pytest

from robot_waiter_ai.assistant.dialogue_manager import DialogueManager
from robot_waiter_ai.inference.grounded_demo import run_grounded_demo
from robot_waiter_ai.inference.grounded_result_builder import GroundedResultBuilder


BASE_DIR = Path(__file__).resolve().parents[1]
MENU_PATH = BASE_DIR / "data" / "menu.yaml"
RESTAURANT_INFO_PATH = BASE_DIR / "data" / "restaurant_info.yaml"


@pytest.fixture
def manager():
    return DialogueManager(MENU_PATH, RESTAURANT_INFO_PATH)


def test_restaurant_hours_question_returns_configured_hours(manager):
    response = manager.handle_message("Kaçta kapanıyorsunuz?")

    assert "Çalışma saatlerimiz" in response
    assert "10:00" in response
    assert "22:00" in response


@pytest.mark.parametrize("message", ["Kart geçiyor mu?", "Ödeme seçenekleri neler?"])
def test_payment_questions_return_configured_methods(manager, message):
    response = manager.handle_message(message)

    assert "Ödeme seçenekleri" in response
    assert "nakit" in response
    assert "kredi kartı" in response


def test_allergen_policy_question_returns_cautious_policy(manager):
    response = manager.handle_message("Alerjen bilgisi güvenilir mi?")

    assert "mutfakla teyit" in response


def test_unknown_operational_info_does_not_invent_facts(manager):
    response = manager.handle_message("Paket servis var mı?")

    assert "demo" in response.casefold()
    assert "gerçek restoran gönderimi yapmaz" in response


def test_restaurant_name_question_returns_configured_name(manager):
    response = manager.handle_message("Restoranın adı ne?")

    assert "Garson Bot Bistro" in response


@pytest.mark.parametrize(
    "message, expected_terms, unexpected_terms",
    [
        ("Tatlı olarak ne önerirsin?", ["Fırın Sütlaç"], ["Mercimek Çorbası"]),
        ("İçecek olarak ne önerirsin?", ["Ayran"], ["Mercimek Çorbası", "Fırın Sütlaç"]),
        ("Çorba olarak ne önerirsin?", ["Mercimek Çorbası"], ["Fırın Sütlaç", "Ayran"]),
        ("Yemek olarak ne önerirsin?", ["Izgara Tavuk Salata"], ["Mercimek Çorbası", "Fırın Sütlaç"]),
    ],
)
def test_category_specific_recommendations_stay_within_category(
    manager,
    message,
    expected_terms,
    unexpected_terms,
):
    response = manager.handle_message(message)

    assert "öner" in response.casefold()
    for term in expected_terms:
        assert term in response
    for term in unexpected_terms:
        assert term not in response


def test_general_recommendation_stays_supported(manager):
    response = manager.handle_message("Ne önerirsin?")

    assert "Öneri" in response


def test_existing_supported_item_order_still_works(manager):
    response = manager.handle_message("Ayran sipariş etmek istiyorum.")

    assert "Ekledim" in response
    assert "Ayran" in response


def test_existing_price_question_still_concise(manager):
    response = manager.handle_message("Ayran ne kadar?")

    assert response == "Yayık Ayran 45.00 TL."


def test_existing_drink_listing_still_works(manager):
    response = manager.handle_message("İçecek seçenekleri neler?")

    assert "İçecek seçeneklerimiz" in response
    assert "Ayran" in response


def test_existing_unsupported_item_rejection_still_works():
    payload = run_grounded_demo("Pizza var mı?")

    assert payload["detected_intent"] == "unavailable_item"
    assert "bulunmuyor" in payload["final_response"]


@pytest.mark.parametrize(
    "message",
    [
        "Taco menünüzde var mı?",
        "Taco var mı?",
        "Taco sipariş edebilir miyim?",
    ],
)
def test_taco_queries_use_unsupported_item_rejection(message):
    payload = run_grounded_demo(message)

    assert payload["detected_intent"] == "unavailable_item"
    assert "bulunmuyor" in payload["final_response"]


def test_existing_off_topic_rejection_still_works():
    payload = run_grounded_demo("Bana hava durumunu söyler misiniz?")

    assert payload["detected_intent"] == "off_topic"
    assert "yardımcı olamıyorum" in payload["final_response"]


@pytest.mark.parametrize(
    "message",
    [
        "Kripto para hakkında bilgi verir misiniz?",
        "Kripto hakkında bilgi verir misiniz?",
        "Bitcoin hakkında bilgi verir misiniz?",
    ],
)
def test_crypto_info_queries_stay_off_topic(message):
    payload = run_grounded_demo(message)

    assert payload["detected_intent"] == "off_topic"
    assert "yardımcı olamıyorum" in payload["final_response"]


def test_grounded_builder_marks_restaurant_info_as_supported():
    builder = GroundedResultBuilder(MENU_PATH, RESTAURANT_INFO_PATH)
    result = builder.build("Kart geçiyor mu?")

    assert result.action.intent == "restaurant_info"
    assert result.action.is_supported is True
    assert "kredi kartı" in result.canonical_response
