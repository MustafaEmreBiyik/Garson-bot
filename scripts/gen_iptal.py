#!/usr/bin/env python3
"""gen_iptal.py — 100 Sipariş iptali / değişiklik örneği üretir.

Bölümler:
  A (40): Saf iptal — 8 çift × 5 iptal formu
          CANCEL_TRIGGER → _is_specific_order_turn=False → bot başka gerekmez
  B (30): Takas — 15 çift × 2 stil ("X yerine Y alayım")
          SWAP_TRIGGER, CANCEL_TRIGGER yok → _is_specific_order_turn=True → bot başka zorunlu
  C (20): İptal + aynı turda yeniden sipariş — 10 çift × 2 stil
          CANCEL_TRIGGER var → _is_specific_order_turn=False → bot başka gerekmez
  D (10): Hızlı aklını değiştirme
          CANCEL + ORDER aynı mesajda, kısa yapı
"""
import json
from pathlib import Path

OUT = Path("robot_waiter_ai/datasets/processed/wbot_v3_iptal.jsonl")

MENU = {
    "Mercimek Çorbası":       85,
    "Mantar Çorbası":         95,
    "Izgara Köfte":          240,
    "Et Döner":              280,
    "Izgara Tavuk Salatası": 210,
    "Fırın Sütlaç":          100,
    "Künefe":                140,
    "Ayran":                  45,
    "Limonata":               70,
    "Şalgam Suyu":            50,
}

SYSTEM = "Sen W-BOT'sun, Türkçe konuşan bir restoran garson robotusun."
GREET_BOT = (
    "Hoş geldiniz! Menümüzde çorba, ana yemek, tatlı ve içecek "
    "çeşitlerimiz mevcuttur. Ne arzedersiniz?"
)

GREETINGS = [
    "Merhaba.", "Günaydın.", "İyi günler.", "İyi akşamlar.",
    "Merhaba, oturabilir miyiz?", "Selam.", "Buyurun.",
    "Merhaba, masaya oturuyoruz.",
]

CONFIRM_FMTS = [
    lambda i, p: f"Anlaşıldı, {i} {p} TL. Başka bir şey alır mısınız?",
    lambda i, p: f"Tamam efendim, {i} {p} TL. Başka arzunuz var mı?",
    lambda i, p: f"Peki efendim, {i} {p} TL. Eklemek istediğiniz bir şey var mı?",
    lambda i, p: f"Anlaşıldı, {i} {p} TL. Başka ne arzu edersiniz?",
    lambda i, p: f"Tabii efendim, {i} {p} TL. Başka bir şey ister misiniz?",
]

# CANCEL_TRIGGER içeren iptal formları: istemiyorum / iptal / çıkar / kaldır / geri al
CANCEL_USER_FMTS = [
    lambda i: f"{i} istemiyorum aslında.",
    lambda i: f"{i} iptal lütfen.",
    lambda i: f"{i} çıkar lütfen.",
    lambda i: f"{i} kaldırır mısınız?",
    lambda i: f"{i} geri alın, istemiyorum.",
]

# Saf iptal yanıtları — başka gerekmez (opsiyonel eklendi bazılarına)
CANCEL_ACKS = [
    lambda i: f"Anlaşıldı, {i} siparişi iptal edildi.",
    lambda i: f"Tamam efendim, {i} siparişinizi kaldırdım.",
    lambda i: f"Peki efendim, {i} iptal edildi.",
    lambda i: f"Anlaşıldı, {i} siparişten çıkarıldı.",
    lambda i: f"Tabii efendim, {i} siparişini iptal ediyorum.",
]

NO_MORE = [
    "Hayır, teşekkürler.", "Yeterli, teşekkürler.", "Bu kadar yeterli.",
    "Şimdilik bu kadar.", "Hayır, hepsi bu.", "Bu kadardı.",
]

BILL_REQS = [
    "Hesabı alabilir miyim?", "Hesap lütfen.", "Ödeyeyim.",
    "Ödemek istiyorum.", "Toplam ne kadar?", "Çek gelsin lütfen.",
    "Adisyonu getirir misiniz?", "Hesabımızı alabilir miyiz?",
    "Hesabı kapatmak istiyorum.", "Kapatalım lütfen.",
]

CLOSINGS = [
    "Afiyet olsun!",
    "Afiyet olsun, tekrar bekleriz.",
    "İyi günler dileriz.",
    "Afiyet olsun, görüşürüz.",
    "Tekrar bekleriz, iyi günler.",
    "Uğradığınız için teşekkürler, iyi günler.",
    "Afiyet olsun, sağlıklı günler dileriz.",
]

ACK_ORDER = [
    "Anlaşıldı, siparişinizi iletiyorum.",
    "Tamam efendim, siparişiniz alındı.",
    "Peki efendim, siparişinizi bildiriyorum.",
    "Anlaşıldı.",
    "Peki, siparişinizi hazırlıyorum.",
]

BASIT = [
    "Başka bir şey alır mısınız?",
    "Başka arzunuz var mı?",
    "Başka bir şey ister misiniz?",
    "Başka bir isteğiniz var mı?",
    "Eklemek istediğiniz bir şey var mı?",
    "İlaveten bir arzunuz olur mu?",
    "Ekleyeceğimiz bir şey var mı?",
]


def _bill(total, idx):
    return f"Toplam {total} TL. {CLOSINGS[idx % len(CLOSINGS)]}"


def s():  return {"role": "system",    "content": SYSTEM}
def u(t): return {"role": "user",      "content": t}
def a(t): return {"role": "assistant", "content": t}


records = []

# ══════════════════════════════════════════════════════════════
# Bölüm A: Saf iptal (40 örnek)
# Sipariş A → onay+başka → sipariş B → onay+başka → no_more → ack
#   → iptal A → iptal_ack → hesap → toplam_B
# 8 çift × 5 iptal formu
# ══════════════════════════════════════════════════════════════

PAIRS_A = [
    ("Mercimek Çorbası",      "Izgara Köfte"),
    ("Mantar Çorbası",        "Et Döner"),
    ("Izgara Köfte",          "Ayran"),
    ("Et Döner",              "Limonata"),
    ("Izgara Tavuk Salatası", "Şalgam Suyu"),
    ("Fırın Sütlaç",          "Mantar Çorbası"),
    ("Künefe",                "Ayran"),
    ("Mercimek Çorbası",      "Fırın Sütlaç"),
]

for c_idx in range(5):
    for p_idx, (ia, ib) in enumerate(PAIRS_A):
        n   = c_idx * 8 + p_idx
        pa  = MENU[ia];  pb = MENU[ib]
        cf  = CONFIRM_FMTS[n % 5]
        cf2 = CONFIRM_FMTS[(n + 1) % 5]
        records.append({"messages": [
            s(),
            u(GREETINGS[n % 8]),
            a(GREET_BOT),
            u(f"{ia} alayım."),
            a(cf(ia, pa)),
            u(f"Bir de {ib} istiyorum."),
            a(cf2(ib, pb)),
            u(NO_MORE[n % 6]),
            a(ACK_ORDER[n % 5]),
            u(CANCEL_USER_FMTS[c_idx](ia)),
            a(CANCEL_ACKS[n % 5](ia)),
            u(BILL_REQS[n % 10]),
            a(_bill(pb, n)),
        ]})

# ══════════════════════════════════════════════════════════════
# Bölüm B: Takas — "X yerine Y alayım" (30 örnek)
# "yerine" = SWAP_TRIGGER, CANCEL_TRIGGER yok → _is_specific_order_turn=True → başka zorunlu
# Sipariş A → onay+başka → no_more → ack → takas A→B → onay_B+başka → no_more → hesap → toplam_B
# 15 çift × 2 stil
# ══════════════════════════════════════════════════════════════

SWAP_PAIRS = [
    ("Mercimek Çorbası",      "Mantar Çorbası"),
    ("Mantar Çorbası",        "Mercimek Çorbası"),
    ("Izgara Köfte",          "Et Döner"),
    ("Et Döner",              "Izgara Köfte"),
    ("Izgara Tavuk Salatası", "Izgara Köfte"),
    ("Fırın Sütlaç",          "Künefe"),
    ("Künefe",                "Fırın Sütlaç"),
    ("Ayran",                 "Limonata"),
    ("Limonata",              "Şalgam Suyu"),
    ("Şalgam Suyu",           "Ayran"),
    ("Izgara Köfte",          "Izgara Tavuk Salatası"),
    ("Et Döner",              "Izgara Tavuk Salatası"),
    ("Mercimek Çorbası",      "Izgara Köfte"),
    ("Ayran",                 "Şalgam Suyu"),
    ("Fırın Sütlaç",          "Limonata"),
]

# Her iki stilde de ORDER_TRIGGER + food token var, CANCEL_TRIGGER yok → başka zorunlu
SWAP_USER = [
    lambda ia, ib: f"{ia} yerine {ib} alayım.",
    lambda ia, ib: f"{ia} yerine {ib} istiyorum.",
]

SWAP_BOT = [
    lambda ia, ib, pb, bk: f"Anlaşıldı, {ia} yerine {ib} {pb} TL. {bk}",
    lambda ia, ib, pb, bk: f"Tamam efendim, {ib} {pb} TL ile değiştirdik. {bk}",
]

for s_idx in range(2):
    for p_idx, (ia, ib) in enumerate(SWAP_PAIRS):
        n  = s_idx * 15 + p_idx
        pa = MENU[ia];  pb = MENU[ib]
        cf = CONFIRM_FMTS[n % 5]
        bk = BASIT[n % 7]
        records.append({"messages": [
            s(),
            u(GREETINGS[n % 8]),
            a(GREET_BOT),
            u(f"{ia} alayım."),
            a(cf(ia, pa)),
            u(NO_MORE[n % 6]),
            a(ACK_ORDER[n % 5]),
            u(SWAP_USER[s_idx](ia, ib)),
            a(SWAP_BOT[s_idx](ia, ib, pb, bk)),
            u(NO_MORE[(n + 1) % 6]),
            a(ACK_ORDER[(n + 1) % 5]),
            u(BILL_REQS[n % 10]),
            a(_bill(pb, n)),
        ]})

# ══════════════════════════════════════════════════════════════
# Bölüm C: İptal + aynı turda yeniden sipariş (20 örnek)
# CANCEL_TRIGGER var → _is_specific_order_turn=False → başka audit check yok
# Sipariş A → onay+başka → no_more → ack → iptal_A+yeniden_B → ack_C → hesap → toplam_B
# 10 çift × 2 stil
# ══════════════════════════════════════════════════════════════

CANCEL_REORDER_PAIRS = [
    ("Mercimek Çorbası",      "Izgara Tavuk Salatası"),
    ("Mantar Çorbası",        "Künefe"),
    ("Izgara Köfte",          "Mercimek Çorbası"),
    ("Et Döner",              "Mantar Çorbası"),
    ("Izgara Tavuk Salatası", "Fırın Sütlaç"),
    ("Fırın Sütlaç",          "Limonata"),
    ("Künefe",                "Şalgam Suyu"),
    ("Ayran",                 "Izgara Köfte"),
    ("Limonata",              "Et Döner"),
    ("Şalgam Suyu",           "Künefe"),
]

# Her iki stilde de CANCEL_TRIGGER var → _is_specific_order_turn=False → başka gerekmez
CANCEL_REORDER_USER = [
    lambda ia, ib: f"{ia} iptal lütfen, {ib} alayım.",
    lambda ia, ib: f"{ia} istemiyorum, {ib} istiyorum.",
]

# TL geçerli: has_cancel=True AND has_order=True → _is_valid_price_context=True
CANCEL_REORDER_BOT = [
    lambda ia, ib, pb: f"Anlaşıldı, {ia} iptal edildi, {ib} {pb} TL siparişinize eklendi.",
    lambda ia, ib, pb: f"Tamam efendim, {ia} kaldırıldı, {ib} {pb} TL eklendi.",
]

for cr_idx in range(2):
    for p_idx, (ia, ib) in enumerate(CANCEL_REORDER_PAIRS):
        n  = cr_idx * 10 + p_idx
        pa = MENU[ia];  pb = MENU[ib]
        cf = CONFIRM_FMTS[n % 5]
        records.append({"messages": [
            s(),
            u(GREETINGS[n % 8]),
            a(GREET_BOT),
            u(f"{ia} alayım."),
            a(cf(ia, pa)),
            u(NO_MORE[n % 6]),
            a(ACK_ORDER[n % 5]),
            u(CANCEL_REORDER_USER[cr_idx](ia, ib)),
            a(CANCEL_REORDER_BOT[cr_idx](ia, ib, pb)),
            u(BILL_REQS[n % 10]),
            a(_bill(pb, n)),
        ]})

# ══════════════════════════════════════════════════════════════
# Bölüm D: Hızlı aklını değiştirme (10 örnek)
# Sipariş A → onay+başka → "Dur, A istemiyorum, B alayım" → ack → hesap → toplam_B
# Tüm kullanıcı mesajları: CANCEL_TRIGGER + ORDER_TRIGGER aynı mesajda
# ══════════════════════════════════════════════════════════════

PAIRS_D = [
    ("Mercimek Çorbası",      "Izgara Tavuk Salatası"),
    ("Mantar Çorbası",        "Künefe"),
    ("Izgara Köfte",          "Mercimek Çorbası"),
    ("Et Döner",              "Mantar Çorbası"),
    ("Izgara Tavuk Salatası", "Fırın Sütlaç"),
    ("Fırın Sütlaç",          "Limonata"),
    ("Künefe",                "Şalgam Suyu"),
    ("Ayran",                 "Izgara Köfte"),
    ("Limonata",              "Et Döner"),
    ("Şalgam Suyu",           "Künefe"),
]

# Tümünde CANCEL_TRIGGER mevcut → _is_specific_order_turn=False → başka gerekmez
MIND_CHANGE_USER = [
    lambda ia, ib: f"Dur, {ia} istemiyorum, {ib} alayım.",
    lambda ia, ib: f"Aslında {ia} iptal, {ib} istiyorum.",
    lambda ia, ib: f"Bekleyin, {ia} geri alın, {ib} alayım.",
    lambda ia, ib: f"{ia} istemiyorum, {ib} alabilir miyim?",
    lambda ia, ib: f"{ia} kaldırın, {ib} istiyorum.",
]

# TL geçerli: has_cancel=True AND _contains_any(ORDER_TRIGGERS)=True → _is_valid_price_context=True
MIND_CHANGE_BOT = [
    lambda ia, ib, pb: f"Anlaşıldı, {ia} iptal, {ib} {pb} TL siparişinize eklendi.",
    lambda ia, ib, pb: f"Tamam efendim, {ia} yerine {ib} {pb} TL.",
    lambda ia, ib, pb: f"Peki efendim, {ia} kaldırıldı, {ib} {pb} TL eklendi.",
    lambda ia, ib, pb: f"Anlaşıldı, {ia} çıkarıldı, {ib} {pb} TL.",
    lambda ia, ib, pb: f"Tabii efendim, {ia} iptal, {ib} {pb} TL ekliyorum.",
]

for p_idx, (ia, ib) in enumerate(PAIRS_D):
    n  = p_idx
    pa = MENU[ia];  pb = MENU[ib]
    cf = CONFIRM_FMTS[n % 5]
    records.append({"messages": [
        s(),
        u(GREETINGS[n % 8]),
        a(GREET_BOT),
        u(f"{ia} alayım."),
        a(cf(ia, pa)),
        u(MIND_CHANGE_USER[n % 5](ia, ib)),
        a(MIND_CHANGE_BOT[n % 5](ia, ib, pb)),
        u(BILL_REQS[n % 10]),
        a(_bill(pb, n)),
    ]})

# ── Çıktı ──────────────────────────────────────────────────────────────────────

assert len(records) == 100, f"Beklenen 100, üretilen {len(records)}"

OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"Yazıldı: {OUT}  ({len(records)} kayıt)")
