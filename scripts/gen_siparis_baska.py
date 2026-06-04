#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v3 — Sipariş onayı / 'başka' pekiştirme eğitim verisi üreticisi
Hedef: 150 yeni, kural-uyumlu, çeşitli multi-turn örnek
Çalıştır: python scripts/gen_siparis_baska.py
"""
import json, sys, random, itertools
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

random.seed(7)
_rng = random.Random(13)

SYSTEM = open(
    "robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl",
    encoding="utf-8",
).readline()
SYSTEM = json.loads(SYSTEM)["messages"][0]["content"]

# ── Menü ──────────────────────────────────────────────────────────────────────
MENU = {
    "Mercimek Çorbası":   ("mercimek çorbası", 85),
    "Kremalı Mantar Çorbası": ("mantar çorbası",   95),
    "Izgara Köfte":       ("ızgara köfte",     240),
    "Et Döner":           ("et döner",         280),
    "Izgara Tavuk Salata":("tavuk salata",      210),
    "Fırın Sütlaç":       ("fırın sütlaç",     100),
    "Künefe":             ("künefe",            140),
    "Yayık Ayran":        ("ayran",              45),
    "Limonata":           ("limonata",           70),
    "Şalgam Suyu":        ("şalgam suyu",        50),
}
ITEMS = list(MENU.keys())

# ── Karşılama turları (kısa — ana öğrenim sipariş onayında) ───────────────────
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

# ── "başka" eşdeğerleri ───────────────────────────────────────────────────────
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
    "Eklemek istediğiniz başka bir şey var mı?",
    "İlaveten ekleyelim mi?",
    "Başka arzunuz var mı?",
]

# ── Olumlu kabul sözcükleri ───────────────────────────────────────────────────
POSITIVE_WORDS = ["Elbette", "Tabii ki", "Tabii efendim", "Memnuniyetle", "Harika seçim"]

# ── Kapanış turları ───────────────────────────────────────────────────────────
CLOSE_PAIRS = [
    ("Yok teşekkürler.",          "Peki, afiyet olsun!"),
    ("Bu kadar.",                 "Anladım, afiyet olsun!"),
    ("Başka istemiyorum.",        "Tabii, afiyet olsun!"),
    ("Hayır teşekkürler.",        "Peki, afiyet olsun!"),
    ("Bu kadar yeterli.",         "Anladım, afiyet olsun!"),
    ("Yeterli teşekkürler.",      "Tabii, afiyet olsun!"),
    ("Hayır bu kadar.",           "Harika, afiyet olsun!"),
    ("Şimdilik bu kadar.",        "Peki, afiyet olsun!"),
    ("Hayır, bu kadar.",          "Tabii, afiyet olsun!"),
    ("Başka isteğim yok.",        "Anladım, afiyet olsun!"),
]

# ── Sipariş cümlesi kalıpları ─────────────────────────────────────────────────
def order_user(item_key, count=1, style=0):
    short = MENU[item_key][0]
    if count > 1:
        templates = [
            f"{count} {short} alayım.",
            f"{count} {short} istiyorum.",
            f"{count} tane {short} verir misiniz?",
            f"{count} adet {short} alabilir miyim?",
        ]
    else:
        templates = [
            f"Bir {short} alayım.",
            f"{short.capitalize()} istiyorum.",
            f"{short.capitalize()} alabilir miyim?",
            f"Bir {short} verir misiniz?",
            f"Bir porsiyon {short} alayım.",
            f"{short.capitalize()} siparişi vereyim.",
            f"Lütfen bir {short} getirin.",
            f"Bana bir {short} alayım.",
        ]
    return templates[style % len(templates)]


def order_bot_single(item_key, count=1, baska_idx=0, pos_idx=0):
    name = item_key
    price = MENU[item_key][1] * count
    pos   = POSITIVE_WORDS[pos_idx % len(POSITIVE_WORDS)]
    baska = BASKA_FORMS[baska_idx % len(BASKA_FORMS)]
    if count > 1:
        return f"{pos}, {count} {name} {price} TL. {baska}"
    else:
        return f"{pos}, {name} {price} TL. {baska}"


def order_user_multi(items_counts, style=0):
    """items_counts: list of (item_key, count)"""
    parts = []
    for item_key, count in items_counts:
        short = MENU[item_key][0]
        if count > 1:
            parts.append(f"{count} {short}")
        else:
            parts.append(f"bir {short}")
    if style % 3 == 0:
        return " ve ".join(parts) + " alayım."
    elif style % 3 == 1:
        return " ve ".join(parts) + " istiyorum."
    else:
        return " ile ".join(parts) + " verir misiniz?"


def order_bot_multi(items_counts, baska_idx=0, pos_idx=0):
    parts = []
    for item_key, count in items_counts:
        price = MENU[item_key][1] * count
        name  = item_key
        if count > 1:
            parts.append(f"{count} {name} {price} TL")
        else:
            parts.append(f"{name} {price} TL")
    baska = BASKA_FORMS[baska_idx % len(BASKA_FORMS)]
    pos   = POSITIVE_WORDS[pos_idx % len(POSITIVE_WORDS)]
    return f"{pos}, {'. '.join(parts)}. {baska}"


# ── Bölüm A: Tek ürün siparişleri (60 örnek) ─────────────────────────────────
section_a = []
for idx, item_key in enumerate(ITEMS):
    for style in range(6):
        greet = GREET_PAIRS[idx % len(GREET_PAIRS)]
        close = CLOSE_PAIRS[(idx * 6 + style) % len(CLOSE_PAIRS)]
        user_order = order_user(item_key, count=1, style=style)
        bot_conf   = order_bot_single(
            item_key, count=1,
            baska_idx=idx * 6 + style,
            pos_idx=style,
        )
        section_a.append({
            "messages": [
                {"role": "system",    "content": SYSTEM},
                {"role": "user",      "content": greet[0]},
                {"role": "assistant", "content": greet[1]},
                {"role": "user",      "content": user_order},
                {"role": "assistant", "content": bot_conf},
                {"role": "user",      "content": close[0]},
                {"role": "assistant", "content": close[1]},
            ]
        })

# ── Bölüm B: Çift ürün siparişleri (50 örnek) ────────────────────────────────
PAIRS = [
    ("Mercimek Çorbası",       "Yayık Ayran"),
    ("Kremalı Mantar Çorbası", "Limonata"),
    ("Izgara Köfte",           "Şalgam Suyu"),
    ("Et Döner",               "Yayık Ayran"),
    ("Izgara Tavuk Salata",    "Limonata"),
    ("Fırın Sütlaç",           "Yayık Ayran"),
    ("Künefe",                 "Şalgam Suyu"),
    ("Mercimek Çorbası",       "Izgara Köfte"),
    ("Kremalı Mantar Çorbası", "Et Döner"),
    ("Izgara Tavuk Salata",    "Künefe"),
    ("Mercimek Çorbası",       "Fırın Sütlaç"),
    ("Et Döner",               "Künefe"),
    ("Izgara Köfte",           "Limonata"),
    ("Kremalı Mantar Çorbası", "Yayık Ayran"),
    ("Fırın Sütlaç",           "Limonata"),
    ("Izgara Tavuk Salata",    "Şalgam Suyu"),
    ("Mercimek Çorbası",       "Et Döner"),
    ("Izgara Köfte",           "Fırın Sütlaç"),
    ("Künefe",                 "Yayık Ayran"),
    ("Et Döner",               "Limonata"),
    ("Kremalı Mantar Çorbası", "Künefe"),
    ("Izgara Köfte",           "Yayık Ayran"),
    ("Mercimek Çorbası",       "Limonata"),
    ("Fırın Sütlaç",           "Şalgam Suyu"),
    ("Et Döner",               "Şalgam Suyu"),
    ("Izgara Tavuk Salata",    "Fırın Sütlaç"),
    ("Kremalı Mantar Çorbası", "Şalgam Suyu"),
    ("Izgara Köfte",           "Künefe"),
    ("Mercimek Çorbası",       "Künefe"),
    ("Izgara Tavuk Salata",    "Yayık Ayran"),
    ("Et Döner",               "Fırın Sütlaç"),
    ("Mercimek Çorbası",       "Şalgam Suyu"),
    ("Izgara Köfte",           "Et Döner"),
    ("Kremalı Mantar Çorbası", "Fırın Sütlaç"),
    ("Künefe",                 "Limonata"),
    ("Fırın Sütlaç",           "Şalgam Suyu"),
    ("Mercimek Çorbası",       "Yayık Ayran"),   # farklı stil ile tekrar
    ("Et Döner",               "Künefe"),
    ("Izgara Tavuk Salata",    "Yayık Ayran"),
    ("Kremalı Mantar Çorbası", "Limonata"),
    ("Izgara Köfte",           "Şalgam Suyu"),
    ("Fırın Sütlaç",           "Künefe"),
    ("Mercimek Çorbası",       "Izgara Tavuk Salata"),
    ("Et Döner",               "Yayık Ayran"),
    ("Izgara Köfte",           "Fırın Sütlaç"),
    ("Künefe",                 "Yayık Ayran"),
    ("Şalgam Suyu",            "Limonata"),
    ("Mercimek Çorbası",       "Et Döner"),
    ("Kremalı Mantar Çorbası", "Izgara Köfte"),
    ("Fırın Sütlaç",           "Yayık Ayran"),
]

section_b = []
for idx, (a_key, b_key) in enumerate(PAIRS[:50]):
    greet = GREET_PAIRS[(idx + 3) % len(GREET_PAIRS)]
    close = CLOSE_PAIRS[(idx + 2) % len(CLOSE_PAIRS)]
    counts = [(a_key, 1), (b_key, 1)]
    user_order = order_user_multi(counts, style=idx)
    bot_conf   = order_bot_multi(counts, baska_idx=idx + 10, pos_idx=idx + 2)
    section_b.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": user_order},
            {"role": "assistant", "content": bot_conf},
            {"role": "user",      "content": close[0]},
            {"role": "assistant", "content": close[1]},
        ]
    })

# ── Bölüm C: Adet belirtilmiş siparişler (20 örnek) ──────────────────────────
COUNT_ORDERS = [
    ("Mercimek Çorbası", 2), ("Izgara Köfte", 2), ("Yayık Ayran", 3),
    ("Et Döner", 2), ("Limonata", 4), ("Künefe", 2), ("Fırın Sütlaç", 3),
    ("Şalgam Suyu", 2), ("Kremalı Mantar Çorbası", 2), ("Izgara Tavuk Salata", 2),
    ("Mercimek Çorbası", 3), ("Yayık Ayran", 2), ("Et Döner", 3), ("Limonata", 2),
    ("Künefe", 3), ("Izgara Köfte", 3), ("Şalgam Suyu", 4), ("Fırın Sütlaç", 2),
    ("Kremalı Mantar Çorbası", 3), ("Izgara Tavuk Salata", 3),
]

section_c = []
for idx, (item_key, count) in enumerate(COUNT_ORDERS):
    greet = GREET_PAIRS[(idx + 5) % len(GREET_PAIRS)]
    close = CLOSE_PAIRS[(idx + 4) % len(CLOSE_PAIRS)]
    user_order = order_user(item_key, count=count, style=idx)
    bot_conf   = order_bot_single(item_key, count=count, baska_idx=idx + 20, pos_idx=idx + 1)
    section_c.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": user_order},
            {"role": "assistant", "content": bot_conf},
            {"role": "user",      "content": close[0]},
            {"role": "assistant", "content": close[1]},
        ]
    })

# ── Bölüm D: Çok turlu — ürün sorusu → sipariş (10 örnek) ────────────────────
# Kullanıcı önce ürünü sorar, bot açıklar ve "Getireyim mi?" der, kullanıcı onaylar.
# Onay turunda "başka" çıkmalı.
PRODUCT_Q = [
    (
        "Izgara köfte nasıl bir yemek?",
        "Kasap köfte, elma dilim patates ve köz biberle servis edilir. Getireyim mi?",
        "Evet bir köfte alayım.",
        f"Elbette, Izgara Köfte 240 TL. {BASKA_FORMS[0]}",
    ),
    (
        "Kremalı mantar çorbası nasıl?",
        "Taze dağ mantarları ve kremadan yapılır, hafif ve doyurucu. Getireyim mi?",
        "Bir mantar çorbası alayım.",
        f"Tabii ki, Kremalı Mantar Çorbası 95 TL. {BASKA_FORMS[1]}",
    ),
    (
        "Künefe nedir?",
        "Özel Hatay peyniri ve ince tel kadayıftan sıcak servis edilir. Getireyim mi?",
        "Bir künefe alayım.",
        f"Memnuniyetle, Künefe 140 TL. {BASKA_FORMS[2]}",
    ),
    (
        "Et döner nasıl hazırlanıyor?",
        "İnce dilimlenmiş dana eti, özel soslu lavaş ve sumaklı soğanla servis edilir. Arzu eder misiniz?",
        "Bir et döner alayım.",
        f"Tabii efendim, Et Döner 280 TL. {BASKA_FORMS[3]}",
    ),
    (
        "Fırın sütlaç nedir?",
        "Fırında üzeri kızarmış günlük taze sütlaçtır. Getireyim mi?",
        "Bir fırın sütlaç alayım.",
        f"Elbette, Fırın Sütlaç 100 TL. {BASKA_FORMS[4]}",
    ),
    (
        "Izgara tavuk salata nasıl bir yemek?",
        "Özel marineli tavuk ve taze yeşilliklerle hazırlanır. Getireyim mi?",
        "Bir tavuk salata alayım.",
        f"Memnuniyetle, Izgara Tavuk Salata 210 TL. {BASKA_FORMS[5]}",
    ),
    (
        "Yayık ayran nasıl?",
        "Ev yapımı, köpüklü ve soğuk ayrandır. İster misiniz?",
        "Bir ayran alayım.",
        f"Tabii ki, Yayık Ayran 45 TL. {BASKA_FORMS[6]}",
    ),
    (
        "Şalgam suyu acılı mı?",
        "Acılı veya acısız seçeneği var, tercihinize göre çıkabilir. İster misiniz?",
        "Acısız bir şalgam alayım.",
        f"Elbette, Şalgam Suyu 50 TL. {BASKA_FORMS[7]}",
    ),
    (
        "Mercimek çorbası her gün taze mi?",
        "Evet, kırmızı mercimek, soğan ve havuçla günlük hazırlanır. Getireyim mi?",
        "Bir mercimek çorbası alayım.",
        f"Tabii efendim, Mercimek Çorbası 85 TL. {BASKA_FORMS[8]}",
    ),
    (
        "Limonata nasıl bir içecek?",
        "Taze nane yapraklarıyla yapılan naneli limonata, çok ferahlatıcı. Getireyim mi?",
        "Bir limonata alayım.",
        f"Memnuniyetle, Limonata 70 TL. {BASKA_FORMS[9]}",
    ),
]

section_d = []
for idx, (q, ans, confirm_user, confirm_bot) in enumerate(PRODUCT_Q):
    greet = GREET_PAIRS[(idx + 2) % len(GREET_PAIRS)]
    close = CLOSE_PAIRS[(idx + 6) % len(CLOSE_PAIRS)]
    section_d.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": q},
            {"role": "assistant", "content": ans},
            {"role": "user",      "content": confirm_user},
            {"role": "assistant", "content": confirm_bot},
            {"role": "user",      "content": close[0]},
            {"role": "assistant", "content": close[1]},
        ]
    })

# ── Bölüm E: "ne alayım?" tipi sorgular — ihlal kaynağı (10 örnek) ───────────
# Bölüm E: Doğrudan sipariş — ihlal senaryolarındaki ürün/kategori kombinasyonları
NE_ALAYIM_CASES = [
    (
        "Çorbadan bir mercimek alayım.",
        f"Elbette, Mercimek Çorbası 85 TL. {BASKA_FORMS[0]}",
        "Yok teşekkürler.",
        "Peki, afiyet olsun!",
    ),
    (
        "Ana yemek olarak bir köfte alayım.",
        f"Tabii ki, Izgara Köfte 240 TL. {BASKA_FORMS[1]}",
        "Başka istemiyorum.",
        "Anladım, afiyet olsun!",
    ),
    (
        "Tatlıdan bir fırın sütlaç istiyorum.",
        f"Memnuniyetle, Fırın Sütlaç 100 TL. {BASKA_FORMS[2]}",
        "Bu kadar.",
        "Tabii, afiyet olsun!",
    ),
    (
        "İçecek olarak limonata alayım.",
        f"Elbette, Limonata 70 TL. {BASKA_FORMS[3]}",
        "Hayır teşekkürler.",
        "Peki, afiyet olsun!",
    ),
    (
        "Mercimek çorbası ve döner istiyorum.",
        f"Elbette, Mercimek Çorbası 85 TL. Et Döner 280 TL. {BASKA_FORMS[4]}",
        "Bu kadar.",
        "Anladım, afiyet olsun!",
    ),
    (
        "Bir tavuk salata alabilir miyim?",
        f"Tabii efendim, Izgara Tavuk Salata 210 TL. {BASKA_FORMS[5]}",
        "Yeterli teşekkürler.",
        "Tabii, afiyet olsun!",
    ),
    (
        "Bir şalgam suyu alayım.",
        f"Tabii ki, Şalgam Suyu 50 TL. {BASKA_FORMS[6]}",
        "Hayır bu kadar.",
        "Peki, afiyet olsun!",
    ),
    (
        "Mantar çorbası ve künefe istiyorum.",
        f"Memnuniyetle, Kremalı Mantar Çorbası 95 TL. Künefe 140 TL. {BASKA_FORMS[7]}",
        "Yok teşekkürler.",
        "Anladım, afiyet olsun!",
    ),
    (
        "İki ayran alayım.",
        f"Elbette, 2 Yayık Ayran 90 TL. {BASKA_FORMS[8]}",
        "Bu kadar yeter.",
        "Tabii, afiyet olsun!",
    ),
    (
        "Köfte ve limonata alabilir miyim?",
        f"Elbette, Izgara Köfte 240 TL. Limonata 70 TL. {BASKA_FORMS[9]}",
        "Bu kadar.",
        "Peki, afiyet olsun!",
    ),
]

section_e = []
for idx, (q, ans, confirm_user, confirm_bot) in enumerate(NE_ALAYIM_CASES):
    greet = GREET_PAIRS[(idx + 1) % len(GREET_PAIRS)]
    section_e.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": q},
            {"role": "assistant", "content": ans},
            {"role": "user",      "content": confirm_user},
            {"role": "assistant", "content": confirm_bot},
        ]
    })

# ── Birleştir ve 150 örnek al ─────────────────────────────────────────────────
all_records = section_a + section_b + section_c + section_d + section_e
print(f"A={len(section_a)}, B={len(section_b)}, C={len(section_c)}, D={len(section_d)}, E={len(section_e)}")
print(f"Toplam: {len(all_records)}")

_rng.shuffle(all_records)
records = all_records[:150]

# ── Audit doğrulaması ──────────────────────────────────────────────────────────
BASKA_EQ = ["başka", "eklemek istediğiniz", "ekleyeceğimiz", "ilaveten",
            "ekleyelim mi", "onaylıyor musunuz"]
ORDER_FOOD = ["mercimek", "mantar", "köfte", "döner", "tavuk", "sütlaç",
              "künefe", "limonata", "ayran", "şalgam", "salata"]
ORDER_TRIGGERS = ["alayım", "istiyorum", "alabilir miyim", "alabilir miyiz",
                  "getir", "ver ", "verir misiniz"]
CATS4 = ["çorba", "ana yemek", "tatlı", "içecek"]

def lower(s): return s.lower().replace("i̇","i").replace("İ","i")

greet_ok = 0
baska_ok = 0
greet_fail = []
baska_fail = []

for rec in records:
    msgs = rec["messages"]
    for i, msg in enumerate(msgs):
        if msg["role"] != "assistant": continue
        user = next((msgs[j]["content"] for j in range(i-1,-1,-1) if msgs[j]["role"]=="user"), "")
        asst = msg["content"]
        u, a = lower(user), lower(asst)

        # Karşılama-4kategori check
        greet_trigs = ["merhaba","selam","günaydın","iyi günler","iyi akşamlar","kolay gelsin","buyurun"]
        menu_trigs  = ["ne var","neler var","menü","ne yiyebilirim","ne alabilirim","sipariş vermek"]
        has_g = any(t in u for t in greet_trigs)
        has_m = any(t in u for t in menu_trigs)
        if (has_g or has_m) and not any(c in u for c in ["çorba","ana yemek","tatlı","içecek"]):
            missing = [c for c in CATS4 if c not in a]
            if missing:
                greet_fail.append({"user": user, "asst": asst, "missing": missing})
            else:
                greet_ok += 1

        # başka check
        has_order = any(t in u for t in ORDER_TRIGGERS)
        has_food  = any(t in u for t in ORDER_FOOD)
        is_specific = has_order and has_food
        if is_specific:
            if any(eq in a for eq in BASKA_EQ):
                baska_ok += 1
            else:
                # Afiyet olsun kapanışı → exempt
                if "afiyet olsun" not in a:
                    baska_fail.append({"user": user, "asst": asst})

print(f"\nKarşılama-4kategori: {greet_ok} geçer, {len(greet_fail)} başarısız")
print(f"Sipariş-başka:        {baska_ok} geçer, {len(baska_fail)} başarısız")

if greet_fail:
    print("  Karşılama hataları:")
    for f in greet_fail[:3]: print(f"    USER={f['user'][:60]}  ASST={f['asst'][:60]}")
if baska_fail:
    print("  Başka hataları:")
    for f in baska_fail[:3]: print(f"    USER={f['user'][:60]}  ASST={f['asst'][:60]}")

# ── Çıktı ──────────────────────────────────────────────────────────────────────
out_path = Path("robot_waiter_ai/datasets/processed/wbot_v3_siparis_baska.jsonl")
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"\n✓ {len(records)} kayıt → {out_path}")
