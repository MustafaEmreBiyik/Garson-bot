#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v4 — A1: Ürün açıklaması + "Getireyim mi?" (W15 / E19 fix)
Hedef: 150 yeni, kural-uyumlu örnek.
Çalıştır: python scripts/gen_aciklama.py
"""
import json
import random
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

_rng = random.Random(41)

SYSTEM = json.loads(
    open(
        "robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl",
        encoding="utf-8",
    ).readline()
)["messages"][0]["content"]

# ── Menü (kısa ad + fiyat) — gen_siparis_baska.py ile aynı ───────────────────
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

# menu.yaml'daki `description` alanından birebir (uydurma detay yok — E34)
DESCRIPTIONS = {
    "Mercimek Çorbası":       "Kırmızı mercimek, soğan ve havuçla günlük hazırlanır.",
    "Kremalı Mantar Çorbası": "Taze dağ mantarları ve kremanın eşsiz uyumuyla yapılır.",
    "Izgara Köfte":           "Kasap köfte, elma dilim patates ve köz biberle servis edilir.",
    "Et Döner":               "İnce dilimlenmiş dana eti, özel soslu lavaş ve sumaklı soğanla servis edilir.",
    "Izgara Tavuk Salata":    "Özel marineli tavuk göğsü, taze roka, domates ve zeytinyağı sosuyla hazırlanır.",
    "Fırın Sütlaç":           "Fırında üzeri kızarmış, günlük taze sütle hazırlanan geleneksel sütlaçtır.",
    "Künefe":                 "Özel Hatay peyniri ve ince tel kadayıf, şerbetle sıcak servis edilir.",
    "Yayık Ayran":            "Ev yapımı, köpüklü, soğuk servis ayrandır.",
    "Limonata":               "Taze nane yaprakları ve limonla hazırlanan soğuk limonatadır.",
    "Şalgam Suyu":            "Acılı veya acısız seçenekleriyle soğuk servis edilen şalgamdır.",
}

# Soru kalıpları — "ne var" / "neler var" gibi audit tetikleyici kalıplardan kaçınıldı
# (bkz. check_greeting_4cats: bu kalıp menü sorusu sayılır, 4 kategori zorunlu olurdu)
Q_TEMPLATES = [
    "{Short} nasıl bir şey?",
    "{Short} içeriğinde neler bulunuyor?",
    "{Short} nedir, tarif eder misiniz?",
    "{Short} nasıl bir tat, anlatır mısınız?",
    "{Short} nasıl hazırlanıyor?",
]

# Bitiş soruları — audit "Getireyim mi?" yasağı yalnızca sipariş onayı turunda geçerli
# (_is_order_turn(user) burada False, çünkü soru cümlesi ORDER_TRIGGER içermiyor)
END_FORMS = [
    "Getireyim mi?",
    "Sipariş vermek ister misiniz?",
    "Denemek ister misiniz?",
    "Ekleyeyim mi?",
    "Sipariş edeyim mi?",
]

# ── Karşılama / kapanış — gen_siparis_baska.py ile aynı, denenmiş kalıplar ───
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

CLOSE_PAIRS = [
    ("Yok teşekkürler.",     "Peki, afiyet olsun!"),
    ("Bu kadar.",            "Anladım, afiyet olsun!"),
    ("Başka istemiyorum.",   "Tabii, afiyet olsun!"),
    ("Hayır teşekkürler.",   "Peki, afiyet olsun!"),
    ("Bu kadar yeterli.",    "Anladım, afiyet olsun!"),
]

ACCEPT_USER_TEMPLATES = [
    "Evet, bir {short} alayım.",
    "Tamam, {short} alabilir miyim?",
    "Olur, bir {short} istiyorum.",
]

DECLINE_USER_TEMPLATES = [
    "Şimdilik istemiyorum, sadece merak ettim.",
    "Hayır, teşekkürler, bilgi almak istemiştim.",
    "Yok, başka zaman denerim.",
]

DECLINE_BOT_TEMPLATES = [
    "Anladım, başka bir konuda yardımcı olabilirim.",
    "Peki, başka bir şey ister misiniz?",
    "Tabii, ihtiyacınız olursa buradayım.",
]


def cap(s: str) -> str:
    return s[0].upper() + s[1:]


records = []
for item_idx, item_key in enumerate(ITEMS):
    short, price = MENU[item_key]
    desc = DESCRIPTIONS[item_key]
    for k in range(15):
        t_idx = k % len(Q_TEMPLATES)
        e_idx = (k + item_idx) % len(END_FORMS)
        question = Q_TEMPLATES[t_idx].format(Short=cap(short))
        ending = END_FORMS[e_idx]
        answer = f"{desc} {ending}"

        greet = GREET_PAIRS[(item_idx * 15 + k) % len(GREET_PAIRS)]

        is_accept = (t_idx + e_idx) % 2 == 0

        if is_accept:
            au_idx = k % len(ACCEPT_USER_TEMPLATES)
            accept_user = ACCEPT_USER_TEMPLATES[au_idx].format(short=short)
            pos = POSITIVE_WORDS[(item_idx + k) % len(POSITIVE_WORDS)]
            baska = BASKA_FORMS[(item_idx * 3 + k) % len(BASKA_FORMS)]
            accept_bot = f"{pos}, {item_key} {price} TL. {baska}"
            close = CLOSE_PAIRS[(item_idx + k) % len(CLOSE_PAIRS)]

            records.append({
                "messages": [
                    {"role": "system",    "content": SYSTEM},
                    {"role": "user",      "content": greet[0]},
                    {"role": "assistant", "content": greet[1]},
                    {"role": "user",      "content": question},
                    {"role": "assistant", "content": answer},
                    {"role": "user",      "content": accept_user},
                    {"role": "assistant", "content": accept_bot},
                    {"role": "user",      "content": close[0]},
                    {"role": "assistant", "content": close[1]},
                ]
            })
        else:
            du_idx = k % len(DECLINE_USER_TEMPLATES)
            db_idx = (k + item_idx) % len(DECLINE_BOT_TEMPLATES)
            decline_user = DECLINE_USER_TEMPLATES[du_idx]
            decline_bot = DECLINE_BOT_TEMPLATES[db_idx]

            records.append({
                "messages": [
                    {"role": "system",    "content": SYSTEM},
                    {"role": "user",      "content": greet[0]},
                    {"role": "assistant", "content": greet[1]},
                    {"role": "user",      "content": question},
                    {"role": "assistant", "content": answer},
                    {"role": "user",      "content": decline_user},
                    {"role": "assistant", "content": decline_bot},
                ]
            })

print(f"Toplam: {len(records)} kayıt (10 ürün x 15 varyant)")

_rng.shuffle(records)

out_path = Path("robot_waiter_ai/datasets/processed/wbot_v4_aciklama.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"✓ {len(records)} kayıt → {out_path}")
