#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v4 — B6: S19-B Kanonik Kalıp — Alerji + Öneri (S38/V06)
Hedef: 20 yeni, kural-uyumlu örnek.
Çalıştır: python scripts/gen_alerji_oneri.py

Senaryo: Müşteri açık uçlu bir öneri istiyor, alerji/kısıt belirterek
("Glüten alerjim var, ne önerirsiniz?"). SENARYO_PLANI_FAZ1.md Karar 1'in
kanonik kalıbı birebir uygulanır:
  "Menü bilgilerimize göre [ürünler] [alerjen] içermiyor olarak işaretli.
   Mutfakta çapraz bulaşma olabileceği için personelimize de teyit
   ettirmenizi rica ederim."
Hiçbir uygun ürün yoksa (S35'teki gibi) dürüstçe söylenir, "personelimize
danışmanızı öneririm" kalıbı kullanılır — kesin "yok" iddiası yerine.
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

GREET_PAIRS = [
    ("Merhaba.",            "Hoş geldiniz, çorba, ana yemek, tatlı ve içeceklerimizden ne arzu edersiniz?"),
    ("Selam.",              "Merhaba, çorba, ana yemek, tatlı ve içecek seçeneklerinden ne istersiniz?"),
    ("İyi günler.",         "Buyurun, çorba, ana yemek, tatlı ve içecek arasından ne alırsınız?"),
    ("İyi akşamlar.",       "Hoş geldiniz, çorba, ana yemek, tatlı ve içecek sunuyoruz, ne tercih edersiniz?"),
    ("Günaydın.",           "Günaydın, çorba, ana yemek, tatlı ve içeceklerimizden ne seçersiniz?"),
]

ALLERGEN_TR = {"gluten": "gluten", "dairy": "süt ürünü", "nuts": "kuruyemiş"}
ALLERGEN_USER_WORD = {"gluten": "Glüten", "dairy": "Süt", "nuts": "Kuruyemiş"}

# menu.yaml'a göre kategori bazlı alerjensiz ürün listeleri
# Çorba: Mercimek(gluten), Mantar(dairy,gluten)
# Ana Yemek: Köfte(gluten), Döner(gluten), Tavuk Salata(-)
# Tatlı: Sütlaç(dairy), Künefe(dairy,gluten,nuts)
# İçecek: Ayran(dairy), Limonata(-), Şalgam(-)

FREE_OF = {
    "gluten": {
        "genel":     ["Izgara Tavuk Salata", "Fırın Sütlaç", "Yayık Ayran"],
        "çorba":     [],
        "ana yemek": ["Izgara Tavuk Salata"],
        "tatlı":     ["Fırın Sütlaç"],
        "içecek":    ["Yayık Ayran", "Limonata", "Şalgam Suyu"],
    },
    "dairy": {
        "genel":     ["Mercimek Çorbası", "Et Döner", "Limonata"],
        "çorba":     ["Mercimek Çorbası"],
        "ana yemek": ["Izgara Köfte", "Et Döner", "Izgara Tavuk Salata"],
        "tatlı":     [],
        "içecek":    ["Limonata", "Şalgam Suyu"],
    },
    "nuts": {
        "genel":     ["Izgara Köfte", "Et Döner", "Limonata"],
        "çorba":     ["Mercimek Çorbası", "Kremalı Mantar Çorbası"],
        "ana yemek": ["Izgara Köfte", "Et Döner", "Izgara Tavuk Salata"],
        "tatlı":     ["Fırın Sütlaç"],
        "içecek":    ["Yayık Ayran", "Limonata", "Şalgam Suyu"],
    },
}

CATEGORY_QUESTION = {
    "genel":     "{Word} alerjim var, ne önerirsiniz?",
    "çorba":     "{Word} alerjim var, çorba önerir misiniz?",
    "ana yemek": "{Word} alerjim var, ana yemek önerir misiniz?",
    "tatlı":     "{Word} alerjim var, tatlı önerir misiniz?",
    "içecek":    "{Word} alerjim var, içecek önerir misiniz?",
}

NO_ALT_REPLY = "Bu konuda personelimize danışmanızı öneririm."


def fmt_list(items):
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " ve " + items[-1]


records = []
allergens = ["gluten", "dairy", "nuts"]
categories = ["genel", "çorba", "ana yemek", "tatlı", "içecek"]

idx = 0
for allergen in allergens:
    for category in categories:
        greet = GREET_PAIRS[idx % len(GREET_PAIRS)]
        question = CATEGORY_QUESTION[category].format(Word=ALLERGEN_USER_WORD[allergen])
        items = FREE_OF[allergen][category]
        allergen_tr = ALLERGEN_TR[allergen]

        if items:
            reply = (
                f"Menü bilgilerimize göre {fmt_list(items)} {allergen_tr} içermiyor "
                f"olarak işaretli. Mutfakta çapraz bulaşma olabileceği için "
                f"personelimize de teyit ettirmenizi rica ederim."
            )
        else:
            reply = (
                f"Menü bilgilerimize göre bu kategoride {allergen_tr} içermeyen bir "
                f"ürünümüz işaretli değil. {NO_ALT_REPLY}"
            )

        records.append({
            "messages": [
                {"role": "system",    "content": SYSTEM},
                {"role": "user",      "content": greet[0]},
                {"role": "assistant", "content": greet[1]},
                {"role": "user",      "content": question},
                {"role": "assistant", "content": reply},
            ]
        })
        idx += 1

# ── Ek varyantlar — farklı soru kalıplarıyla "genel" öneri (5) ──────────────
ALT_GENERAL_QUESTIONS = [
    "{Word} alerjim var, bana ne tavsiye edersiniz?",
    "{Word} alerjisi olan biri ne yiyebilir?",
    "{Word} alerjim var, uygun bir şey var mı?",
    "{Word} alerjim var, neyi önerirsiniz bana?",
    "{Word} alerjisine uygun ne var menüde?",
]

for i, allergen in enumerate(allergens):
    for j in range(2 if allergen != "nuts" else 1):
        greet = GREET_PAIRS[idx % len(GREET_PAIRS)]
        q_idx = (i * 2 + j) % len(ALT_GENERAL_QUESTIONS)
        question = ALT_GENERAL_QUESTIONS[q_idx].format(Word=ALLERGEN_USER_WORD[allergen])
        items = FREE_OF[allergen]["genel"]
        allergen_tr = ALLERGEN_TR[allergen]
        reply = (
            f"Menü bilgilerimize göre {fmt_list(items)} {allergen_tr} içermiyor "
            f"olarak işaretli. Mutfakta çapraz bulaşma olabileceği için "
            f"personelimize de teyit ettirmenizi rica ederim."
        )
        records.append({
            "messages": [
                {"role": "system",    "content": SYSTEM},
                {"role": "user",      "content": greet[0]},
                {"role": "assistant", "content": greet[1]},
                {"role": "user",      "content": question},
                {"role": "assistant", "content": reply},
            ]
        })
        idx += 1

print(f"Toplam: {len(records)} kayıt")

out_path = Path("robot_waiter_ai/datasets/processed/wbot_v4_alerji_oneri.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"✓ {len(records)} kayıt → {out_path}")
