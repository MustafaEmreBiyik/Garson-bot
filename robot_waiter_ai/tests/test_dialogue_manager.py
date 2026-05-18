from pathlib import Path

import pytest

from robot_waiter_ai.assistant.dialogue_manager import DialogueManager


@pytest.fixture
def manager():
    base_dir = Path(__file__).resolve().parents[1]
    return DialogueManager(
        base_dir / "data" / "menu.yaml",
        base_dir / "data" / "restaurant_info.yaml",
    )


def test_greeting_response(manager):
    response = manager.handle_message("Merhaba")
    assert "Merhaba" in response
    assert "hoş geldiniz" in response.casefold()


def test_add_order_flow(manager):
    response = manager.handle_message("2 Ayran istiyorum")
    assert "Ekledim" in response
    assert "Ayran" in response
    assert manager.order.items["b1"].quantity == 2

    response = manager.handle_message("ayran alabilir miyim 3 tane")
    assert "Ekledim" in response
    assert manager.order.items["b1"].quantity == 5

    response = manager.handle_message("bir mercimek corbasi ekle")
    assert "Ekledim" in response
    assert "Mercimek" in response
    assert manager.order.items["s1"].quantity == 1


def test_add_order_flow_handles_turkish_characters(manager):
    response = manager.handle_message("Bir mercimek çorbası ekle")
    assert "Ekledim" in response
    assert "Mercimek" in response
    assert manager.order.items["s1"].quantity == 1


@pytest.mark.parametrize(
    "message, item_id, expected_quantity",
    [
        ("2 ayran daha", "b1", 2),
        ("bir ayran daha", "b1", 1),
        ("bir tane ayran daha", "b1", 1),
        ("2 limonata daha", "b2", 2),
    ],
)
def test_add_order_shorthand_phrases(manager, message, item_id, expected_quantity):
    response = manager.handle_message(message)

    assert "Ekledim" in response
    assert manager.order.items[item_id].quantity == expected_quantity


def test_remove_order(manager):
    manager.handle_message("2 ayran istiyorum")
    assert "b1" in manager.order.items
    response = manager.handle_message("ayranı çıkar")
    assert "Çıkardım" in response
    assert "b1" not in manager.order.items


def test_clear_order(manager):
    manager.handle_message("ayran ekle")
    response = manager.handle_message("siparişi temizle")
    assert "temizlendi" in response
    assert len(manager.order.items) == 0


def test_summarize_order(manager):
    manager.handle_message("ayran ekle")
    response = manager.handle_message("siparişim ne")
    assert "Ayran" in response
    assert "Toplam" in response
    assert "Onaylamak ister misiniz?" in response


def test_confirm_order_with_non_empty_order(manager):
    manager.handle_message("2 Ayran istiyorum")
    response = manager.handle_message("Siparişi onayla")
    assert "Siparişinizi onaylıyorum." in response
    assert "2 x Ayran" in response
    assert "MVP/demo onayıdır" in response


def test_confirm_order_when_empty(manager):
    response = manager.handle_message("Onaylıyorum")
    assert "aktif bir siparişiniz görünmüyor" in response
    assert "Önce" in response


def test_confirm_order_natural_turkish_phrases(manager):
    manager.handle_message("Bir mercimek çorbası ekle")
    response = manager.handle_message("Bu sipariş doğru")
    assert "Siparişinizi onaylıyorum." in response
    assert "Mercimek Çorbası" in response

    response = manager.handle_message("Evet doğru")
    assert "Siparişinizi onaylıyorum." in response


def test_menu_question(manager):
    response = manager.handle_message("ayranın fiyatı nedir")
    assert "Ayran" in response
    assert "45.00 TL" in response
    assert response == "Ayran 45.00 TL."
    assert "Alerjenler" not in response
    assert "Tuzlu yoğurt içeceği" not in response


def test_price_question_ne_kadar_is_concise(manager):
    response = manager.handle_message("Ayran ne kadar?")
    assert response == "Ayran 45.00 TL."


def test_price_question_fiyat_word_is_concise(manager):
    response = manager.handle_message("Ayran fiyatı nedir?")
    assert response == "Ayran 45.00 TL."


def test_ingredient_question_still_returns_detail_and_caution(manager):
    response = manager.handle_message("Domates Çorbası içinde ne var?")
    assert "Domates bazlı" in response
    assert "Alerjenler" in response
    assert "teyit" in response


def test_item_allergy_question_keeps_cautious_language(manager):
    response = manager.handle_message("Ayran süt ürünü içeriyor mu?")
    assert "Ayran" in response
    assert "teyit" in response
    assert "kesinlikle güvenli" not in response


def test_category_specific_menu_question_lists_category_items(manager):
    response = manager.handle_message("İçecek seçenekleri neler?")
    assert "İçecek seçeneklerimiz" in response
    assert "Ayran" in response
    assert "Limonata" in response
    assert "Siparişe eklemek istediğiniz ürünü yazar mısınız?" not in response


def test_category_question_with_turkish_characters(manager):
    response = manager.handle_message("Menüde neler var?")
    assert "Kategoriler" in response
    assert "Çorba" in response


@pytest.mark.parametrize(
    "message",
    [
        "yemekler ne",
        "yemek seçenekleri neler",
        "ana yemekler neler",
        "Menüdeki yemekleri say",
        "Menüde hangi yemekler var?",
    ],
)
def test_main_dish_alias_questions_list_main_dishes(manager, message):
    response = manager.handle_message(message)

    assert "Ana Yemek seçeneklerimiz" in response
    assert "Izgara Tavuk Salata" in response
    assert "Etli Güveç" in response


def test_recommendation_with_turkish_characters(manager):
    response = manager.handle_message("Ne önerirsiniz?")
    assert "Öneri" in response


def test_allergy_response(manager):
    response = manager.handle_message("alerjim var")
    assert "Alerji" in response


def test_gluten_free_question_uses_cautious_allergy_response(manager):
    response = manager.handle_message("Glutensiz seçenek var mı?")
    assert "Alerji" in response
    assert "teyit" in response


def test_fallback_response(manager):
    response = manager.handle_message("bana bir fikra anlat")
    assert "yardımcı olamıyorum" in response
