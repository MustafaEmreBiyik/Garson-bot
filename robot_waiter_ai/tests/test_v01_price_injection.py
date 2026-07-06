"""V01 fiyat enjeksiyonu birim testleri (scripts/demo_usb.py, C paketi kod görevi).

Modifikasyon onayında TL fiyat eksikliği fix'inin kalıcı regresyon güvencesi:
- _has_modification_request(): modifikasyon sinyali tespiti ("soğansız",
  "acılı", "X olsun" — görev #21 gereği "olsun" ekleme DEĞİL, sinyaldir).
- _modification_price_addition(): sipariş + modifikasyon aynı cümlede ve
  yanıtta ürünün TL fiyatı yoksa fiyat cümlesi üretir; fiyat zaten
  söylenmişse / modifikasyon yoksa / bu turda ürün eklenmemişse None.
- Delta akışı: main loop'taki detect_order() öncesi/sonrası sepet farkı —
  S34 (ürün önceki turda alınmış, yalnızca not değişiyor) turlarında delta
  boş kalır, enjeksiyon tetiklenmez ve sepet İKİLENMEZ.

Gerçek menu.yaml kullanılır (robot_waiter_ai/data/menu.yaml).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from demo_usb import (  # noqa: E402
    OrderTracker,
    _has_modification_request,
    _modification_price_addition,
)

pytestmark = pytest.mark.unit


def _delta_after(tracker: OrderTracker, text: str) -> list[tuple[str, int, int]]:
    """Main loop'taki _added_this_turn hesabının birebir eşdeğeri."""
    before = {name: qty for name, _p, qty in tracker.items}
    tracker.detect_order(text)
    return [
        (name, price, qty - before.get(name, 0))
        for name, price, qty in tracker.items
        if qty > before.get(name, 0)
    ]


# --- _has_modification_request: sinyal tespiti ---

@pytest.mark.parametrize("cumle", [
    "Bir şalgam suyu alayım, acılı olsun.",
    "Et döner soğansız olsun.",
    "Köfte az pişmiş istiyorum.",
    "Bir limonata alayım, şekersiz lütfen.",
    "Ayran tuzsuz olabilir mi?",
    "İki köfte alalım, acısız olsun.",
])
def test_modifikasyon_sinyali_tespit_edilir(cumle):
    assert _has_modification_request(cumle) is True


@pytest.mark.parametrize("cumle", [
    "Bir köfte alayım.",
    "Menüde neler var?",
    "Hesabı alabilir miyim?",
    "İki tane ayran istiyorum.",
])
def test_modifikasyonsuz_cumleler(cumle):
    assert _has_modification_request(cumle) is False


def test_olsun_kelime_siniri():
    """'olsun' kelime sınırıyla aranır — 'dolsun' gibi içeren kelimeler değil."""
    assert _has_modification_request("Bardak dolsun.") is False


# --- _modification_price_addition: enjeksiyon kararı ---

_S33_CUMLE = "Bir şalgam suyu alayım, acılı olsun."
_S33_DELTA = [("Şalgam Suyu", 50, 1)]


def test_fiyatsiz_yanita_enjekte_edilir():
    """V01 çekirdek senaryosu: onay yanıtında TL yok → fiyat cümlesi üretilir."""
    addition = _modification_price_addition(
        _S33_CUMLE, "Tabii, acılı olarak not aldım. Başka bir şey alır mısınız?",
        _S33_DELTA)
    assert addition == "Şalgam Suyu 50 TL."


def test_fiyat_zaten_soylendiyse_none():
    addition = _modification_price_addition(
        _S33_CUMLE, "Elbette, Şalgam Suyu 50 TL, acılı not aldım.", _S33_DELTA)
    assert addition is None


def test_satir_toplami_soylendiyse_none():
    """Adet >1: yanıtta satır toplamı (2×50=100) geçiyorsa tekrar edilmez."""
    addition = _modification_price_addition(
        "İki şalgam alayım, acılı olsun.",
        "Tabii, iki Şalgam Suyu 100 TL, acılı not aldım.",
        [("Şalgam Suyu", 50, 2)])
    assert addition is None


def test_kelime_siniri_yanlis_eslesme_yok():
    """Yanıttaki '150' rakamı, ürünün 50 TL fiyatı sayılMAmalı."""
    addition = _modification_price_addition(
        _S33_CUMLE, "Tabii, toplam 150 TL oldu, acılı not aldım.", _S33_DELTA)
    assert addition == "Şalgam Suyu 50 TL."


def test_modifikasyon_yoksa_none():
    addition = _modification_price_addition(
        "Bir şalgam suyu alayım.", "Elbette efendim, not aldım.", _S33_DELTA)
    assert addition is None


def test_delta_bossa_none():
    """Bu turda ürün eklenmediyse (S34 dahil) enjeksiyon yok."""
    addition = _modification_price_addition(
        "Et döner soğansız olsun.", "Tabii, soğansız güncelledim.", [])
    assert addition is None


def test_coklu_urun_ve_adet():
    addition = _modification_price_addition(
        "İki şalgam ve bir ayran alayım, acılı olsun.",
        "Tabii, not aldım.",
        [("Şalgam Suyu", 50, 2), ("Yayık Ayran", 45, 1)])
    assert addition == "2 Şalgam Suyu 100 TL, Yayık Ayran 45 TL."


def test_kismi_fiyat_yalnizca_eksik_urun():
    """Yanıt bir ürünün fiyatını içeriyorsa yalnızca eksik olan eklenir."""
    addition = _modification_price_addition(
        "Bir şalgam ve bir ayran alayım, acılı olsun.",
        "Şalgam Suyu 50 TL, acılı not aldım.",
        [("Şalgam Suyu", 50, 1), ("Yayık Ayran", 45, 1)])
    assert addition == "Yayık Ayran 45 TL."


# --- Delta akışı: main loop entegrasyonunun saf eşdeğeri ---

def test_s33_delta_urun_ekler():
    """S33: sipariş + modifikasyon aynı cümlede → delta dolu, sepet doğru."""
    ot = OrderTracker()
    delta = _delta_after(ot, _S33_CUMLE)
    assert delta == [("Şalgam Suyu", 50, 1)]
    assert ot.total == 50


def test_s34_delta_bos_sepet_ikilenmez():
    """S34: ürün önceki turda alınmış, 'soğansız olsun' yalnızca not —
    delta boş kalmalı (görev #21: 'olsun' ekleme değil), sepet ikilenmemeli."""
    ot = OrderTracker()
    _delta_after(ot, "Bir et döner alayım.")
    delta = _delta_after(ot, "Et döner soğansız olsun.")
    assert delta == []
    assert ot.items == [("Et Döner", 280, 1)]
    assert _modification_price_addition(
        "Et döner soğansız olsun.", "Tabii, soğansız güncelledim.", delta) is None


def test_adet_artisinda_delta_yalnizca_fark():
    """Sepette 1 ayran varken 'bir ayran daha olsun' → delta yalnızca +1."""
    ot = OrderTracker()
    _delta_after(ot, "Bir ayran alayım.")
    delta = _delta_after(ot, "Bir ayran daha olsun.")
    assert delta == [("Yayık Ayran", 45, 1)]
    assert ot.items == [("Yayık Ayran", 45, 2)]
