#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v4 — B7: Sipariş Durumu / "Ne Zaman Gelir?" (S40)
Hedef: 15 yeni, kural-uyumlu örnek.
Çalıştır: python scripts/gen_siparis_durumu.py

Senaryo: Müşteri siparişinin ne zaman geleceğini soruyor. Robotun mutfak
durumuna gerçek zamanlı erişimi yok — uydurma bir süre tahmini ("5 dakikaya
gelir" gibi) VERİLMEZ. Dürüst yanıt + personel yönlendirmesi.
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

STATUS_QUESTIONS = [
    "Yemeğim ne zaman gelir?",
    "Siparişim nerede kaldı?",
    "Ne kadar sürer?",
    "Daha ne kadar bekleyeceğiz?",
    "Uzun sürüyor, ne oldu acaba?",
    "Siparişimiz ne zaman hazır olur?",
    "Yemekler daha gelmedi, ne zaman gelir?",
    "Çok bekledik, sipariş nerede?",
    "Az kaldı mı acaba?",
    "Mutfaktan haber var mı?",
    "Siparişimiz unutuldu mu acaba?",
    "Ne zaman servis edilir?",
    "Beklemek zorunda mıyız daha?",
    "Sipariş ne durumda?",
    "Yemeğimiz gelmek üzere mi?",
]

# Dürüst yanıt + personel yönlendirmesi — uydurma süre tahmini YOK
HONEST_REDIRECT = [
    "Bu konuda net bilgim yok, personelimize sorabilirsiniz.",
    "Kesin süreyi bilemiyorum, personelimiz size bilgi verebilir.",
    "Bu konuda bilgim yok, hemen personelimize ileteceğim.",
    "Net bir süre veremem, personelimize danışabilirsiniz.",
    "Mutfağın durumunu bilmiyorum, personelimiz size bilgi verebilir.",
]

records = []
for idx, question in enumerate(STATUS_QUESTIONS):
    greet = GREET_PAIRS[idx % len(GREET_PAIRS)]
    reply = HONEST_REDIRECT[idx % len(HONEST_REDIRECT)]

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

out_path = Path("robot_waiter_ai/datasets/processed/wbot_v4_siparis_durumu.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"✓ {len(records)} kayıt → {out_path}")
