#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v5 (C paketi) — Madde 1: Modifikasyon, Sipariş SONRASI (S34/V02)
Hedef: 20 yeni, kural-uyumlu örnek.
Çalıştır: python scripts/gen_modifikasyon_sonrasi.py

S33/V01'den (gen_modifikasyon.py) farkı: orada modifikasyon sipariş
cümlesiyle AYNI mesajda ("bir şalgam alayım, acılı olsun"); burada sipariş
verilip fiyatla onaylandıktan SONRA, AYRI bir kullanıcı turunda geliyor
("az önce aldığım döneri soğansız yapar mısınız?"). Beklenen davranış:
kabul + güncellenmiş onay tekrarı — yeni fiyat YOK (ürün aynı, yalnızca
modifikasyon notu güncellenir). "Getireyim mi?" / "onaylandı/kaydedildi"
yasağı burada da geçerli. Modifikasyonlar menü verisiyle çelişmeyen genel
mutfak talepleri (şalgam suyu için acılı/acısız menu.yaml'da zaten var).
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

# Modifikasyon kabul kalıpları — fiyat YOK, yalnızca güncellenmiş onay + başka sorusu.
# {item} = kanonik menü adı, {mod} = modifikasyon sıfatı, {baska} = başka sorusu.
MOD_REPLY_FORMS = [
    "Tabii, {item} {mod} olacak şekilde güncellendi. {baska}",
    "Elbette, {item} siparişinizi {mod} olarak not ettim. {baska}",
    "Memnuniyetle, {item} {mod} hazırlanacak. {baska}",
    "Tabii efendim, {item} {mod} olacak şekilde mutfağa ilettim. {baska}",
]

# (ürün, sipariş_kısa_ad, sipariş_fiili, modifikasyon_sıfatı, ayrı_turdaki_modifikasyon_cümlesi)
CASES = [
    ("Et Döner",               "et döner",          "alayım",          "soğansız",
     "Az önce aldığım et döneri soğansız yapar mısınız?"),
    ("Et Döner",               "et döner",          "istiyorum",       "bol soslu",
     "Bir şey diyeceğim, et döner bol soslu olsun."),
    ("Izgara Köfte",           "ızgara köfte",      "alayım",          "az pişmiş",
     "Pardon, köfteyi az pişmiş yapabilir misiniz?"),
    ("Izgara Köfte",           "ızgara köfte",      "alabilir miyim",  "soğansız",
     "Demin söylediğim köfte soğansız gelsin."),
    ("Şalgam Suyu",            "şalgam suyu",       "alayım",          "acılı",
     "Şalgam suyunu acılı yapar mısınız?"),
    ("Şalgam Suyu",            "şalgam suyu",       "istiyorum",       "acısız",
     "Az önce söylediğim şalgam suyu acısız olsun."),
    ("Mercimek Çorbası",       "mercimek çorbası",  "alayım",          "az tuzlu",
     "Pardon, mercimek çorbasını az tuzlu yapabilir misiniz?"),
    ("Kremalı Mantar Çorbası", "mantar çorbası",    "istiyorum",       "az tuzlu",
     "Demin aldığım mantar çorbası az tuzlu olsun lütfen."),
    ("Limonata",               "limonata",          "alayım",          "az şekerli",
     "Limonatayı az şekerli yapar mısınız?"),
    ("Limonata",               "limonata",          "alabilir miyim",  "buzsuz",
     "Bir şey soracaktım, limonatam buzsuz olabilir mi?"),
    ("Yayık Ayran",            "ayran",             "alayım",          "buzlu",
     "Az önce söylediğim ayran buzlu gelsin."),
    ("Yayık Ayran",            "ayran",             "istiyorum",       "az tuzlu",
     "Ayranı az tuzlu yapabilir misiniz?"),
    ("Künefe",                 "künefe",            "alayım",          "az şerbetli",
     "Pardon, künefeyi az şerbetli yapar mısınız?"),
    ("Künefe",                 "künefe",            "istiyorum",       "bol şerbetli",
     "Demin söylediğim künefe bol şerbetli olsun."),
    ("Fırın Sütlaç",           "fırın sütlaç",      "alayım",          "az şekerli",
     "Sütlacı az şekerli yapabilir misiniz?"),
    ("Fırın Sütlaç",           "fırın sütlaç",      "alabilir miyim",  "soğuk servis",
     "Az önce aldığım sütlaç soğuk gelsin lütfen."),
    ("Izgara Tavuk Salata",    "tavuk salata",      "alayım",          "sossuz",
     "Tavuk salatayı sossuz yapar mısınız?"),
    ("Izgara Tavuk Salata",    "tavuk salata",      "istiyorum",       "bol soslu",
     "Az önce söylediğim tavuk salata bol soslu olsun."),
    ("Et Döner",               "et döner",          "alabilir miyim",  "az soslu",
     "Bir ricam olacak, et döner az soslu olabilir mi?"),
    ("Izgara Köfte",           "ızgara köfte",      "istiyorum",       "bol soslu",
     "Demin aldığım köfte bol soslu gelsin."),
]

records = []
for idx, (item, short, verb, mod, user_mod) in enumerate(CASES):
    greet = GREET_PAIRS[idx % len(GREET_PAIRS)]
    user_order = f"Bir {short} alayım." if verb == "alayım" else \
                 f"Bir {short} istiyorum." if verb == "istiyorum" else \
                 f"Bir {short} alabilir miyim?"
    pos = POSITIVE_WORDS[idx % len(POSITIVE_WORDS)]
    price = MENU[item][1]
    bot_confirm = f"{pos}, {item} {price} TL. {BASKA_FORMS[idx % len(BASKA_FORMS)]}"
    bot_mod = MOD_REPLY_FORMS[idx % len(MOD_REPLY_FORMS)].format(
        item=item, mod=mod, baska=BASKA_FORMS[(idx + 3) % len(BASKA_FORMS)]
    )

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": user_order},
            {"role": "assistant", "content": bot_confirm},
            {"role": "user",      "content": user_mod},
            {"role": "assistant", "content": bot_mod},
        ]
    })

print(f"Sistem promptu: {len(SYSTEM)} karakter")
print(f"Toplam: {len(records)} kayıt")

out_path = Path("robot_waiter_ai/datasets/processed/wbot_c_modifikasyon_sonrasi.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"✓ {len(records)} kayıt → {out_path}")
