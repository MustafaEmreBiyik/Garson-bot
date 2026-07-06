"""OrderTracker.detect_order() birim testleri (scripts/demo_usb.py).

Ekle+kapat çakışması fix'inin kalıcı regresyon güvencesi:
- "Bir de ayran, başka istemiyorum." → kapanış kalıbındaki "istemiyorum"
  ürün iptali sayılmamalı, ayran sepete eklenmeli.
- gen_karmasik.py'nin 6 eğitilmiş ekle+kapat kalıbının tamamı ürün eklemeli.
- "Et Döner soğansız olsun." (modifikasyon, S34/V02) ürünü İKİLEMEMELİ.
- Gerçek iptal / takas / miktar / saf kapanış davranışları değişmemeli.

Gerçek menu.yaml kullanılır (robot_waiter_ai/data/menu.yaml).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from demo_usb import OrderTracker  # noqa: E402

pytestmark = pytest.mark.unit


def _cart_after(*turns: str) -> OrderTracker:
    tracker = OrderTracker()
    for turn in turns:
        tracker.detect_order(turn)
    return tracker


def _names(tracker: OrderTracker) -> set[str]:
    return {name for name, _, _ in tracker.items}


# --- Asıl bug senaryosu: ekle+kapat, cancel dalı çakışması ---

def test_ekle_kapat_baska_istemiyorum():
    """'Bir de ayran, başka istemiyorum.' → ayran EKLENMELİ (görev #21 bug'ı)."""
    t = _cart_after("Bir mercimek çorbası istiyorum.", "Bir de ayran, başka istemiyorum.")
    assert _names(t) == {"Mercimek Çorbası", "Yayık Ayran"}
    assert t.total == 130


# --- gen_karmasik.py'nin diğer 5 eğitilmiş ekle+kapat kalıbı ---

@pytest.mark.parametrize("kapat_cumlesi, beklenen_urun, beklenen_toplam", [
    ("Ayrıca bir ayran, bu kadar yeterli.", "Yayık Ayran", 285),
    ("Son olarak bir limonata, yeter artık.", "Limonata", 310),
    ("Bir de sütlaç alayım, o kadar yeter.", "Fırın Sütlaç", 340),
])
def test_ekle_kapat_kaliplari(kapat_cumlesi, beklenen_urun, beklenen_toplam):
    t = _cart_after("Bir köfte alayım.", kapat_cumlesi)
    assert _names(t) == {"Izgara Köfte", beklenen_urun}
    assert t.total == beklenen_toplam


def test_ekle_kapat_daha_mevcut_urun():
    """'Bir ayran daha, başka bir şey istemem.' → sepetteki ayran 2'ye çıkmalı."""
    t = _cart_after("Bir köfte ve bir ayran alayım.", "Bir ayran daha, başka bir şey istemem.")
    assert _names(t) == {"Izgara Köfte", "Yayık Ayran"}
    assert t.total == 330  # 240 + 2×45


def test_ekle_kapat_daha_olsun():
    """'Bir künefe daha olsun, teşekkürler bu kadar.' → künefe 2 adet olmalı."""
    t = _cart_after("Bir künefe istiyorum.", "Bir künefe daha olsun, teşekkürler bu kadar.")
    assert _names(t) == {"Künefe"}
    assert t.total == 280  # 2×140


# --- 'X olsun' modifikasyon çakışması (S34/V02): ürün İKİLENMEMELİ ---

def test_modifikasyon_olsun_ikilemez():
    """'Et Döner soğansız olsun.' bir modifikasyon isteğidir, ikinci döner değil."""
    t = _cart_after("Bir et döner alayım.", "Et Döner soğansız olsun.")
    assert _names(t) == {"Et Döner"}
    assert t.total == 280  # ÇİFT DEĞİL

def test_modifikasyon_olsun_varyant():
    t = _cart_after("Bir köfte alayım.", "Köfte az pişmiş olsun.")
    assert _names(t) == {"Izgara Köfte"}
    assert t.total == 240  # ÇİFT DEĞİL


# --- 'lütfen' + modifikasyon çakışması (görev #25 yan bulgu b): ikilenMEmeli ---

def test_lutfen_modifikasyon_ikilemez():
    """'Köfte acısız olsun lütfen.' → sepetteki köfte İKİLENMEMELİ (görev #25 b)."""
    t = _cart_after("Bir köfte alayım.", "Köfte acısız olsun lütfen.")
    assert _names(t) == {"Izgara Köfte"}
    assert t.total == 240  # ÇİFT DEĞİL


def test_lutfen_modifikasyon_varyant_ikilemez():
    """'Ayran buzsuz olsun lütfen.' → sepetteki ayran İKİLENMEMELİ."""
    t = _cart_after("Bir ayran istiyorum.", "Ayran buzsuz olsun lütfen.")
    assert _names(t) == {"Yayık Ayran"}
    assert t.total == 45  # ÇİFT DEĞİL


def test_lutfen_tek_tetikleyici_siparis():
    """'Bir köfte lütfen.' → köfte EKLENMELİ (regresyon: 'lütfen' geçerli tetikleyici)."""
    t = _cart_after("Bir köfte lütfen.")
    assert _names(t) == {"Izgara Köfte"}
    assert t.total == 240


def test_lutfen_modifikasyonlu_yeni_siparis_eklenir():
    """'Bir köfte lütfen, acısız olsun.' (boş sepet) → yeni sipariş EKLENMELİ."""
    t = _cart_after("Bir köfte lütfen, acısız olsun.")
    assert _names(t) == {"Izgara Köfte"}
    assert t.total == 240


def test_lutfen_daha_miktar_artisi_calisir():
    """'Bir ayran daha lütfen.' → ekleme kalıbı ('daha') miktarı artırmalı."""
    t = _cart_after("Bir ayran alayım.", "Bir ayran daha lütfen.")
    assert _names(t) == {"Yayık Ayran"}
    assert t.total == 90  # 2×45


# --- Regresyon: mevcut davranışlar bozulmamalı ---

def test_gercek_iptal():
    t = _cart_after("Bir ızgara köfte alayım.", "Bir de ayran istiyorum.",
                    "Köfteyi istemiyorum, iptal edin.")
    assert _names(t) == {"Yayık Ayran"}
    assert t.total == 45


def test_oneri_reddi_eklemez():
    """'Ayran istemiyorum.' (sepette yokken) → ayran EKLENMEMELİ."""
    t = _cart_after("Bir köfte alayım.", "Ayran istemiyorum.")
    assert _names(t) == {"Izgara Köfte"}
    assert t.total == 240


def test_saf_kapanis_sepeti_bozmaz():
    t = _cart_after("Bir sütlaç istiyorum.", "Hayır, başka istemiyorum, bu kadar.")
    assert _names(t) == {"Fırın Sütlaç"}
    assert t.total == 100


def test_takas():
    t = _cart_after("Bir köfte ve bir ayran alayım.", "Ayran yerine limonata olsun.")
    assert _names(t) == {"Izgara Köfte", "Limonata"}
    assert t.total == 310


def test_miktar():
    t = _cart_after("İki ayran istiyorum.")
    assert _names(t) == {"Yayık Ayran"}
    assert t.total == 90


def test_hepsini_iptal():
    t = _cart_after("İki ayran alayım.", "Bir köfte alayım.", "Ayranların hepsini iptal et.")
    assert _names(t) == {"Izgara Köfte"}
    assert t.total == 240


def test_siparis_disi_cumle():
    t = _cart_after("Menüde neler var?")
    assert _names(t) == set()
    assert t.total == 0
