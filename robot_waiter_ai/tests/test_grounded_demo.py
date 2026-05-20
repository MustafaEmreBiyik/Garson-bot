from robot_waiter_ai.inference.grounded_demo import run_grounded_demo


def test_unavailable_item_without_paraphrase_returns_canonical_refusal():
    payload = run_grounded_demo("Pizza var mı?")

    assert payload["detected_intent"] == "unavailable_item"
    assert payload["final_response"] == payload["canonical_response"]
    assert payload["used_paraphrase"] is False


def test_unsafe_paraphrase_introducing_pizza_is_rejected():
    payload = run_grounded_demo("Pizza var mı?", paraphrase_candidate="Evet, pizzamız var.")

    assert payload["final_response"] == payload["canonical_response"]
    assert payload["used_paraphrase"] is False
    assert "introduced unsupported item" in payload["rejection_reasons"]


def test_safe_paraphrase_for_greeting_is_accepted():
    payload = run_grounded_demo("Merhaba", paraphrase_candidate="Merhaba, hoş geldiniz.")

    assert payload["detected_intent"] == "greeting"
    assert payload["final_response"] == "Merhaba, hoş geldiniz."
    assert payload["used_paraphrase"] is True
    assert payload["rejection_reasons"] == []


def test_allergy_paraphrase_missing_required_terms_is_rejected():
    payload = run_grounded_demo(
        "Süt ürünlerine alerjim var",
        paraphrase_candidate="Bu konuda yardımcı olabilirim.",
    )

    assert payload["final_response"] == payload["canonical_response"]
    assert payload["used_paraphrase"] is False
    assert "missing allergy confirmation wording" in payload["rejection_reasons"]


def test_price_paraphrase_changing_price_is_rejected():
    payload = run_grounded_demo(
        "Ayranın fiyatı nedir?",
        paraphrase_candidate="Ayran 15.00 TL.",
    )

    assert payload["final_response"] == payload["canonical_response"]
    assert payload["used_paraphrase"] is False
    assert "missing price" in payload["rejection_reasons"]


def test_returned_dict_contains_expected_fields():
    payload = run_grounded_demo("Pizza var mı?")

    assert set(payload.keys()) == {
        "user_message",
        "detected_intent",
        "canonical_response",
        "paraphrase_candidate",
        "final_response",
        "used_paraphrase",
        "rejection_reasons",
        "must_preserve_terms",
        "must_not_introduce",
        "metadata",
    }


def test_price_only_question_returns_concise_price_answer():
    payload = run_grounded_demo("Ayran ne kadar?")

    assert payload["detected_intent"] == "price_question"
    assert payload["final_response"] == "Yayık Ayran 45.00 TL."
    assert "Alerjenler" not in payload["final_response"]
    assert "Tuzlu yoğurt" not in payload["final_response"]


def test_ingredient_question_keeps_description_and_caution():
    payload = run_grounded_demo("Kremalı Mantar Çorbası içinde ne var?")

    assert "dağ mantarları" in payload["final_response"]
    assert "Alerjenler" in payload["final_response"]
    assert "teyit" in payload["final_response"]


def test_item_allergy_question_keeps_cautious_language():
    payload = run_grounded_demo("Ayran süt ürünü içeriyor mu?")

    assert payload["detected_intent"] == "allergen_question"
    assert "teyit" in payload["final_response"]
    assert "kesinlikle güvenli" not in payload["final_response"]


def test_category_question_returns_menu_oriented_response():
    payload = run_grounded_demo("İçecek seçenekleri neler?")

    assert payload["detected_intent"] == "menu_question"
    assert "İçecek seçeneklerimiz" in payload["final_response"]
    assert "Siparişe eklemek istediğiniz ürünü yazar mısınız?" not in payload["final_response"]
