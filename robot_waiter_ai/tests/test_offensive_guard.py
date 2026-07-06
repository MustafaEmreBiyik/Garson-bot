"""Guard 3 küfür/hakaret tespiti testleri (scripts/demo_usb.py, V04 — C paketi 4-b).

_is_offensive() saf fonksiyonu: kaba/küfürlü girdi LLM'e ulaşmadan sabit
S29 yanıtına düşer (ana döngü Guard 3, history'ye yazılmaz). Genişletme
kuralı: yalnızca tek anlamlı terimler — guard meşru sipariş/soru
cümlelerinde ASLA tetiklenmemeli (negatif testler bunu kilitler).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from demo_usb import _is_offensive  # noqa: E402

pytestmark = pytest.mark.unit


# --- Mevcut davranış korunmalı (V04 ham eval girdisi dahil) ---

def test_mevcut_aptal_davranisi():
    assert _is_offensive("Aptal robot, siparişimi karıştırdın!")


def test_mevcut_kufur():
    assert _is_offensive("Siktir git buradan")


# --- Genişletilen terimler (C paketi 4-b) → guard tetiklenmeli ---

@pytest.mark.parametrize("cumle", [
    # hakaret — zeka/kişilik
    "Gerzek misin sen?",
    "Dangalak robot",
    "Budala gibi davranma",
    "Beyinsiz makine",
    "Hödük gibi bakma öyle",
    "Avanak mısın nesin",
    "Denyo musun sen",
    "Mal mısın sen?",
    "Beceriksiz robot, yine yanlış getirdin",
    "İşe yaramaz bir şeysin",
    # hakaret — ağır
    "Kahpe dünya deme bana",
    "Kaltak seni",
    "Sürtük müsün",
    "Yavşak robot",
    "Puşt herif",
    "Pezevenk misin",
    "Gavat gibi dolaşma",
    "İbne misin sen",
    "Terbiyesiz robot",
    "Ahlaksız şey",
    # küfür — cinsel/argo
    "Sikik robot",
    "Amına koyayım böyle servisin",
    "Amcık ağızlı",
    "Yarrak gibi robot",
    "Yarak kafalı",
    # kaba emir / kovma
    "Kes sesini artık",
    "Kapa çeneni",
    "Çeneni kapa da dinle",
])
def test_genisletilen_terimler_tetikler(cumle):
    assert _is_offensive(cumle)


# --- NEGATİF: meşru sipariş/soru cümleleri → guard ASLA tetiklenmez ---

@pytest.mark.parametrize("cumle", [
    "Bir köfte alayım.",
    "Çorbadan ne var?",
    "İki ayran, bir de künefe lütfen.",
    "Et döner soğansız olsun.",
    "Hesabı alabilir miyim?",
    "Adisyonu getirir misiniz?",       # "adi" bilinçli listede DEĞİL
    "Terbiyeli çorbanız var mı?",      # "terbiyesiz" değil, mutfak terimi
    "Susamlı bir şey var mı?",         # "sus" bilinçli listede DEĞİL
    "Malzemeleri nelerdir?",           # "mal" bilinçli listede DEĞİL
    "Hayvan gibi acıktım, iki döner alayım.",  # meşru deyim
    "Acılı olan hangisi?",             # "lan" bilinçli listede DEĞİL
    "Salatanın yanında ne önerirsiniz?",
    "Şalgam suyu acılı mı oluyor?",
    "Mercimek çorbası ve sütlaç istiyorum.",
])
def test_mesru_cumleler_tetiklemez(cumle):
    assert not _is_offensive(cumle)
