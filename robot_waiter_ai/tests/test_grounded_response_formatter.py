from pathlib import Path

from robot_waiter_ai.assistant.dialogue_manager import DialogueManager
from robot_waiter_ai.inference.grounded_response_formatter import (
    explain_paraphrase_rejection,
    format_grounded_response,
)
from robot_waiter_ai.inference.grounded_result_builder import GroundedResultBuilder


BASE_DIR = Path(__file__).resolve().parents[1]
MENU_PATH = BASE_DIR / "data" / "menu.yaml"
RESTAURANT_INFO_PATH = BASE_DIR / "data" / "restaurant_info.yaml"


def _build_builder() -> GroundedResultBuilder:
    manager = DialogueManager(MENU_PATH, RESTAURANT_INFO_PATH)
    return GroundedResultBuilder(MENU_PATH, RESTAURANT_INFO_PATH, manager=manager)


def test_no_paraphrase_returns_canonical_response():
    builder = _build_builder()
    result = builder.build("Merhaba")

    assert format_grounded_response(result) == result.canonical_response


def test_safe_paraphrase_is_accepted():
    builder = _build_builder()
    result = builder.build("Ayranın fiyatı nedir?")
    candidate = "Fiyat bilgisi: Ayran 45.00 TL."

    assert format_grounded_response(result, candidate) == candidate
    assert explain_paraphrase_rejection(result, candidate) == []


def test_unsafe_paraphrase_missing_required_term_is_rejected():
    builder = _build_builder()
    result = builder.build("Siparişi temizle")
    candidate = "Siparişinizi sıfırladım."

    assert format_grounded_response(result, candidate) == result.canonical_response
    assert "missing required term" in explain_paraphrase_rejection(result, candidate)


def test_unsafe_paraphrase_introducing_unavailable_item_is_rejected():
    builder = _build_builder()
    result = builder.build("Pizza var mı?")
    candidate = "Pizza: 100 TL, isterseniz ekleyebilirim."

    assert format_grounded_response(result, candidate) == result.canonical_response
    assert "introduced unsupported item" in explain_paraphrase_rejection(result, candidate)


def test_allergy_paraphrase_must_preserve_alerji_and_teyit():
    builder = _build_builder()
    result = builder.build("Süt ürünlerine alerjim var")
    safe_candidate = "Alerji konusunda dikkatli olalım ve mutfakla teyit edelim."
    unsafe_candidate = "Bu konuda yardımcı olabilirim."

    assert format_grounded_response(result, safe_candidate) == safe_candidate
    assert format_grounded_response(result, unsafe_candidate) == result.canonical_response
    assert "missing allergy confirmation wording" in explain_paraphrase_rejection(result, unsafe_candidate)


def test_price_paraphrase_must_preserve_exact_price_and_tl():
    builder = _build_builder()
    result = builder.build("Ayranın fiyatı nedir?")
    unsafe_candidate = "Fiyat bilgisi: Ayran 15.00 lira."

    assert format_grounded_response(result, unsafe_candidate) == result.canonical_response
    assert "missing price" in explain_paraphrase_rejection(result, unsafe_candidate)


def test_off_topic_paraphrase_must_preserve_refusal_meaning():
    builder = _build_builder()
    result = builder.build("Bana bir şiir yazar mısın?")
    safe_candidate = "Bu konuda yardımcı olamıyorum; menü veya siparişle ilgili yardımcı olabilirim."
    unsafe_candidate = "İşte bir şiir yazdım."

    assert format_grounded_response(result, safe_candidate) == safe_candidate
    assert format_grounded_response(result, unsafe_candidate) == result.canonical_response
    assert "contains forbidden term" in explain_paraphrase_rejection(result, unsafe_candidate)


def test_confirm_order_paraphrase_must_preserve_mvp_demo():
    builder = _build_builder()
    builder.build("Bir Ayran istiyorum")
    result = builder.build("Evet, onaylıyorum")
    safe_candidate = (
        "Siparişinizi onaylıyorum. 1 x Ayran için birim fiyat 45.00 TL, Toplam 45.00 TL. "
        "Not: Bu yalnızca MVP/demo onayıdır."
    )
    unsafe_candidate = "Siparişinizi onaylıyorum. Toplam 45.00 TL."

    assert format_grounded_response(result, safe_candidate) == safe_candidate
    assert format_grounded_response(result, unsafe_candidate) == result.canonical_response
    assert "missing required term" in explain_paraphrase_rejection(result, unsafe_candidate)
