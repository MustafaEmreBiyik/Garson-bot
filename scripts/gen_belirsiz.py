#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v4 — B1: Belirsiz/Eksik Girdi (S25/S27)
Hedef: 20 yeni, kural-uyumlu örnek.
Çalıştır: python scripts/gen_belirsiz.py

Senaryo: Müşteri belirsiz/eksik bir şey söylüyor → robot netleştirici soru
sorar. S03 sessizlik politikasındaki "birebir tekrar değil" ilkesi burada da
uygulanır: art arda iki belirsizlik olursa ikinci netleştirme sorusu
BİRİNCİSİNİN AYNISI olamaz, farklı bir soru formu kullanılır.
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
    "Başka bir şey alır mısınız?", "Başka ne arzu edersiniz?", "Başka ne alırsınız?",
    "Başka bir şey ister misiniz?", "Başka bir şey daha alır mısınız?",
    "Başka bir isteğiniz var mı?", "Eklemek istediğiniz bir şey var mı?",
    "Ekleyeceğimiz bir şey var mı?", "İlaveten bir arzunuz olur mu?", "Başka arzunuz var mı?",
]
POSITIVE_WORDS = ["Elbette", "Tabii ki", "Tabii efendim", "Memnuniyetle", "Harika seçim"]

# Belirsiz/eksik kullanıcı cümleleri
VAGUE_PHRASES = [
    "Şey... onu istiyorum yani...",
    "Bir tane.",
    "Hani şu, onu...",
    "Ee... bilmiyorum, bir şey.",
    "Şunu... neydi...",
    "Onu alayım, işte.",
    "Bir tane, şeyden.",
    "Yani... bir şey istiyorum.",
]

# Netleştirici sorular — her biri farklı, art arda kullanıldığında birebir tekrar olmaz
CLARIFY_QUESTIONS = [
    "Tam anlayamadım, ne almak istersiniz?",
    "Hangi ürünü istersiniz?",
    "Menüden hangi ürünü söylüyorsunuz, belirtir misiniz?",
    "Anlayamadım, hangi ürünü arzu edersiniz?",
    "Üzgünüm, tam duyamadım, ne alırsınız?",
    "Hangi ürünü kastediyorsunuz?",
]

# Belirsizlik sonrası netleşme cümleleri (müşteri sonunda ürünü söylüyor)
CLARIFIED_ORDERS = [
    "Bir köfte alayım.",
    "Bir ayran alayım.",
    "Bir mercimek çorbası istiyorum.",
    "Bir künefe alabilir miyim?",
    "Bir limonata alayım.",
    "Bir et döner istiyorum.",
    "Bir tavuk salata alayım.",
    "Bir şalgam suyu alabilir miyim?",
    "Bir mantar çorbası istiyorum.",
    "Bir fırın sütlaç alayım.",
]

ORDER_TO_ITEM = {
    "Bir köfte alayım.": "Izgara Köfte",
    "Bir ayran alayım.": "Yayık Ayran",
    "Bir mercimek çorbası istiyorum.": "Mercimek Çorbası",
    "Bir künefe alabilir miyim?": "Künefe",
    "Bir limonata alayım.": "Limonata",
    "Bir et döner istiyorum.": "Et Döner",
    "Bir tavuk salata alayım.": "Izgara Tavuk Salata",
    "Bir şalgam suyu alabilir miyim?": "Şalgam Suyu",
    "Bir mantar çorbası istiyorum.": "Kremalı Mantar Çorbası",
    "Bir fırın sütlaç alayım.": "Fırın Sütlaç",
}

records = []

# ── Bölüm A: Tek belirsizlik → netleşme → sipariş (10) ──────────────────────
for idx in range(10):
    greet = GREET_PAIRS[idx % len(GREET_PAIRS)]
    vague = VAGUE_PHRASES[idx % len(VAGUE_PHRASES)]
    clarify = CLARIFY_QUESTIONS[idx % len(CLARIFY_QUESTIONS)]
    clarified = CLARIFIED_ORDERS[idx % len(CLARIFIED_ORDERS)]
    item = ORDER_TO_ITEM[clarified]
    pos = POSITIVE_WORDS[idx % len(POSITIVE_WORDS)]
    baska = BASKA_FORMS[idx % len(BASKA_FORMS)]
    confirm = f"{pos}, {item} {MENU[item][1]} TL. {baska}"

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": vague},
            {"role": "assistant", "content": clarify},
            {"role": "user",      "content": clarified},
            {"role": "assistant", "content": confirm},
        ]
    })

# ── Bölüm B: İki belirsizlik (farklı netleştirme) → sipariş (10) ────────────
for idx in range(10):
    greet = GREET_PAIRS[(idx + 3) % len(GREET_PAIRS)]
    vague1 = VAGUE_PHRASES[idx % len(VAGUE_PHRASES)]
    vague2 = VAGUE_PHRASES[(idx + 4) % len(VAGUE_PHRASES)]
    clarify1 = CLARIFY_QUESTIONS[idx % len(CLARIFY_QUESTIONS)]
    clarify2 = CLARIFY_QUESTIONS[(idx + 3) % len(CLARIFY_QUESTIONS)]
    # aynı sorunun tekrar seçilmediğinden emin ol
    if clarify2 == clarify1:
        clarify2 = CLARIFY_QUESTIONS[(idx + 3 + 1) % len(CLARIFY_QUESTIONS)]

    clarified = CLARIFIED_ORDERS[(idx + 5) % len(CLARIFIED_ORDERS)]
    item = ORDER_TO_ITEM[clarified]
    pos = POSITIVE_WORDS[(idx + 1) % len(POSITIVE_WORDS)]
    baska = BASKA_FORMS[(idx + 2) % len(BASKA_FORMS)]
    confirm = f"{pos}, {item} {MENU[item][1]} TL. {baska}"

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": vague1},
            {"role": "assistant", "content": clarify1},
            {"role": "user",      "content": vague2},
            {"role": "assistant", "content": clarify2},
            {"role": "user",      "content": clarified},
            {"role": "assistant", "content": confirm},
        ]
    })

print(f"Toplam: {len(records)} kayıt (tek-belirsizlik=10, çift-belirsizlik=10)")

out_path = Path("robot_waiter_ai/datasets/processed/wbot_v4_belirsiz.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"✓ {len(records)} kayıt → {out_path}")
