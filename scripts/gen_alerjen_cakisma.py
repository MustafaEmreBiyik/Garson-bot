#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v4 — B4: Sipariş + Alerjen Çakışması (S35/V03)
Hedef: 15 yeni, kural-uyumlu örnek.
Çalıştır: python scripts/gen_alerjen_cakisma.py

Senaryo: Müşteri, menu.yaml'daki `allergens` alanına göre kendi beyan ettiği
alerjenle çakışan bir ürün sipariş ediyor. Robot: uyarır, menü kaynağına
atıfla konuşur ("menü bilgilerimize göre"), varsa güvenli bir alternatif
önerir, personel teyidi ister. Güvenli alternatif YOKSA kesin "uygun
ürünümüz yok" demez — "Bu konuda personelimize danışmanızı öneririm" kalıbı
kullanılır (SENARYO_PLANI_FAZ1.md Karar 1 ile uyumlu, anti-hallüsinasyon).
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
]

# menu.yaml allergens: Mercimek(gluten), Mantar(dairy,gluten), Köfte(gluten),
# Döner(gluten), Tavuk Salata(-), Sütlaç(dairy), Künefe(dairy,gluten,nuts),
# Ayran(dairy), Limonata(-), Şalgam(-)

ALLERGEN_TR = {"gluten": "gluten", "dairy": "süt ürünü", "nuts": "kuruyemiş"}

NO_ALT_REPLY = "Bu konuda personelimize danışmanızı öneririm."

# (sipariş_ürünü, alerjen_kodu, kullanıcı_alerjen_kelimesi, alternatif_ürün_veya_None)
CASES = [
    ("Künefe",                 "nuts",   "fıstık",  "Fırın Sütlaç"),
    ("Kremalı Mantar Çorbası", "dairy",  "süt",     "Mercimek Çorbası"),
    ("Yayık Ayran",            "dairy",  "süt",     "Limonata"),
    ("Fırın Sütlaç",           "dairy",  "süt",     None),
    ("Künefe",                 "dairy",  "süt",     None),
    ("Izgara Köfte",           "gluten", "gluten",  "Izgara Tavuk Salata"),
    ("Et Döner",               "gluten", "gluten",  "Izgara Tavuk Salata"),
    ("Mercimek Çorbası",       "gluten", "gluten",  None),
    ("Kremalı Mantar Çorbası", "gluten", "gluten",  None),
    ("Künefe",                 "gluten", "gluten",  "Fırın Sütlaç"),
    ("Yayık Ayran",            "dairy",  "süt",     "Şalgam Suyu"),
    ("Izgara Köfte",           "gluten", "gluten",  "Izgara Tavuk Salata"),
    ("Et Döner",               "gluten", "gluten",  "Izgara Tavuk Salata"),
    ("Künefe",                 "nuts",   "kuruyemiş", "Fırın Sütlaç"),
    ("Kremalı Mantar Çorbası", "dairy",  "süt",     "Mercimek Çorbası"),
]

ORDER_VERBS = ["alayım", "istiyorum", "alabilir miyim"]

records = []
for idx, (item, allergen_code, allergen_word, alt_item) in enumerate(CASES):
    greet = GREET_PAIRS[idx % len(GREET_PAIRS)]
    short = MENU[item][0]
    verb = ORDER_VERBS[idx % len(ORDER_VERBS)]
    user_order = f"Bir {short} {verb}, {allergen_word} alerjim var." if verb != "alabilir miyim" \
        else f"Bir {short} alabilir miyim, {allergen_word} alerjim var?"

    allergen_tr = ALLERGEN_TR[allergen_code]

    if alt_item:
        reply = (
            f"Menü bilgilerimize göre {item} {allergen_tr} içeriyor olarak işaretli, "
            f"bu yüzden önermiyorum. {alt_item} bu alerjenden arınık görünüyor, onu "
            f"tercih edebilirsiniz. Personelimize de teyit ettirmenizi rica ederim."
        )
    else:
        reply = (
            f"Menü bilgilerimize göre {item} {allergen_tr} içeriyor olarak işaretli, "
            f"bu yüzden önermiyorum. {NO_ALT_REPLY}"
        )

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": user_order},
            {"role": "assistant", "content": reply},
        ]
    })

print(f"Toplam: {len(records)} kayıt")

out_path = Path("robot_waiter_ai/datasets/processed/wbot_v4_alerjen_cakisma.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"✓ {len(records)} kayıt → {out_path}")
