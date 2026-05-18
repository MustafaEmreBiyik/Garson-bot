from pathlib import Path

from robot_waiter_ai.inference.hybrid_orchestrator import HybridOrchestrator
from robot_waiter_ai.inference.mock_nlu_adapter import MockNLUAdapter


BASE_DIR = Path(__file__).resolve().parents[1]


def _build_orchestrator() -> HybridOrchestrator:
    return HybridOrchestrator(
        menu_path=BASE_DIR / "data" / "menu.yaml",
        restaurant_info_path=BASE_DIR / "data" / "restaurant_info.yaml",
        nlu_adapter=MockNLUAdapter(),
    )


def test_hybrid_orchestrator_rejects_items_not_in_menu():
    orchestrator = _build_orchestrator()

    result = orchestrator.handle_message("Falafel var mı?")

    assert "Uydurma bilgi vermek istemem" in result.response_text
    assert result.parsed_intent.intent == "unsupported_item"


def test_hybrid_orchestrator_does_not_invent_prices():
    orchestrator = _build_orchestrator()

    result = orchestrator.handle_message("Ayran ne kadar?")

    assert result.response_text == "Ayran 45.00 TL."
    assert "tahminen" not in result.response_text.casefold()


def test_hybrid_orchestrator_keeps_off_topic_rejection():
    orchestrator = _build_orchestrator()

    for message in ["Bitcoin alınır mı?", "Hava durumu nasıl?", "Python kodu yazar mısın?"]:
        result = orchestrator.handle_message(message)
        assert "menü veya siparişle ilgili" in result.response_text.casefold()
        assert result.parsed_intent.intent == "off_topic"


def test_hybrid_orchestrator_asks_clarification_on_low_confidence_restaurant_message():
    orchestrator = _build_orchestrator()

    result = orchestrator.handle_message("Şundan iki tane daha")

    assert "netleştiremedim" in result.response_text
    assert result.parsed_intent.intent == "unclear"
    assert result.used_deterministic_fallback is True


def test_hybrid_orchestrator_routes_flexible_category_question_to_deterministic_logic():
    orchestrator = _build_orchestrator()

    result = orchestrator.handle_message("Soğuk içecek var mı?")

    assert "İçecek seçeneklerimiz" in result.response_text
    assert "Ayran" in result.response_text
    assert "Limonata" in result.response_text


def test_hybrid_orchestrator_routes_recommendation_request_without_bypassing_menu_rules():
    orchestrator = _build_orchestrator()

    result = orchestrator.handle_message("Bana hafif bir yemek öner")

    assert "Izgara Tavuk Salata" in result.response_text
    assert "öner" in result.response_text.casefold()
