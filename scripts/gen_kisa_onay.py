#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v4 — A4: Kısa Onay Senaryosu / S13
Hedef: 60 yeni, kural-uyumlu örnek.
Çalıştır: python scripts/gen_kisa_onay.py

Senaryo: Robot özet okuyup "Onaylıyor musunuz?" dedi, müşteri kısa onay
sözcüğüyle yanıtladı ("evet", "tamam", "doğru", "olur", "evet öyle") →
robot siparişi işleme aldığını belirtip kapanış yapar.
"onaylandı/kaydedildi" YASAK (E29/forbidden phrase kuralı).
"""
import itertools
import json
import random
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

_rng = random.Random(93)

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

SUMMARY_PREFIXES = ["Elbette, Siparişiniz:", "Tabii, Siparişiniz:", "Peki, Siparişiniz:"]

# S13 onay sözcükleri
CONFIRM_WORDS = ["Evet.", "Evet, öyle.", "Tamam.", "Doğru.", "Olur."]

# Kapanış — "onaylandı/kaydedildi" YASAK (forbidden phrase kuralı)
CLOSING_FORMS = [
    "Afiyet olsun!",
    "Hemen iletiyorum, afiyet olsun!",
    "Anlaşıldı, afiyet olsun!",
    "Hemen mutfağa iletiyorum, afiyet olsun!",
    "Tamamdır, afiyet olsun!",
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

# ── Bölüm A: Tek ürünlü sipariş → özet+onay → onay sözcüğü → kapanış (30) ───
for idx in range(30):
    item_key = ITEMS[idx % len(ITEMS)]
    qty = 1 if idx % 3 != 0 else 2
    items_qty = [(item_key, qty)]
    greet = GREET_PAIRS[idx % len(GREET_PAIRS)]
    user_order = user_order_sentence(items_qty, verb_idx=idx)
    bot_summary = summary_turn(items_qty, idx)
    confirm = CONFIRM_WORDS[idx % len(CONFIRM_WORDS)]
    closing = CLOSING_FORMS[idx % len(CLOSING_FORMS)]

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": user_order},
            {"role": "assistant", "content": bot_summary},
            {"role": "user",      "content": confirm},
            {"role": "assistant", "content": closing},
        ]
    })

# ── Bölüm B: Çoklu ürünlü sipariş (2-3) → özet+onay → onay sözcüğü → kapanış (30)
PAIRS = list(itertools.combinations(ITEMS, 2))       # 45
TRIPLES = list(itertools.combinations(ITEMS, 3))     # 120

for idx in range(30):
    if idx % 2 == 0:
        i1, i2 = PAIRS[idx % len(PAIRS)]
        items_qty = [(i1, 1), (i2, 1)]
    else:
        i1, i2, i3 = TRIPLES[(idx * 7) % len(TRIPLES)]
        items_qty = [(i1, 1), (i2, 1), (i3, 1)]

    greet = GREET_PAIRS[(idx + 4) % len(GREET_PAIRS)]
    user_order = user_order_sentence(items_qty, verb_idx=idx + 1)
    bot_summary = summary_turn(items_qty, idx + 1)
    confirm = CONFIRM_WORDS[(idx + 1) % len(CONFIRM_WORDS)]
    closing = CLOSING_FORMS[(idx + 1) % len(CLOSING_FORMS)]

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": user_order},
            {"role": "assistant", "content": bot_summary},
            {"role": "user",      "content": confirm},
            {"role": "assistant", "content": closing},
        ]
    })

print(f"Toplam: {len(records)} kayıt (A=30, B=30)")

_rng.shuffle(records)

out_path = Path("robot_waiter_ai/datasets/processed/wbot_v4_kisa_onay.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"✓ {len(records)} kayıt → {out_path}")
