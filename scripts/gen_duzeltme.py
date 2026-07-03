#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v4 — A5: Yanlış Anlama → Düzeltme / S26
Hedef: 30 yeni, kural-uyumlu örnek.
Çalıştır: python scripts/gen_duzeltme.py

Alt tipler (~10'ar):
  1. Ürün adı yanlış — bot yanlış ürünü onaylamış, müşteri düzeltiyor.
  2. Adet yanlış — bot yanlış adedi onaylamış, müşteri düzeltiyor.
  3. Tamamen farklı / menüde yok — müşteri menüde olmayan bir ürün istiyor,
     bot uydurmadan "Bu konuda bilgim yok, personelimize sorabilirsiniz." der.
"""
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SYSTEM = json.loads(
    open(
        "robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl",
        encoding="utf-8",
    ).readline()
)["messages"][0]["content"]

MENU_PRICE = {
    "Mercimek Çorbası": 85, "Kremalı Mantar Çorbası": 95, "Izgara Köfte": 240,
    "Et Döner": 280, "Izgara Tavuk Salata": 210, "Fırın Sütlaç": 100,
    "Künefe": 140, "Yayık Ayran": 45, "Limonata": 70, "Şalgam Suyu": 50,
}

# Kısa ad (Türkçe ı/İ karışıklığını önlemek için .lower() yerine sabit eşleme —
# gen_siparis_baska.py / gen_karmasik.py ile aynı kısa adlar kullanılır)
MENU_SHORT = {
    "Mercimek Çorbası":        "mercimek çorbası",
    "Kremalı Mantar Çorbası":  "mantar çorbası",
    "Izgara Köfte":            "ızgara köfte",
    "Et Döner":                "et döner",
    "Izgara Tavuk Salata":     "tavuk salata",
    "Fırın Sütlaç":            "fırın sütlaç",
    "Künefe":                  "künefe",
    "Yayık Ayran":             "ayran",
    "Limonata":                "limonata",
    "Şalgam Suyu":             "şalgam suyu",
}

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

records = []

# ── Alt tip 1: Ürün adı yanlış (10) ──────────────────────────────────────────
# (istenen, yanlış_anlaşılan, doğal düzeltme cümlesi)
NAME_CASES = [
    ("Et Döner",            "Izgara Köfte",           "Döner dedim, köfte demedim."),
    ("Mercimek Çorbası",    "Kremalı Mantar Çorbası", "Mantar çorbası değil, mercimek çorbası istemiştim."),
    ("Limonata",            "Yayık Ayran",            "Ayran değil, limonata istiyorum."),
    ("Fırın Sütlaç",        "Künefe",                 "Künefe demedim, sütlaç dedim."),
    ("Et Döner",            "Izgara Tavuk Salata",    "Tavuk salata değil, döner istemiştim."),
    ("Yayık Ayran",         "Şalgam Suyu",            "Şalgam değil, ayran istiyorum."),
    ("Et Döner",            "Izgara Köfte",           "Köfte dedim, döner demedim."),
    ("Kremalı Mantar Çorbası", "Mercimek Çorbası",    "Mercimek değil, mantar çorbası istemiştim."),
    ("Şalgam Suyu",         "Limonata",               "Limonata demedim, şalgam suyu dedim."),
    ("Künefe",              "Fırın Sütlaç",           "Sütlaç değil, künefe istiyorum."),
]

BASKA_Q = [
    "Başka bir şey ister misiniz?", "Başka bir şey alır mısınız?",
    "Başka arzunuz var mı?", "Başka ne alırsınız?",
]

for idx, (correct, wrong, correction_msg) in enumerate(NAME_CASES):
    greet = GREET_PAIRS[idx % len(GREET_PAIRS)]
    order_msg = {
        "Et Döner": "Bir et döner alayım.",
        "Mercimek Çorbası": "Bir mercimek çorbası alayım.",
        "Limonata": "Bir limonata alayım.",
        "Fırın Sütlaç": "Bir fırın sütlaç alayım.",
        "Izgara Tavuk Salata": "Bir tavuk salata alayım.",
        "Yayık Ayran": "Bir ayran alayım.",
        "Izgara Köfte": "Bir ızgara köfte alayım.",
        "Kremalı Mantar Çorbası": "Bir mantar çorbası alayım.",
        "Şalgam Suyu": "Bir şalgam suyu alayım.",
        "Künefe": "Bir künefe alayım.",
    }[correct]
    wrong_confirm = f"Elbette, {wrong} {MENU_PRICE[wrong]} TL. {BASKA_Q[idx % len(BASKA_Q)]}"
    fix_reply = (f"Anladım, {wrong} çıkarılıyor, {correct} {MENU_PRICE[correct]} TL ekleniyor. "
                 f"{BASKA_Q[(idx + 1) % len(BASKA_Q)]}")

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": order_msg},
            {"role": "assistant", "content": wrong_confirm},
            {"role": "user",      "content": correction_msg},
            {"role": "assistant", "content": fix_reply},
        ]
    })

# ── Alt tip 2: Adet yanlış (10) ──────────────────────────────────────────────
QTY_WORDS = {1: "bir", 2: "iki", 3: "üç", 4: "dört"}
QTY_WORDS_CAP = {1: "Bir", 2: "İki", 3: "Üç", 4: "Dört"}
QTY_CASES = [
    ("Izgara Köfte", 2, 1, "İki değil bir tane."),
    ("Et Döner", 3, 2, "Üç değil iki tane."),
    ("Yayık Ayran", 1, 2, "Bir değil iki tane olsun."),
    ("Limonata", 4, 3, "Dört değil üç tane."),
    ("Mercimek Çorbası", 2, 1, "İki değil, bir tane yeter."),
    ("Şalgam Suyu", 3, 2, "Üç değil iki tane istiyorum."),
    ("Kremalı Mantar Çorbası", 1, 2, "Bir değil iki tane alayım."),
    ("Künefe", 2, 1, "İki değil bir tane yeter."),
    ("Fırın Sütlaç", 3, 1, "Üç değil, bir tane istiyorum."),
    ("Izgara Tavuk Salata", 2, 3, "İki değil üç tane olsun."),
]

for idx, (item, wrong_qty, correct_qty, correction_msg) in enumerate(QTY_CASES):
    greet = GREET_PAIRS[(idx + 5) % len(GREET_PAIRS)]
    order_msg = f"{QTY_WORDS_CAP[wrong_qty]} {MENU_SHORT[item]} alayım."
    wrong_price = MENU_PRICE[item] * wrong_qty
    wrong_confirm = f"Elbette, {wrong_qty} {item} {wrong_price} TL. {BASKA_Q[idx % len(BASKA_Q)]}"
    correct_price = MENU_PRICE[item] * correct_qty
    fix_reply = f"Anladım, {correct_qty} {item} {correct_price} TL olarak güncelledim."

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": order_msg},
            {"role": "assistant", "content": wrong_confirm},
            {"role": "user",      "content": correction_msg},
            {"role": "assistant", "content": fix_reply},
        ]
    })

# ── Alt tip 3: Tamamen farklı / menüde yok (10) ──────────────────────────────
OFFMENU_CASES = [
    ("çorba",    "çay istiyorum",              "Hayır, çorba istemiyorum, çay istiyorum."),
    ("tatlı",    "dondurma istiyorum",         "Hayır, tatlı istemiyorum, dondurma istiyorum."),
    ("içecek",   "kahve istiyorum",            "Hayır, içecek değil, kahve istiyorum."),
    ("ana yemek","hamburger istiyorum",        "Hayır, ana yemek istemiyorum, hamburger istiyorum."),
    ("ana yemek","pizza istiyorum",            "Hayır, onu istemiyorum, pizza istiyorum."),
    ("çorba",    "makarna istiyorum",          "Çorba değil, makarna istiyorum."),
    ("tatlı",    "tost istiyorum",             "Tatlı değil, tost istiyorum."),
    ("ana yemek","patates kızartması istiyorum","Hayır, onu istemiyorum, patates kızartması istiyorum."),
    ("içecek",   "su istiyorum",               "İçecek değil, sade su istiyorum."),
    ("çorba",    "ezogelin çorbası istiyorum", "Hayır, mercimek değil, ezogelin çorbası istiyorum."),
]

REDIRECT_REPLY = "Bu konuda bilgim yok, personelimize sorabilirsiniz."

for idx, (category, _unused, correction_msg) in enumerate(OFFMENU_CASES):
    greet = GREET_PAIRS[(idx + 2) % len(GREET_PAIRS)]

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": correction_msg},
            {"role": "assistant", "content": REDIRECT_REPLY},
        ]
    })

print(f"Toplam: {len(records)} kayıt (isim=10, adet=10, off-menu=10)")

out_path = Path("robot_waiter_ai/datasets/processed/wbot_v4_duzeltme.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"✓ {len(records)} kayıt → {out_path}")
