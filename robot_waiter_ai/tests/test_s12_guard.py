"""S12/E24 runtime guard birim testleri (scripts/demo_usb.py, görev #22).

Guard'ın saf yapı taşları izole test edilir:
- _is_closing_signal(): yalnızca kapanış kalıbına bakar, ürün eşleşmesi yürütmez.
- _is_order_confirmation(): TUR 2 onay sınıflandırması.
- _closing_summary(): TUR 1 deterministik özet (özet + toplam + onay sorusu).
- Akış sırası: detect_order() ÖNCE → order_tracker.items güncel → özet doğru
  (ilk guard taslağındaki ürün-eşleşme mantık hatasının düzeltilmiş tasarımı).

Gerçek menu.yaml kullanılır (robot_waiter_ai/data/menu.yaml).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from demo_usb import (  # noqa: E402
    OrderTracker,
    _S12_CLOSING_REPLY,
    _closing_summary,
    _fast_path_reply,
    _is_closing_signal,
    _is_order_confirmation,
)

pytestmark = pytest.mark.unit


# --- _is_closing_signal: kapanış kalıbı tespiti ---

@pytest.mark.parametrize("cumle", [
    # gen_karmasik.py'nin 6 eğitilmiş ekle+kapat kalıbı
    "Bir de ayran, başka istemiyorum.",
    "Ayrıca bir ayran, bu kadar yeterli.",
    "Son olarak bir limonata, yeter artık.",
    "Bir ayran daha, başka bir şey istemem.",
    "Bir de sütlaç alayım, o kadar yeter.",
    "Bir künefe daha olsun, teşekkürler bu kadar.",
    # saf kapanışlar (ürün adı yok)
    "Hayır, başka istemiyorum, bu kadar.",
    "Başka bir şey istemiyorum.",
    "Hepsi bu.",
    "Teşekkürler, bu kadar.",
])
def test_kapanis_sinyali_tespit_edilir(cumle):
    assert _is_closing_signal(cumle) is True


@pytest.mark.parametrize("cumle", [
    "Köfteyi istemiyorum, iptal edin.",   # ürün iptali — kapanış DEĞİL
    "Ayran istemiyorum.",                 # öneri reddi — kapanış DEĞİL
    "Bir köfte alayım.",                  # sipariş
    "Menüde neler var?",                  # bilgi sorusu
    "Ne kadar tuttu?",                    # hesap ("bu kadar" ile karışmamalı)
])
def test_kapanis_olmayan_cumleler(cumle):
    assert _is_closing_signal(cumle) is False


# --- Saf veda + dolu sepet: TUR 1'e yönlenmeli, fast-path'e yutulmamalı ---

def test_saf_veda_dolu_sepette_tur1_tetikler():
    """Sepette köfte varken müşteri yalnızca 'Teşekkürler.' derse özet+onay
    duyulmadan oturum kapanmamalı: veda kapanış sinyali sayılır ve TUR 1
    koşulu (dolu sepet + kapanış) sağlanır."""
    ot = OrderTracker()
    ot.detect_order("Bir köfte alayım.")
    assert _fast_path_reply("Teşekkürler.") is not None      # veda fast-path'i yakalar...
    assert _is_closing_signal("Teşekkürler.") is True        # ...ama guard önce çalışır
    assert ot.items                                          # TUR 1 koşulu: sepet dolu
    ozet = _closing_summary(ot.items, ot.total)
    assert "1 Izgara Köfte" in ozet and "Toplam 240 TL" in ozet


def test_ekle_veda_ayran_eklenir_ve_tur1_tetikler():
    """'Bir de ayran, teşekkürler.' → ayran EKLENMELİ ve TUR 1 tetiklenmeli;
    cümle fast-path'e hiç düşmemeli (guard, fast-path'ten önce)."""
    ot = OrderTracker()
    ot.detect_order("Bir köfte alayım.")
    cumle = "Bir de ayran, teşekkürler."
    ot.detect_order(cumle)                                   # 1) ayran sepete girer
    assert {n for n, _, _ in ot.items} == {"Izgara Köfte", "Yayık Ayran"}
    assert _is_closing_signal(cumle) is True                 # 2) TUR 1'e yönlenir
    ozet = _closing_summary(ot.items, ot.total)
    assert "1 Yayık Ayran" in ozet and "Toplam 285 TL" in ozet


def test_veda_bos_sepette_tur1_kosulu_saglanmaz():
    """Sepet boşken veda normal fast-path'e düşmeli — TUR 1'in sepet-dolu
    koşulu guard'ı devre dışı bırakır, davranış değişmez."""
    ot = OrderTracker()
    assert _is_closing_signal("Teşekkürler, iyi günler.") is True
    assert not ot.items                                      # TUR 1 koşulu sağlanmaz


# --- _is_order_confirmation: TUR 2 onay sınıflandırması ---

@pytest.mark.parametrize("cumle", [
    "Evet",
    "Evet.",
    "Tamam",
    "Olur, tabii.",
    "Evet, onaylıyorum.",
    "Evet, başka istemiyorum.",  # kapanış kalıbı ret iması sayılmaz
])
def test_onay_kabul_edilir(cumle):
    assert _is_order_confirmation(cumle) is True


@pytest.mark.parametrize("cumle", [
    "Hayır",
    "Hayır, köfteyi çıkar.",
    "Olmaz, yanlış oldu.",
    "Evet ama köfte eksik.",          # ret iması → normal akış
    "Bir de ayran olsun o zaman.",    # fikir değişikliği → normal akış
    "Toplam ne kadardı?",             # soru → normal akış
    "",
])
def test_onay_disi_normal_akisa_duser(cumle):
    assert _is_order_confirmation(cumle) is False


# --- _closing_summary: TUR 1 deterministik özet ---

def test_tur1_ozet_toplam_onay_icerir():
    ot = OrderTracker()
    ot.detect_order("Bir mercimek çorbası istiyorum.")
    ot.detect_order("Bir de ayran, başka istemiyorum.")
    ozet = _closing_summary(ot.items, ot.total)
    assert "1 Mercimek Çorbası" in ozet
    assert "1 Yayık Ayran" in ozet          # ekle+kapat'la eklenen ürün özette VAR
    assert "Toplam 130 TL" in ozet
    assert ozet.rstrip().endswith("Onaylıyor musunuz?")


def test_tur1_miktar_dogru():
    ot = OrderTracker()
    ot.detect_order("İki ayran ve bir köfte alayım.")
    ozet = _closing_summary(ot.items, ot.total)
    assert "2 Yayık Ayran" in ozet
    assert "1 Izgara Köfte" in ozet
    assert "Toplam 330 TL" in ozet  # 2×45 + 240


# --- TUR 2 sabit yanıtı: toplamsız kapanış ---

def test_tur2_yaniti_toplamsiz():
    assert "TL" not in _S12_CLOSING_REPLY
    assert "afiyet olsun" in _S12_CLOSING_REPLY.lower()


# --- Akış sırası: detect_order() önce → özet güncel sepetten kurulur ---

def test_akis_sirasi_ekle_kapat_hedef_senaryo():
    """E24 hedef senaryosu: 'Bir de ayran, başka istemiyorum.' hem kapanış
    sinyalidir hem ayranı ekler — guard sıralaması (önce detect_order, sonra
    closing check) her ikisini de yakalamalı."""
    ot = OrderTracker()
    ot.detect_order("Bir mercimek çorbası istiyorum.")
    cumle = "Bir de ayran, başka istemiyorum."
    ot.detect_order(cumle)                      # 1) sepet güncellenir
    assert _is_closing_signal(cumle) is True    # 2) kapanış tespit edilir
    assert {n for n, _, _ in ot.items} == {"Mercimek Çorbası", "Yayık Ayran"}


def test_fast_path_kapanisi_yutardi():
    """Guard'ın fast-path'ten ÖNCE durmasının gerekçesi: 'Teşekkürler, bu
    kadar.' (≤5 kelime, sipariş fiili yok) veda fast-path'ine düşer — guard
    önce çalışmazsa dolu sepet hiç özetlenmeden oturum kapanır."""
    assert _fast_path_reply("Teşekkürler, bu kadar.") is not None  # fast-path yakalıyor
    assert _is_closing_signal("Teşekkürler, bu kadar.") is True    # guard da yakalıyor
