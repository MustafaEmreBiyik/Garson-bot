#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v4 — A2: Karmaşık/Adetli Sipariş + S12 koşulsuz özet
Hedef: 150 yeni, kural-uyumlu örnek.
Çalıştır: python scripts/gen_karmasik.py

Tasarım notu (S12 / audit çatışması çözümü):
  SENARYO_PLANI_FAZ1.md Karar 2 — onay öncesi her zaman özet+toplam.
  audit_dataset.py'nin check_tl_in_wrong_context kuralı TL'nin yalnızca
  fiyat/sipariş/hesap bağlamında geçmesine izin verir. Bu yüzden özet+toplam
  turu HER ZAMAN, son ürünün de anıldığı bir kullanıcı mesajına yanıt olarak
  üretilir (ör. "Bir de ayran, başka istemiyorum." — menü ürünü adı geçtiği
  için _is_valid_price_context True döner). "Onaylıyor musunuz?" zaten
  _BASIT_EQUIVALENTS listesinde olduğundan "başka" kuralını da karşılar.
  audit_dataset.py'ye dokunulmadı.
"""
import itertools
import json
import random
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

_rng = random.Random(72)

SYSTEM = json.loads(
    open(
        "robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl",
        encoding="utf-8",
    ).readline()
)["messages"][0]["content"]

MENU = {
    "Mercimek Çorbası":        ("mercimek çorbası", 85),
    "Kremalı Mantar Çorbası":  ("mantar çorbası",   95),
    "Izgara Köfte":            ("ızgara köfte",     240),
    "Et Döner":                ("et döner",         280),
    "Izgara Tavuk Salata":     ("tavuk salata",     210),
    "Fırın Sütlaç":            ("fırın sütlaç",     100),
    "Künefe":                  ("künefe",           140),
    "Yayık Ayran":             ("ayran",            45),
    "Limonata":                ("limonata",         70),
    "Şalgam Suyu":             ("şalgam suyu",      50),
}
ITEMS = list(MENU.keys())
SOUPS  = ["Mercimek Çorbası", "Kremalı Mantar Çorbası"]
MAINS  = ["Izgara Köfte", "Et Döner", "Izgara Tavuk Salata"]
OTHERS = ["Fırın Sütlaç", "Künefe", "Yayık Ayran", "Limonata", "Şalgam Suyu"]

QUANT_WORD = {1: "bir", 2: "iki", 3: "üç", 4: "dört"}

GREET_PAIRS = [
    ("Merhaba.",            "Hoş geldiniz, çorba, ana yemek, tatlı ve içeceklerimizden ne arzu edersiniz?"),
    ("Selam.",              "Merhaba, çorba, ana yemek, tatlı ve içecek seçeneklerinden ne istersiniz?"),
    ("İyi günler.",         "Buyurun, çorba, ana yemek, tatlı ve içecek arasından ne alırsınız?"),
    ("İyi akşamlar.",       "Hoş geldiniz, çorba, ana yemek, tatlı ve içecek sunuyoruz, ne tercih edersiniz?"),
    ("Günaydın.",           "Günaydın, çorba, ana yemek, tatlı ve içeceklerimizden ne seçersiniz?"),
    ("Buyurun.",            "Buyurun efendim, çorba, ana yemek, tatlı ve içecekten ne alayım?"),
    ("Merhaba, ne var?",    "Çorba, ana yemek, tatlı ve içecek seçeneklerimiz mevcut, ne istersiniz?"),
    ("Selam, menü nedir?",  "Menümüzde çorba, ana yemek, tatlı ve içecek var, ne alırsınız?"),
    ("Merhaba, sipariş vermek istiyorum.", "Hoş geldiniz, çorba, ana yemek, tatlı ve içeceklerimizden ne arzu edersiniz?"),
    ("İyi günler, bir şeyler ısmarlamak istiyorum.", "Buyurun, çorba, ana yemek, tatlı ve içecek arasından ne alırsınız?"),
]

BASKA_FORMS = [
    "Başka bir şey alır mısınız?",
    "Başka ne arzu edersiniz?",
    "Başka ne alırsınız?",
    "Başka bir şey ister misiniz?",
    "Başka bir şey daha alır mısınız?",
    "Başka bir isteğiniz var mı?",
    "Eklemek istediğiniz bir şey var mı?",
    "Ekleyeceğimiz bir şey var mı?",
    "İlaveten bir arzunuz olur mu?",
    "Başka arzunuz var mı?",
]

POSITIVE_WORDS = ["Elbette", "Tabii ki", "Tabii efendim", "Memnuniyetle", "Harika seçim"]

SUMMARY_PREFIXES = ["Elbette, Siparişiniz:", "Tabii, Siparişiniz:", "Peki, Siparişiniz:"]

EVET_FORMS = ["Evet.", "Evet, onaylıyorum.", "Evet, doğru."]

AFIYET_FORMS = [
    "Afiyet olsun!",
    "Harika, afiyet olsun!",
    "Afiyet olsun, iyi günler!",
    "Afiyet olsun, tekrar bekleriz!",
]

# Tur-tur ekleme kapanışı — doğal, birleşik cümleler (menü ürünü + kapanış aynı cümlede)
CLOSE_ADD_TEMPLATES = [
    "Bir de {short}, başka istemiyorum.",
    "Ayrıca bir {short}, bu kadar yeterli.",
    "Son olarak bir {short}, yeter artık.",
    "Bir {short} daha, başka bir şey istemem.",
    "Bir de {short} alayım, o kadar yeter.",
    "Bir {short} daha olsun, teşekkürler bu kadar.",
]


def cap(s: str) -> str:
    return s[0].upper() + s[1:]


def fmt_items_list(items_qty):
    parts = []
    for item_key, qty in items_qty:
        parts.append(f"{qty} {item_key}" if qty > 1 else item_key)
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " ve " + parts[-1]


def total_of(items_qty):
    return sum(MENU[k][1] * q for k, q in items_qty)


def user_order_sentence(items_qty, verb_idx=0):
    parts = []
    for item_key, qty in items_qty:
        short = MENU[item_key][0]
        parts.append(f"{QUANT_WORD.get(qty, str(qty))} {short}")
    body = ", ".join(parts[:-1]) + (" ve " if len(parts) > 1 else "") + parts[-1]
    verbs = ["alayım.", "istiyorum.", "alabilir miyim?"]
    s = f"{body} {verbs[verb_idx % len(verbs)]}"
    return cap(s)


def summary_turn(items_qty, idx):
    prefix = SUMMARY_PREFIXES[idx % len(SUMMARY_PREFIXES)]
    total = total_of(items_qty)
    return f"{prefix} {fmt_items_list(items_qty)}. Toplam {total} TL. Onaylıyor musunuz?"


records = []

# ── Bölüm A: Adetli sipariş — tek mesajda çoklu ürün + adet (55) ────────────
PAIRS = list(itertools.combinations(ITEMS, 2))  # 45 çift
QTY_PATTERNS = [(2, 1), (1, 2), (3, 1), (1, 3), (2, 2), (2, 3), (3, 2)]

for idx in range(55):
    i1, i2 = PAIRS[idx % len(PAIRS)]
    q1, q2 = QTY_PATTERNS[idx % len(QTY_PATTERNS)]
    items_qty = [(i1, q1), (i2, q2)]
    greet = GREET_PAIRS[idx % len(GREET_PAIRS)]
    user_order = user_order_sentence(items_qty, verb_idx=idx)
    bot_summary = summary_turn(items_qty, idx)
    evet = EVET_FORMS[idx % len(EVET_FORMS)]
    afiyet = AFIYET_FORMS[idx % len(AFIYET_FORMS)]

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": user_order},
            {"role": "assistant", "content": bot_summary},
            {"role": "user",      "content": evet},
            {"role": "assistant", "content": afiyet},
        ]
    })

# ── Bölüm B: Karma kategori — çorba + ana yemek + diğer, tek mesajda (55) ───
TRIPLETS = [(s, m, o) for s in SOUPS for m in MAINS for o in OTHERS]  # 30
QTY3_PATTERNS = [(1, 1, 1), (2, 1, 1), (1, 2, 1), (1, 1, 2)]

for idx in range(55):
    i1, i2, i3 = TRIPLETS[idx % len(TRIPLETS)]
    q1, q2, q3 = QTY3_PATTERNS[idx % len(QTY3_PATTERNS)]
    items_qty = [(i1, q1), (i2, q2), (i3, q3)]
    greet = GREET_PAIRS[(idx + 3) % len(GREET_PAIRS)]
    user_order = user_order_sentence(items_qty, verb_idx=idx + 1)
    bot_summary = summary_turn(items_qty, idx + 1)
    evet = EVET_FORMS[(idx + 1) % len(EVET_FORMS)]
    afiyet = AFIYET_FORMS[(idx + 1) % len(AFIYET_FORMS)]

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": user_order},
            {"role": "assistant", "content": bot_summary},
            {"role": "user",      "content": evet},
            {"role": "assistant", "content": afiyet},
        ]
    })

# ── Bölüm C: Tur tur ekleme — çok turlu, doğal kapanış (40) ─────────────────
# C1: 2 adımlı zincir (20) — item1 sipariş, item2 + kapanış birleşik cümlede
TWO_STEP_PAIRS = PAIRS  # 45 çift, ilk 20'si kullanılacak

for idx in range(20):
    i1, i2 = TWO_STEP_PAIRS[idx]
    items_qty_final = [(i1, 1), (i2, 1)]
    greet = GREET_PAIRS[idx % len(GREET_PAIRS)]

    order1 = user_order_sentence([(i1, 1)], verb_idx=idx)
    pos1 = POSITIVE_WORDS[idx % len(POSITIVE_WORDS)]
    baska1 = BASKA_FORMS[idx % len(BASKA_FORMS)]
    confirm1 = f"{pos1}, {i1} {MENU[i1][1]} TL. {baska1}"

    close_tmpl = CLOSE_ADD_TEMPLATES[idx % len(CLOSE_ADD_TEMPLATES)]
    order2_close = cap(close_tmpl.format(short=MENU[i2][0]))
    bot_summary = summary_turn(items_qty_final, idx + 2)

    evet = EVET_FORMS[idx % len(EVET_FORMS)]
    afiyet = AFIYET_FORMS[idx % len(AFIYET_FORMS)]

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": order1},
            {"role": "assistant", "content": confirm1},
            {"role": "user",      "content": order2_close},
            {"role": "assistant", "content": bot_summary},
            {"role": "user",      "content": evet},
            {"role": "assistant", "content": afiyet},
        ]
    })

# C2: 3 adımlı zincir (20) — item1, item2 sipariş, item3 + kapanış birleşik cümlede
TRIPLE_COMBOS = list(itertools.combinations(ITEMS, 3))  # 120

for idx in range(20):
    i1, i2, i3 = TRIPLE_COMBOS[idx * 5]  # geniş aralıkla dağıt, tekrarı azalt
    items_qty_final = [(i1, 1), (i2, 1), (i3, 1)]
    greet = GREET_PAIRS[(idx + 5) % len(GREET_PAIRS)]

    order1 = user_order_sentence([(i1, 1)], verb_idx=idx + 1)
    pos1 = POSITIVE_WORDS[(idx + 1) % len(POSITIVE_WORDS)]
    baska1 = BASKA_FORMS[(idx + 1) % len(BASKA_FORMS)]
    confirm1 = f"{pos1}, {i1} {MENU[i1][1]} TL. {baska1}"

    order2 = user_order_sentence([(i2, 1)], verb_idx=idx + 2)
    pos2 = POSITIVE_WORDS[(idx + 2) % len(POSITIVE_WORDS)]
    baska2 = BASKA_FORMS[(idx + 2) % len(BASKA_FORMS)]
    confirm2 = f"{pos2}, {i2} {MENU[i2][1]} TL. {baska2}"

    close_tmpl = CLOSE_ADD_TEMPLATES[(idx + 3) % len(CLOSE_ADD_TEMPLATES)]
    order3_close = cap(close_tmpl.format(short=MENU[i3][0]))
    bot_summary = summary_turn(items_qty_final, idx + 3)

    evet = EVET_FORMS[(idx + 2) % len(EVET_FORMS)]
    afiyet = AFIYET_FORMS[(idx + 2) % len(AFIYET_FORMS)]

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": order1},
            {"role": "assistant", "content": confirm1},
            {"role": "user",      "content": order2},
            {"role": "assistant", "content": confirm2},
            {"role": "user",      "content": order3_close},
            {"role": "assistant", "content": bot_summary},
            {"role": "user",      "content": evet},
            {"role": "assistant", "content": afiyet},
        ]
    })

print(f"Toplam: {len(records)} kayıt (A=55, B=55, C=40)")

_rng.shuffle(records)

out_path = Path("robot_waiter_ai/datasets/processed/wbot_v4_karmasik.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"✓ {len(records)} kayıt → {out_path}")
