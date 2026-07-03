#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v4 — B5: Pratik Soru (S37/V05)
Hedef: 10 yeni, kural-uyumlu örnek.
Çalıştır: python scripts/gen_pratik_soru.py

Senaryo: Tuvalet, wifi, otopark gibi restoran işletmesiyle ilgili ama
menü dışı pratik sorular. Robotun bu bilgiye erişimi yok — uydurma
yapmadan personele yönlendirir.
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

REDIRECT_VARIANTS = [
    "Bu konuda bilgim yok, personelimize sorabilirsiniz.",
    "Bu konuda bilgim yok, personelimize danışabilirsiniz.",
    "Bu konuda bilgim yok, personelimiz size yardımcı olabilir.",
]

PRACTICAL_QUESTIONS = [
    "Tuvalet nerede?",
    "Wifi şifresi nedir?",
    "Otopark var mı?",
    "Sigara içilen bir alan var mı?",
    "Kredi kartı geçiyor mu?",
    "Bebek sandalyesi var mı?",
    "Rezervasyon yapabilir miyim?",
    "Engelli erişimi var mı?",
    "Çocuk oyun alanı var mı?",
    "Evcil hayvan kabul ediyor musunuz?",
]

records = []
for idx, question in enumerate(PRACTICAL_QUESTIONS):
    greet = GREET_PAIRS[idx % len(GREET_PAIRS)]
    reply = REDIRECT_VARIANTS[idx % len(REDIRECT_VARIANTS)]

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": question},
            {"role": "assistant", "content": reply},
        ]
    })

print(f"Toplam: {len(records)} kayıt")

out_path = Path("robot_waiter_ai/datasets/processed/wbot_v4_pratik_soru.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"✓ {len(records)} kayıt → {out_path}")
