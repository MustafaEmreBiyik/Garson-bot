from __future__ import annotations

from robot_waiter_ai.inference.structured_result import (
    GroundedAction,
    GroundedResult,
    MenuGrounding,
    OrderGrounding,
    SafetyGrounding,
    check_paraphrase_safety,
    ensure_forbidden_terms_absent,
    ensure_required_terms,
    validate_grounded_result,
)


def test_add_item_result_preserves_item_quantity_and_price():
    result = GroundedResult(
        action=GroundedAction(
            intent="add_item",
            user_message="2 Ayran istiyorum",
            normalized_user_message="2 ayran istiyorum",
            entities={"item": "Ayran", "quantity": 2},
            confidence=0.98,
            is_supported=True,
        ),
        menu=MenuGrounding(
            matched_items=[{"id": "ayran", "name": "Ayran"}],
            prices={"Ayran": 45.0},
        ),
        order=OrderGrounding(
            action_type="add_item",
            items=[
                {
                    "id": "ayran",
                    "name": "Ayran",
                    "quantity": 2,
                    "unit_price": 45.0,
                    "line_total": 90.0,
                }
            ],
            total_price=90.0,
            order_is_empty=False,
        ),
        safety=SafetyGrounding(),
        canonical_response="Ekledim: 2 x Ayran. Güncel toplam: 90.00 TL.",
        allowed_paraphrase=True,
        must_preserve_terms=["Ekledim", "TL"],
    )

    assert validate_grounded_result(result) == []
    safe_text = "Ekledim: 2 x Ayran, birim fiyatı 45.00 TL. Güncel toplam 90.00 TL oldu."
    assert check_paraphrase_safety(result, safe_text) == []


def test_price_question_preserves_exact_tl_price():
    result = GroundedResult(
        action=GroundedAction(
            intent="price_question",
            user_message="Ayranın fiyatı nedir?",
            entities={"item": "Ayran"},
        ),
        menu=MenuGrounding(
            matched_items=[{"id": "ayran", "name": "Ayran"}],
            prices={"Ayran": 45.0},
        ),
        order=OrderGrounding(action_type="price_question", order_is_empty=True),
        safety=SafetyGrounding(),
        canonical_response="Fiyat: Ayran 45.00 TL.",
        allowed_paraphrase=True,
        must_preserve_terms=["Fiyat", "Ayran", "45.00", "TL"],
    )

    assert check_paraphrase_safety(result, "Fiyat bilgisi: Ayran 45.00 TL.") == []
    errors = check_paraphrase_safety(result, "Fiyat bilgisi: Ayran 15.00 TL.")
    assert "Missing required term: 45.00" in errors


def test_allergen_question_requires_alerji_and_teyit():
    result = GroundedResult(
        action=GroundedAction(
            intent="allergen_question",
            user_message="Süt ürünlerine alerjim var",
            requires_safety_response=True,
        ),
        menu=MenuGrounding(),
        order=OrderGrounding(action_type="allergen_question", order_is_empty=True),
        safety=SafetyGrounding(
            safety_type="allergy_caution",
            must_include_terms=["Alerji", "teyit"],
            forbidden_claims=["kesinlikle güvenli", "hiç sorun yok"],
            requires_staff_confirmation=True,
        ),
        canonical_response="Alerji konusunda dikkatli olalım. Lütfen mutfakla teyit edelim.",
        allowed_paraphrase=True,
        must_preserve_terms=[],
    )

    assert validate_grounded_result(result) == []
    assert check_paraphrase_safety(
        result,
        "Alerji konusunda dikkatli olalım ve mutfakla teyit edelim.",
    ) == []
    errors = check_paraphrase_safety(result, "Bu seçenek kesinlikle güvenli görünüyor.")
    assert "Missing required term: Alerji" in errors
    assert "Missing required term: teyit" in errors
    assert "Forbidden term present: kesinlikle güvenli" in errors


def test_off_topic_requires_refusal_meaning():
    result = GroundedResult(
        action=GroundedAction(
            intent="off_topic",
            user_message="Bana bir şiir yazar mısın?",
            requires_safety_response=True,
            is_supported=False,
            reason="restaurant_scope_only",
        ),
        menu=MenuGrounding(),
        order=OrderGrounding(action_type="off_topic", order_is_empty=True),
        safety=SafetyGrounding(
            safety_type="scope_refusal",
            must_include_terms=["yardımcı olamıyorum"],
        ),
        canonical_response="Bu konuda yardımcı olamıyorum. Menü veya siparişle ilgili sorabilir misiniz?",
        allowed_paraphrase=True,
        must_preserve_terms=[],
        must_not_introduce=["şiir hazırladım", "işte bir şiir"],
    )

    assert check_paraphrase_safety(
        result,
        "Bu konuda yardımcı olamıyorum; menü veya siparişle ilgili yardımcı olabilirim.",
    ) == []


def test_unavailable_item_prevents_unsupported_menu_items():
    result = GroundedResult(
        action=GroundedAction(
            intent="unavailable_item",
            user_message="Pizza var mı?",
            entities={"item": "Pizza"},
            is_supported=False,
            reason="menu_item_not_found",
        ),
        menu=MenuGrounding(unavailable_items=["Pizza"]),
        order=OrderGrounding(action_type="unavailable_item", order_is_empty=True),
        safety=SafetyGrounding(),
        canonical_response="Pizza menümüzde bulunmuyor. İsterseniz mevcut kategorilerden öneri sunabilirim.",
        allowed_paraphrase=True,
        must_preserve_terms=["Pizza", "bulunmuyor"],
        must_not_introduce=["Pizza: ", "fiyatı", "eklendi"],
    )

    assert check_paraphrase_safety(
        result,
        "Pizza menümüzde bulunmuyor. İsterseniz mevcut kategorilerden öneri sunabilirim.",
    ) == []
    errors = check_paraphrase_safety(result, "Pizza: 100 TL, isterseniz ekleyebilirim.")
    assert "Forbidden term present: Pizza: " in errors


def test_confirm_order_preserves_demo_note():
    result = GroundedResult(
        action=GroundedAction(
            intent="confirm_order",
            user_message="Evet, onaylıyorum",
            entities={},
        ),
        menu=MenuGrounding(
            matched_items=[{"id": "ayran", "name": "Ayran"}],
            prices={"Ayran": 45.0},
        ),
        order=OrderGrounding(
            action_type="confirm_order",
            items=[{"id": "ayran", "name": "Ayran", "quantity": 1, "unit_price": 45.0}],
            total_price=45.0,
            order_is_empty=False,
            order_summary="1 x Ayran = 45.00 TL\nToplam: 45.00 TL",
            is_demo_confirmation=True,
        ),
        safety=SafetyGrounding(),
        canonical_response=(
            "Siparişinizi onaylıyorum.\n"
            "1 x Ayran = 45.00 TL\n"
            "Toplam: 45.00 TL\n"
            "Not: Bu yalnızca MVP/demo onayıdır; gerçek restoran gönderimi yapılmaz."
        ),
        allowed_paraphrase=True,
        must_preserve_terms=["Toplam", "MVP/demo", "Ayran", "45.00"],
    )

    assert validate_grounded_result(result) == []
    assert check_paraphrase_safety(
        result,
        "Siparişinizi onaylıyorum. 1 x Ayran için birim fiyat 45.00 TL, Toplam 45.00 TL. Not: Bu yalnızca MVP/demo onayıdır.",
    ) == []


def test_basic_term_helpers_report_missing_and_forbidden_terms():
    assert ensure_required_terms("Merhaba", ["Merhaba", "Hoş geldiniz"]) == ["Hoş geldiniz"]
    assert ensure_forbidden_terms_absent("Pizza: 100 TL", ["Pizza: ", "Hamburger"]) == ["Pizza: "]
