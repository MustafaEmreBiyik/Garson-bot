"""E19 kelime-kalıbı guard'ı birim testleri (scripts/demo_usb.py).

Kök neden: W11 kapanış kuralı revizyonu (görev #29, commit 58d3ec8) sonrası
ürün-açıklaması sorularında model bazen kuralı ("Getireyim mi?"/"İster
misiniz?" ile bit) kendi soru kalıbıyla (ör. "...edilir mi?") çiğniyor. Yanıt
"?" ile bittiği için genel "?" kontrolü bunu yakalamaz. WSL2'de doğrulanan
prompt güçlendirmesi (llama_cpp_backend.py + qwen3_backend.py, "ZORUNLU/
İSTİSNASIZ" vurgusu) tek başına yetersiz kaldı — kod katmanında sabitlendi.

Not: model RNG durumu çağrı pozisyonuna bağlı olduğundan aynı girdi bazen
doğru bazen yanlış kalıp üretebilir (bkz. PROJE_DURUMU.md "determinizm
kapsamı" notu) — bu guard, hangi pozisyonda gelirse gelsin metni sabitler.

Ses ZATEN _speak_streaming içinde cümle cümle çalındığından burada
DÜZELTİLEMEZ — yalnızca reply metni (LLM history + log + eval) düzeltilir.

Gerçek menu.yaml kullanılır (robot_waiter_ai/data/menu.yaml).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from demo_usb import _apply_e19_word_pattern_guard, _load_menu_lookup  # noqa: E402

pytestmark = pytest.mark.unit

_LOOKUP = _load_menu_lookup()


# ---------------------------------------------------------------------------
# Yanlış kalıp → düzeltilmeli
# ---------------------------------------------------------------------------

def test_wrong_pattern_replaced_with_getireyim_mi():
    user_text = "Kremalı mantar çorbası nasıl bir şey?"
    bad_reply = ("Taze dağ mantarları ve kremanın eşsiz uyumuyla yapılır. "
                "Sıcak servis edilir mi?")
    fixed = _apply_e19_word_pattern_guard(user_text, bad_reply, _LOOKUP)
    assert fixed.endswith("Getireyim mi?")
    assert "servis edilir mi" not in fixed.lower()
    # Açıklama gövdesi korunmalı, yalnızca yanlış kapanış cümlesi değişmeli
    assert "taze dağ mantarları" in fixed.lower()


def test_wrong_pattern_single_sentence():
    user_text = "Izgara köfte nasıl hazırlanıyor?"
    bad_reply = "Bu tabak çok sever misiniz?"
    fixed = _apply_e19_word_pattern_guard(user_text, bad_reply, _LOOKUP)
    assert fixed == "Getireyim mi?" or fixed.endswith("Getireyim mi?")


@pytest.mark.parametrize("wrong_ending", [
    "Çok sever misiniz?",
    "Beğenirsiniz sanırım?",
    "İlginizi çeker mi?",
])
def test_various_wrong_endings_normalized(wrong_ending):
    # _DESCRIPTION_TRIGGERS: {"nasıl", "nedir", "ne gibi", "tarif", "anlat", "hakkında"}
    user_text = "Künefe nasıl bir tatlı?"
    bad_reply = f"Hatay peyniri ve tel kadayıfla yapılır. {wrong_ending}"
    fixed = _apply_e19_word_pattern_guard(user_text, bad_reply, _LOOKUP)
    assert fixed.endswith("Getireyim mi?")


# ---------------------------------------------------------------------------
# Doğru kalıp → DOKUNULMAMALI (idempotent)
# ---------------------------------------------------------------------------

def test_already_getireyim_mi_untouched():
    user_text = "Mercimek çorbası nasıl bir şey?"
    good_reply = "Kırmızı mercimek ve havuçla yapılır. Getireyim mi?"
    assert _apply_e19_word_pattern_guard(user_text, good_reply, _LOOKUP) == good_reply


def test_already_ister_misiniz_untouched():
    user_text = "Şalgam suyu nasıl bir içecek?"
    good_reply = "Acılı ve acısız seçeneği var, sindirimi kolaylaştırır. İster misiniz?"
    assert _apply_e19_word_pattern_guard(user_text, good_reply, _LOOKUP) == good_reply


# ---------------------------------------------------------------------------
# Açıklama sorusu DEĞİLSE → guard hiç devreye girmemeli
# ---------------------------------------------------------------------------

def test_not_description_question_untouched():
    user_text = "Bir mercimek çorbası alayım."
    reply = "Elbette, Mercimek Çorbası 85 TL. Başka bir şey alır mısınız?"
    assert _apply_e19_word_pattern_guard(user_text, reply, _LOOKUP) == reply


def test_greeting_untouched():
    user_text = "Merhaba"
    reply = "Merhaba! Çorba, ana yemek, tatlı ve içecek çeşitlerimiz var. Ne arzu edersiniz?"
    assert _apply_e19_word_pattern_guard(user_text, reply, _LOOKUP) == reply


def test_bill_request_untouched():
    user_text = "Hesabı alabilir miyim?"
    reply = "Toplam 240 TL. Afiyet olsun!"
    assert _apply_e19_word_pattern_guard(user_text, reply, _LOOKUP) == reply
