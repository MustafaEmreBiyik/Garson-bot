"""Fast-path selam/veda ayrımı testleri (scripts/demo_usb.py, görev #25 a).

"İyi günler" hem _GREETING_TRIGGERS hem _FAREWELL_TRIGGERS üyesi; eski kodda
veda dalı önce kontrol edildiğinden açılışta müşteri uğurlanıp oturum
kapanıyordu. Ayrım artık oturum bağlamıyla (_salutation_intent, in_convo):
- Taze açılış (in_convo=False) → selam yanıtı, oturum açık kalır.
- Yerleşik konuşma (in_convo=True) → veda, oturum kapanır.
- Tek anlamlı vedalar ("görüşürüz", "güle güle") her bağlamda vedadır.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from demo_usb import (  # noqa: E402
    _FAREWELL_TEMPLATES,
    _GREETING_TEMPLATES,
    _fast_path_reply,
    _salutation_intent,
)

pytestmark = pytest.mark.unit


# --- Asıl bug senaryosu: açılışta "İyi günler" veda sanılıyordu ---

def test_iyi_gunler_acilista_selam():
    """Taze açılışta 'İyi günler' → selam, oturum KAPANMAZ (veda değil)."""
    assert _salutation_intent("İyi günler", in_convo=False) == "greeting"
    assert _fast_path_reply("İyi günler", in_convo=False) in _GREETING_TEMPLATES


def test_iyi_gunler_konusma_icinde_veda():
    """Yerleşik konuşmada 'İyi günler' → veda (mevcut kapanış davranışı)."""
    assert _salutation_intent("İyi günler", in_convo=True) == "farewell"
    assert _fast_path_reply("İyi günler", in_convo=True) in _FAREWELL_TEMPLATES


def test_iyi_gunler_gorusuruz_acilista_bile_veda():
    """'İyi günler, görüşürüz' → 'görüşürüz' tek anlamlı, açılışta bile veda."""
    assert _salutation_intent("İyi günler, görüşürüz", in_convo=False) == "farewell"
    assert _fast_path_reply("İyi günler, görüşürüz", in_convo=False) in _FAREWELL_TEMPLATES
    assert _salutation_intent("İyi günler, görüşürüz", in_convo=True) == "farewell"


def test_iyi_aksamlar_ayni_kural():
    """'İyi akşamlar' da çift anlamlı — açılışta selam, konuşmada veda."""
    assert _salutation_intent("İyi akşamlar", in_convo=False) == "greeting"
    assert _salutation_intent("İyi akşamlar", in_convo=True) == "farewell"


# --- Regresyon: tek anlamlı selam/veda davranışı değişmemeli ---

def test_merhaba_her_baglamda_selam():
    assert _salutation_intent("Merhaba", in_convo=False) == "greeting"
    assert _salutation_intent("Merhaba", in_convo=True) == "greeting"
    assert _fast_path_reply("Merhaba", in_convo=False) in _GREETING_TEMPLATES


def test_gule_gule_her_baglamda_veda():
    assert _salutation_intent("Güle güle", in_convo=False) == "farewell"
    assert _salutation_intent("Güle güle", in_convo=True) == "farewell"
    assert _fast_path_reply("Güle güle", in_convo=True) in _FAREWELL_TEMPLATES


def test_tesekkurler_veda_kalir():
    """'Teşekkürler.' tek anlamlı veda — S12 guard testlerinin dayandığı davranış."""
    assert _salutation_intent("Teşekkürler.", in_convo=True) == "farewell"
    assert _fast_path_reply("Teşekkürler.", in_convo=True) in _FAREWELL_TEMPLATES


# --- Fast-path kapsam sınırları korunmalı ---

def test_soru_isareti_llm_e_kalir():
    assert _fast_path_reply("İyi günler, menüde ne var?", in_convo=False) is None


def test_siparis_fiili_llm_e_kalir():
    assert _fast_path_reply("İyi günler, köfte istiyorum", in_convo=False) is None


def test_uzun_cumle_llm_e_kalir():
    assert _fast_path_reply(
        "İyi günler size hepinize buradan tekrar tekrar", in_convo=False) is None
