"""
Unit tests for speech/pronunciation.py — yabancı-yazımlı kelime telaffuz haritası.

Saf metin dönüşümü (piper gerektirmez) + PiperTTS entegrasyonu (dönüşümün
sentezden önce uygulandığı). Gerçek espeak fonem kanıtı testte değil; ayrı
bir --debug koşusuyla (scripts dışı, elle) gösterilir.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from robot_waiter_ai.speech.pronunciation import apply_pronunciation

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Düz eşleşme
# ---------------------------------------------------------------------------

def test_plain_single_word():
    assert apply_pronunciation("cheesecake") == "çizkeyk"


def test_plain_within_sentence():
    assert apply_pronunciation("Bir latte alır mısınız?") == "Bir late alır mısınız?"


@pytest.mark.parametrize("src,exp", [
    ("cappuccino", "kapuçino"),
    ("espresso", "espreso"),
    ("croissant", "kruvasan"),
    ("milkshake", "milkşeyk"),
    ("ketchup", "keçap"),
    ("smoothie", "ismuti"),
])
def test_map_entries(src, exp):
    assert apply_pronunciation(src) == exp


# ---------------------------------------------------------------------------
# Ekli hâller (Türkçe ek + kesme işareti) — kök çevrilir, ek korunur
# ---------------------------------------------------------------------------

def test_suffix_apostrophe_ascii():
    assert apply_pronunciation("cheesecake'i beğendim") == "çizkeyk'i beğendim"


def test_suffix_apostrophe_unicode_right_quote():
    # U+2019 ' (Türkçe klavyelerde/otomatik düzeltmede yaygın)
    assert apply_pronunciation("latte’niz hazır") == "late’niz hazır"


def test_suffix_multiple_forms():
    assert apply_pronunciation("cappuccino'yu ve cola'ları getir") == \
        "kapuçino'yu ve kola'ları getir"


# ---------------------------------------------------------------------------
# Kelime-içi YANLIŞ-POZİTİF olmamalı (_OFFENSIVE "göt"/götürür hatası tekrarı)
# ---------------------------------------------------------------------------

def test_no_match_inside_word_cola_in_chocolate():
    # "chocolate" içinde "cola" substring'i var ama kelime sınırı yok → dokunma
    assert apply_pronunciation("chocolate") == "chocolate"


def test_no_match_turkish_word_untouched():
    # "çikolata" hiç değişmemeli
    assert apply_pronunciation("çikolatalı sütlaç") == "çikolatalı sütlaç"


def test_no_match_suffix_without_apostrophe_is_conservative():
    # "cookies" = kesme işaretsiz İngilizce çoğul → muhafazakâr: dokunma
    # (Türkçe'de "cookie'ler" yazılır; kesme işaretsiz eş biçim nadirdir)
    assert apply_pronunciation("cookies") == "cookies"


# ---------------------------------------------------------------------------
# Büyük/küçük harf ve cümle-başı büyük harf korunur
# ---------------------------------------------------------------------------

def test_sentence_initial_capital_preserved():
    assert apply_pronunciation("Cheesecake çok lezzetli.") == "Çizkeyk çok lezzetli."


def test_uppercase_word_first_letter_capitalized():
    assert apply_pronunciation("COLA") == "Kola"


def test_case_insensitive_match():
    assert apply_pronunciation("Latte") == "Late"


# ---------------------------------------------------------------------------
# Çok kelimeli / uzun-önce öncelik (Coca-Cola > cola, club sandwich > sandwich)
# ---------------------------------------------------------------------------

def test_multiword_coca_cola_beats_cola():
    assert apply_pronunciation("Coca-Cola") == "Koka kola"


def test_multiword_coca_cola_with_suffix():
    assert apply_pronunciation("Coca-Cola'yı açar mısın") == "Koka kola'yı açar mısın"


def test_multiword_club_sandwich_beats_sandwich():
    assert apply_pronunciation("club sandwich") == "klap sendviç"


# ---------------------------------------------------------------------------
# Birden çok kelime aynı cümlede
# ---------------------------------------------------------------------------

def test_multiple_words_in_one_sentence():
    assert apply_pronunciation("Yanında latte ve cheesecake olsun.") == \
        "Yanında late ve çizkeyk olsun."


# ---------------------------------------------------------------------------
# Sözlükte olmayan / saf Türkçe metin aynen geçer
# ---------------------------------------------------------------------------

def test_dictionary_absent_text_unchanged():
    src = "Mercimek çorbası seksen beş lira, afiyet olsun."
    assert apply_pronunciation(src) == src


def test_empty_string_unchanged():
    assert apply_pronunciation("") == ""


def test_turkish_dotted_capital_i_sentence_passes():
    # İ-fix kuralına uyum + İ içeren metnin bozulmaması
    assert apply_pronunciation("İki cheesecake lütfen") == "İki çizkeyk lütfen"


# ---------------------------------------------------------------------------
# PiperTTS entegrasyonu — dönüşüm sentezden HEMEN ÖNCE uygulanır
# ---------------------------------------------------------------------------

def test_piper_applies_pronunciation_before_synthesis(tmp_path):
    from robot_waiter_ai.speech import tts as tts_mod
    from robot_waiter_ai.speech.tts import PiperTTS

    captured: dict[str, bytes] = {}

    def fake_run(cmd, input=None, capture_output=None, timeout=None):
        captured["input"] = input
        out = cmd[cmd.index("--output_file") + 1]
        Path(out).write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
        result = MagicMock()
        result.returncode = 0
        result.stderr = b""
        return result

    with patch("robot_waiter_ai.speech.tts._find_piper_binary", return_value="/fake/piper"), \
         patch("robot_waiter_ai.speech.tts._find_piper_model", return_value=tmp_path / "m.onnx"), \
         patch.object(tts_mod.subprocess, "run", side_effect=fake_run):
        tts = PiperTTS()
        wav = asyncio.run(tts.synthesize("Bir cheesecake ve cappuccino alabilir miyim?"))

    assert wav[:4] == b"RIFF"
    sent = captured["input"].decode("utf-8")
    # Yabancı yazım piper'a GİTMEZ; Türkçe fonetik yazım gider
    assert "cheesecake" not in sent
    assert "cappuccino" not in sent
    assert "çizkeyk" in sent
    assert "kapuçino" in sent
