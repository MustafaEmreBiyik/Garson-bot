#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v4 — B3: Modifikasyon, Sipariş Anında (S33/V01)
Hedef: 20 yeni, kural-uyumlu örnek.
Çalıştır: python scripts/gen_modifikasyon.py

Senaryo: "acılı olsun", "soğansız olsun" gibi bir modifikasyon, sipariş
cümlesiyle AYNI mesajda söyleniyor. Modifikasyonlar menü verisiyle
çelişmeyen genel mutfak talepleri (uydurma ürün özelliği eklenmiyor) —
şalgam suyu için acılı/acısız zaten menu.yaml'da var, diğerleri için
soğansız/az pişmiş/bol soslu/az şekerli/buzsuz gibi standart talepler.
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

# (ürün, modifikasyon_sıfatı, sipariş_fiili, sipariş_kısa_ad)
MOD_CASES = [
    ("Şalgam Suyu",             "acılı",        "alayım",       "şalgam suyu"),
    ("Şalgam Suyu",             "acısız",       "istiyorum",    "şalgam suyu"),
    ("Et Döner",                "soğansız",     "alayım",       "et döner"),
    ("Et Döner",                "bol soslu",    "istiyorum",    "et döner"),
    ("Izgara Köfte",            "az pişmiş",    "alayım",       "ızgara köfte"),
    ("Izgara Köfte",            "bol soslu",    "alabilir miyim", "ızgara köfte"),
    ("Mercimek Çorbası",        "az tuzlu",     "alayım",       "mercimek çorbası"),
    ("Kremalı Mantar Çorbası",  "az tuzlu",     "istiyorum",    "mantar çorbası"),
    ("Limonata",                "az şekerli",   "alayım",       "limonata"),
    ("Limonata",                "buzsuz",       "istiyorum",    "limonata"),
    ("Yayık Ayran",             "buzlu",        "alayım",       "ayran"),
    ("Yayık Ayran",             "az tuzlu",     "alabilir miyim", "ayran"),
    ("Künefe",                  "az şerbetli",  "alayım",       "künefe"),
    ("Künefe",                  "bol şerbetli", "istiyorum",    "künefe"),
    ("Fırın Sütlaç",            "az şekerli",   "alayım",       "fırın sütlaç"),
    ("Fırın Sütlaç",            "soğuk servis", "alabilir miyim", "fırın sütlaç"),
    ("Izgara Tavuk Salata",     "sossuz",       "alayım",       "tavuk salata"),
    ("Izgara Tavuk Salata",     "bol soslu",    "istiyorum",    "tavuk salata"),
    ("Et Döner",                "az soslu",     "alabilir miyim", "et döner"),
    ("Izgara Köfte",            "soğansız",     "alayım",       "ızgara köfte"),
]

records = []
for idx, (item, mod, verb, short) in enumerate(MOD_CASES):
    greet = GREET_PAIRS[idx % len(GREET_PAIRS)]
    user_order = f"Bir {short} alayım, {mod} olsun." if verb == "alayım" else \
                 f"Bir {short} istiyorum, {mod} olsun." if verb == "istiyorum" else \
                 f"Bir {short} alabilir miyim, {mod} olsun?"
    pos = POSITIVE_WORDS[idx % len(POSITIVE_WORDS)]
    baska = BASKA_FORMS[idx % len(BASKA_FORMS)]
    price = MENU[item][1]
    bot_confirm = f"{pos}, {item} {mod} olacak şekilde, {price} TL. {baska}"

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": user_order},
            {"role": "assistant", "content": bot_confirm},
        ]
    })

print(f"Toplam: {len(records)} kayıt")

out_path = Path("robot_waiter_ai/datasets/processed/wbot_v4_modifikasyon.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"✓ {len(records)} kayıt → {out_path}")
