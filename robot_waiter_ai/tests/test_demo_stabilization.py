from pathlib import Path

import pytest

from robot_waiter_ai.assistant.dialogue_manager import DialogueManager
from robot_waiter_ai.demo.voice_web_demo import HTML_PATH
from robot_waiter_ai.inference.grounded_demo import run_grounded_demo


@pytest.fixture
def manager():
    base_dir = Path(__file__).resolve().parents[1]
    return DialogueManager(
        base_dir / "data" / "menu.yaml",
        base_dir / "data" / "restaurant_info.yaml",
    )


@pytest.mark.parametrize(
    "message, expected",
    [
        ("Menüde neler var?", "Kategoriler"),
        ("Menünüzde neler var?", "Kategoriler"),
        ("İçecek seçenekleri neler?", "İçecek seçeneklerimiz"),
        ("İçecekler neler?", "İçecek seçeneklerimiz"),
        ("Menüde hangi içecekler var?", "İçecek seçeneklerimiz"),
        ("Tatlı seçenekleri neler?", "Tatlı seçeneklerimiz"),
        ("Çorba seçenekleri neler?", "Çorba seçeneklerimiz"),
        ("Ana yemek seçenekleri neler?", "Ana Yemek seçeneklerimiz"),
        ("yemekler ne", "Ana Yemek seçeneklerimiz"),
        ("Menüdeki yemekleri say", "Ana Yemek seçeneklerimiz"),
    ],
)
def test_supervisor_menu_category_phrases_are_menu_oriented(manager, message, expected):
    response = manager.handle_message(message)

    assert expected in response
    assert "Siparişe eklemek istediğiniz ürünü yazar mısınız?" not in response


@pytest.mark.parametrize(
    "message, expected",
    [
        ("Ayran ne kadar?", "Yayık Ayran 45.00 TL."),
        ("Ayran fiyatı nedir?", "Yayık Ayran 45.00 TL."),
        ("Et Döner kaç TL?", "Et Döner 280.00 TL."),
    ],
)
def test_supervisor_price_phrases_are_concise(manager, message, expected):
    response = manager.handle_message(message)

    assert response == expected
    assert "Alerjenler" not in response


def test_grounded_demo_keeps_ingredient_detail_and_allergy_caution():
    payload = run_grounded_demo("Kremalı Mantar Çorbası içinde ne var?")

    assert payload["detected_intent"] == "menu_question"
    assert "dağ mantarları" in payload["final_response"]
    assert "teyit" in payload["final_response"]


def test_grounded_demo_keeps_refusals_for_unsupported_and_off_topic():
    unsupported = run_grounded_demo("Pizza var mı?")
    off_topic = run_grounded_demo("Bana hava durumunu söyler misiniz?")

    assert unsupported["detected_intent"] == "unavailable_item"
    assert "bulunmuyor" in unsupported["final_response"]
    assert off_topic["detected_intent"] == "off_topic"
    assert "yardımcı olamıyorum" in off_topic["final_response"]


@pytest.mark.parametrize(
    "message, expected_quantity_text",
    [
        ("2 ayran daha", "2 x Yayık Ayran"),
        ("bir ayran daha", "1 x Yayık Ayran"),
    ],
)
def test_grounded_demo_supports_add_order_shorthand(message, expected_quantity_text):
    payload = run_grounded_demo(message)

    assert payload["detected_intent"] == "add_item"
    assert expected_quantity_text in payload["final_response"]


def test_voice_demo_includes_clickable_demo_phrases():
    html = HTML_PATH.read_text(encoding="utf-8")

    assert "data-phrase" in html
    assert "Ayran ne kadar?" in html
    assert "İçecek seçenekleri neler?" in html
    assert "sendMessage();" in html
