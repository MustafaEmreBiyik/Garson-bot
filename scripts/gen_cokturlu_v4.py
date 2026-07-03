#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v4 — A3: Uzun Çok Turlu Konuşma
Hedef: 100 yeni, kural-uyumlu örnek.
Çalıştır: python scripts/gen_cokturlu_v4.py

gen_cotturlu.py'den (wbot_v3, 3-5 tur, yalnızca sipariş akışı) farklı olarak
daha zengin akışlar: menü sorusu + ret + sipariş, yanlış anlama + düzeltme +
devam, onay aşamasında değişiklik.

Alt tipler:
  A (35): Menü sorusu + önce ret + sonra sipariş
  B (35): Yanlış anlama → düzeltme → tekrar sipariş → devam
  C (30): Onay aşamasında değişiklik (özet toplamı HER değişiklikte sıfırdan
          yeniden hesaplanır — delta/fark biriktirme YOK)
"""
import itertools
import json
import random
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

_rng = random.Random(104)

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

Q_TEMPLATES = [
    "{Short} nasıl bir şey?",
    "{Short} içeriğinde neler bulunuyor?",
    "{Short} nedir, tarif eder misiniz?",
    "{Short} nasıl bir tat, anlatır mısınız?",
    "{Short} nasıl hazırlanıyor?",
]

END_FORMS = [
    "Getireyim mi?",
    "Sipariş vermek ister misiniz?",
    "Denemek ister misiniz?",
    "Ekleyeyim mi?",
    "Sipariş edeyim mi?",
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
SUMMARY_PREFIXES = ["Elbette, Siparişiniz:", "Tabii, Siparişiniz:", "Peki, Siparişiniz:"]
EVET_FORMS = ["Evet.", "Evet, öyle.", "Tamam.", "Doğru.", "Olur."]
AFIYET_FORMS = [
    "Afiyet olsun!", "Harika, afiyet olsun!", "Afiyet olsun, iyi günler!", "Afiyet olsun, tekrar bekleriz!",
]

CLOSE_ADD_TEMPLATES = [
    "Bir de {short}, başka istemiyorum.",
    "Ayrıca bir {short}, bu kadar yeterli.",
    "Son olarak bir {short}, yeter artık.",
    "Bir {short} daha, başka bir şey istemem.",
    "Bir de {short} alayım, o kadar yeter.",
    "Bir {short} daha olsun, teşekkürler bu kadar.",
]

# A5 ile aynı doğal düzeltme kalıbı — "yerine" zorlanmıyor
NAME_CASES = [
    ("Et Döner",               "Izgara Köfte",           "Döner dedim, köfte demedim."),
    ("Mercimek Çorbası",       "Kremalı Mantar Çorbası", "Mantar çorbası değil, mercimek çorbası istemiştim."),
    ("Limonata",               "Yayık Ayran",            "Ayran değil, limonata istiyorum."),
    ("Fırın Sütlaç",           "Künefe",                 "Künefe demedim, sütlaç dedim."),
    ("Et Döner",               "Izgara Tavuk Salata",    "Tavuk salata değil, döner istemiştim."),
    ("Yayık Ayran",            "Şalgam Suyu",            "Şalgam değil, ayran istiyorum."),
    ("Et Döner",               "Izgara Köfte",           "Köfte dedim, döner demedim."),
    ("Kremalı Mantar Çorbası", "Mercimek Çorbası",       "Mercimek değil, mantar çorbası istemiştim."),
    ("Şalgam Suyu",            "Limonata",               "Limonata demedim, şalgam suyu dedim."),
    ("Künefe",                 "Fırın Sütlaç",           "Sütlaç değil, künefe istiyorum."),
]

CANCEL_ADD_TEMPLATES = [
    "Aslında {cancel_short} iptal edin, bir de {add_short} ekleyin.",
    "Vazgeçtim, {cancel_short} çıkarın, {add_short} ekleyin.",
    "Bir düşündüm, {cancel_short} yerine {add_short} olsun.",
    "Şey, {cancel_short} istemiyorum, {add_short} ekleyin.",
]
ADD_ONLY_TEMPLATES = [
    "Bir de {add_short} ekleyin.",
    "Ayrıca bir {add_short} da alayım.",
    "Bekleyin, bir {add_short} daha ekleyin.",
]
CANCEL_ONLY_TEMPLATES = [
    "Aslında {cancel_short} iptal edin.",
    "Vazgeçtim, {cancel_short} çıkarın.",
]


def cap(s: str) -> str:
    return s[0].upper() + s[1:]


def fmt_items_list(items_qty):
    parts = [f"{qty} {item_key}" if qty > 1 else item_key for item_key, qty in items_qty]
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " ve " + parts[-1]


def total_of(items_qty):
    return sum(MENU[k][1] * q for k, q in items_qty)


def summary_turn(items_qty, idx):
    prefix = SUMMARY_PREFIXES[idx % len(SUMMARY_PREFIXES)]
    total = total_of(items_qty)  # HER ZAMAN sıfırdan yeniden hesaplanır
    return f"{prefix} {fmt_items_list(items_qty)}. Toplam {total} TL. Onaylıyor musunuz?"


def order_msg(item_key, verb_idx=0):
    short = MENU[item_key][0]
    verbs = ["alayım.", "istiyorum.", "alabilir miyim?"]
    return cap(f"bir {short} {verbs[verb_idx % len(verbs)]}")


def confirm_msg(item_key, idx):
    pos = POSITIVE_WORDS[idx % len(POSITIVE_WORDS)]
    baska = BASKA_FORMS[idx % len(BASKA_FORMS)]
    return f"{pos}, {item_key} {MENU[item_key][1]} TL. {baska}"


records = []

# ── Alt tip A: Menü sorusu + ret + sipariş (35) ──────────────────────────────
PAIRS = list(itertools.combinations(ITEMS, 2))  # 45

for idx in range(35):
    ask_item, order_item = PAIRS[idx % len(PAIRS)]
    remaining = [x for x in ITEMS if x not in (ask_item, order_item)]
    order_item2 = remaining[idx % len(remaining)]

    greet = GREET_PAIRS[idx % len(GREET_PAIRS)]

    t_idx = idx % len(Q_TEMPLATES)
    e_idx = (idx + 1) % len(END_FORMS)
    question = Q_TEMPLATES[t_idx].format(Short=cap(MENU[ask_item][0]))
    answer = f"{DESCRIPTIONS[ask_item]} {END_FORMS[e_idx]}"

    decline_user = DECLINE_USER_TEMPLATES[idx % len(DECLINE_USER_TEMPLATES)]
    decline_bot = DECLINE_BOT_TEMPLATES[idx % len(DECLINE_BOT_TEMPLATES)]

    order1 = order_msg(order_item, verb_idx=idx)
    confirm1 = confirm_msg(order_item, idx)

    close_tmpl = CLOSE_ADD_TEMPLATES[idx % len(CLOSE_ADD_TEMPLATES)]
    order2_close = cap(close_tmpl.format(short=MENU[order_item2][0]))
    summary = summary_turn([(order_item, 1), (order_item2, 1)], idx)

    evet = EVET_FORMS[idx % len(EVET_FORMS)]
    afiyet = AFIYET_FORMS[idx % len(AFIYET_FORMS)]

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": question},
            {"role": "assistant", "content": answer},
            {"role": "user",      "content": decline_user},
            {"role": "assistant", "content": decline_bot},
            {"role": "user",      "content": order1},
            {"role": "assistant", "content": confirm1},
            {"role": "user",      "content": order2_close},
            {"role": "assistant", "content": summary},
            {"role": "user",      "content": evet},
            {"role": "assistant", "content": afiyet},
        ]
    })

# ── Alt tip B: Yanlış anlama → düzeltme → tekrar sipariş → devam (35) ───────
for idx in range(35):
    correct, wrong, correction_msg = NAME_CASES[idx % len(NAME_CASES)]
    remaining = [x for x in ITEMS if x not in (correct, wrong)]
    item2 = remaining[idx % len(remaining)]
    item3 = remaining[(idx + 1) % len(remaining)]
    if item3 == item2:
        item3 = remaining[(idx + 2) % len(remaining)]

    greet = GREET_PAIRS[(idx + 2) % len(GREET_PAIRS)]

    order1 = order_msg(correct, verb_idx=idx)
    wrong_confirm = confirm_msg(wrong, idx)
    fix_reply = (f"Anladım, {wrong} çıkarılıyor, {correct} {MENU[correct][1]} TL ekleniyor. "
                 f"{BASKA_FORMS[(idx + 1) % len(BASKA_FORMS)]}")

    order2 = order_msg(item2, verb_idx=idx + 1)
    confirm2 = confirm_msg(item2, idx + 2)

    close_tmpl = CLOSE_ADD_TEMPLATES[(idx + 2) % len(CLOSE_ADD_TEMPLATES)]
    order3_close = cap(close_tmpl.format(short=MENU[item3][0]))
    summary = summary_turn([(correct, 1), (item2, 1), (item3, 1)], idx + 1)

    evet = EVET_FORMS[(idx + 1) % len(EVET_FORMS)]
    afiyet = AFIYET_FORMS[(idx + 1) % len(AFIYET_FORMS)]

    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": order1},
            {"role": "assistant", "content": wrong_confirm},
            {"role": "user",      "content": correction_msg},
            {"role": "assistant", "content": fix_reply},
            {"role": "user",      "content": order2},
            {"role": "assistant", "content": confirm2},
            {"role": "user",      "content": order3_close},
            {"role": "assistant", "content": summary},
            {"role": "user",      "content": evet},
            {"role": "assistant", "content": afiyet},
        ]
    })

# ── Alt tip C: Onay aşamasında değişiklik (30) — toplam HER zaman sıfırdan ──
for idx in range(30):
    i1, i2 = PAIRS[(idx * 3) % len(PAIRS)]
    remaining = [x for x in ITEMS if x not in (i1, i2)]
    i3 = remaining[idx % len(remaining)]

    greet = GREET_PAIRS[(idx + 6) % len(GREET_PAIRS)]
    order_both = cap(f"bir {MENU[i1][0]} bir {MENU[i2][0]} alayım.")
    current_items = [(i1, 1), (i2, 1)]
    summary1 = summary_turn(current_items, idx)

    change_type = idx % 3  # 0=iptal+ekle, 1=sadece ekle, 2=sadece iptal
    if change_type == 0:
        tmpl = CANCEL_ADD_TEMPLATES[idx % len(CANCEL_ADD_TEMPLATES)]
        change_user = tmpl.format(cancel_short=MENU[i1][0], add_short=MENU[i3][0])
        current_items = [(i2, 1), (i3, 1)]
    elif change_type == 1:
        tmpl = ADD_ONLY_TEMPLATES[idx % len(ADD_ONLY_TEMPLATES)]
        change_user = tmpl.format(add_short=MENU[i3][0])
        current_items = [(i1, 1), (i2, 1), (i3, 1)]
    else:
        tmpl = CANCEL_ONLY_TEMPLATES[idx % len(CANCEL_ONLY_TEMPLATES)]
        change_user = cap(tmpl.format(cancel_short=MENU[i1][0]))
        current_items = [(i2, 1)]
    summary2 = summary_turn(current_items, idx + 1)  # sıfırdan yeniden hesap

    messages = [
        {"role": "system",    "content": SYSTEM},
        {"role": "user",      "content": greet[0]},
        {"role": "assistant", "content": greet[1]},
        {"role": "user",      "content": order_both},
        {"role": "assistant", "content": summary1},
        {"role": "user",      "content": change_user},
        {"role": "assistant", "content": summary2},
    ]

    # 10 kayıtta ikinci bir değişiklik daha uygula (hata birikmediğini göstermek için)
    if idx < 10:
        remaining2 = [x for x in ITEMS if x not in [k for k, _ in current_items]]
        i4 = remaining2[idx % len(remaining2)]
        tmpl2 = ADD_ONLY_TEMPLATES[(idx + 1) % len(ADD_ONLY_TEMPLATES)]
        change_user2 = tmpl2.format(add_short=MENU[i4][0])
        current_items = current_items + [(i4, 1)]
        summary3 = summary_turn(current_items, idx + 2)  # yine sıfırdan
        messages += [
            {"role": "user",      "content": change_user2},
            {"role": "assistant", "content": summary3},
        ]

    evet = EVET_FORMS[(idx + 2) % len(EVET_FORMS)]
    afiyet = AFIYET_FORMS[(idx + 2) % len(AFIYET_FORMS)]
    messages += [
        {"role": "user",      "content": evet},
        {"role": "assistant", "content": afiyet},
    ]

    records.append({"messages": messages})

print(f"Toplam: {len(records)} kayıt (A=35, B=35, C=30)")

_rng.shuffle(records)

out_path = Path("robot_waiter_ai/datasets/processed/wbot_v4_cokturlu.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"✓ {len(records)} kayıt → {out_path}")
