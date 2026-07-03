#!/usr/bin/env python3
"""gen_hesap.py — 100 Hesap varyasyonları örneği üretir.

Sections:
  A (30): Tek ürün × 10 items × 3 bill styles
  B (40): İki ürün × 20 pairs × 2 bill styles
  C (20): Üç ürün × 10 triples × 2 bill styles
  D  (5): Adetli siparişler (2×, 3×)
  E  (5): Doğrudan hesap (ara "yeterli" turu yok)
Total: 100
"""

import json
from pathlib import Path

OUT = Path("robot_waiter_ai/datasets/processed/wbot_v3_hesap.jsonl")

# Kanonik sistem promptu — wbot_finetune_v1.jsonl'in ilk kaydından okunur
# (gen_karsilama.py / gen_siparis_baska.py ile aynı desen).
SYSTEM = json.loads(
    open(
        "robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl",
        encoding="utf-8",
    ).readline()
)["messages"][0]["content"]

MENU = {
    "Mercimek Çorbası": 85,
    "Kremalı Mantar Çorbası": 95,
    "Izgara Köfte": 240,
    "Et Döner": 280,
    "Izgara Tavuk Salata": 210,
    "Fırın Sütlaç": 100,
    "Künefe": 140,
    "Yayık Ayran": 45,
    "Limonata": 70,
    "Şalgam Suyu": 50,
}

BOT_GREETS = [
    "Hoş geldiniz! Menümüzde çorba, ana yemek, tatlı ve içecek çeşitlerimiz mevcuttur.",
    "Merhaba, hoş geldiniz! Çorba, ana yemek, tatlı ve içeceklerimizle hizmetinizdeyiz.",
    "Hoş geldiniz! Çorba, ana yemek, tatlı ve içecek seçeneklerimiz sizi bekliyor.",
    "Merhaba! Menümüzde çorba, ana yemek, tatlı ve içecekler dahil geniş seçenekler mevcut.",
    "Hoş geldiniz, buyurun! Çorba, ana yemek, tatlı ve içecek kategorilerinde hizmetinizdeyiz.",
    "İyi günler! Çorba, ana yemek, tatlı ve içecek çeşitlerimizle buyurun.",
    "Merhaba! Menümüzde çorba, ana yemek, tatlı ve içecek olmak üzere zengin seçenekler var.",
    "Hoş geldiniz! Çorba, ana yemek, tatlı ve içeceklerimize göz atabilirsiniz.",
    "Buyurun, hoş geldiniz! Menümüzde çorba, ana yemek, tatlı ve içecek kategorileri yer alıyor.",
    "Merhaba, hoş geldiniz! Çorba, ana yemek, tatlı ve içecek dahil geniş menümüze buyurun.",
]

USER_GREETS = [
    "Merhaba.",
    "İyi günler.",
    "Selam.",
    "Merhaba, masaya geçtim.",
    "Buyurun.",
    "Merhaba, ne var menünüzde?",
    "Selam, neler var?",
    "Merhaba, masaya oturduk.",
    "İyi akşamlar.",
    "Günaydın.",
]

ORDER_MSGS = {
    "Mercimek Çorbası": [
        "Mercimek çorbası istiyorum.",
        "Bir mercimek çorbası alayım.",
        "Mercimek çorbası alabilir miyim?",
        "Bana mercimek çorbası getir.",
        "Mercimek çorbası sipariş etmek istiyorum.",
    ],
    "Kremalı Mantar Çorbası": [
        "Kremalı mantar çorbası istiyorum.",
        "Bir mantar çorbası alayım.",
        "Mantar çorbası alabilir miyim?",
        "Kremalı mantar çorbası getir lütfen.",
        "Mantar çorbası sipariş ediyorum.",
    ],
    "Izgara Köfte": [
        "Izgara köfte istiyorum.",
        "Bir ızgara köfte alayım.",
        "Köfte alabilir miyim?",
        "Bana köfte getir.",
        "Izgara köfte sipariş etmek istiyorum.",
    ],
    "Et Döner": [
        "Et döner istiyorum.",
        "Bir et döner alayım.",
        "Döner alabilir miyim?",
        "Et döner getir lütfen.",
        "Döner sipariş ediyorum.",
    ],
    "Izgara Tavuk Salata": [
        "Izgara tavuk salata istiyorum.",
        "Tavuk salata alayım.",
        "Tavuk salata alabilir miyim?",
        "Izgara tavuk salata getir.",
        "Tavuk salata sipariş etmek istiyorum.",
    ],
    "Fırın Sütlaç": [
        "Fırın sütlaç istiyorum.",
        "Bir sütlaç alayım.",
        "Sütlaç alabilir miyim?",
        "Sütlaç getir lütfen.",
        "Sütlaç sipariş ediyorum.",
    ],
    "Künefe": [
        "Künefe istiyorum.",
        "Bir künefe alayım.",
        "Künefe alabilir miyim?",
        "Bana künefe getir.",
        "Künefe sipariş etmek istiyorum.",
    ],
    "Yayık Ayran": [
        "Yayık ayran istiyorum.",
        "Bir ayran alayım.",
        "Ayran alabilir miyim?",
        "Ayran getir lütfen.",
        "Ayran sipariş ediyorum.",
    ],
    "Limonata": [
        "Limonata istiyorum.",
        "Bir limonata alayım.",
        "Limonata alabilir miyim?",
        "Limonata getir lütfen.",
        "Limonata sipariş ediyorum.",
    ],
    "Şalgam Suyu": [
        "Şalgam suyu istiyorum.",
        "Bir şalgam alayım.",
        "Şalgam alabilir miyim?",
        "Şalgam suyu getir lütfen.",
        "Şalgam sipariş ediyorum.",
    ],
}

CONFIRMS = ["Elbette", "Tabii ki", "Tabii efendim", "Memnuniyetle", "Harika seçim"]

# Tüm formlar _BASIT_EQUIVALENTS ile eşleşiyor:
# "başka", "eklemek istediğiniz", "ekleyeceğimiz", "ilaveten"
BASKA_FORMS = [
    "Başka bir şey alır mısınız?",
    "Başka ne arzu edersiniz?",
    "Başka bir şey ister misiniz?",
    "Başka bir isteğiniz var mı?",
    "Eklemek istediğiniz bir şey var mı?",
    "Ekleyeceğimiz bir şey var mı?",
    "İlaveten bir arzunuz olur mu?",
    "Başka arzunuz var mı?",
    "Başka bir şey daha alır mısınız?",
]

NO_MORE = [
    "Hayır, teşekkürler.",
    "Yeterli, teşekkürler.",
    "Bu kadar yeterli.",
    "Hayır, hepsi bu.",
    "Bu kadardı.",
    "Şimdilik bu kadar.",
]

ANLASILDI = [
    "Anlaşıldı, siparişinizi iletiyorum.",
    "Tamam efendim, siparişiniz alındı.",
    "Peki efendim, siparişinizi bildiriyorum.",
    "Anlaşıldı.",
    "Peki, siparişinizi hazırlıyorum.",
]

# Tüm ifadeler _BILL_TRIGGERS'dan en az biriyle eşleşiyor
BILL_REQUESTS = [
    "Hesabı alabilir miyim?",
    "Hesap lütfen.",
    "Ödeyeyim.",
    "Ödemek istiyorum.",
    "Hesabımızı alabilir miyiz?",
    "Toplam ne kadar?",
    "Ödeme yapmak istiyorum.",
    "Ödeyelim.",
    "Çek gelsin lütfen.",
    "Adisyonu getirir misiniz?",
    "Hesabı kapatmak istiyorum.",
    "Hesabı kapatabilir miyiz?",
]

CLOSINGS = [
    "Afiyet olsun!",
    "Afiyet olsun, tekrar bekleriz.",
    "İyi günler dileriz.",
    "Afiyet olsun, görüşürüz.",
    "Tekrar bekleriz, iyi günler.",
    "Uğradığınız için teşekkürler, iyi günler.",
    "Afiyet olsun, sağlıklı günler dileriz.",
]


def _m(role: str, content: str) -> dict:
    return {"role": role, "content": content}


def _confirm(item: str, price: int, baska: str, pos: str) -> str:
    return f"{pos}, {item} {price} TL. {baska}"


def _bill(total: int, closing: str) -> str:
    return f"Toplam {total} TL. {closing}"


def _rec(*turns) -> dict:
    return {"messages": list(turns)}


def main() -> None:
    records: list[dict] = []
    items = list(MENU.keys())

    # ── Section A: Tek ürün (10 × 3 = 30) ─────────────────────────────────────
    for i_idx, item in enumerate(items):
        price = MENU[item]
        for b_idx in range(3):
            n = len(records)
            records.append(_rec(
                _m("system",    SYSTEM),
                _m("user",      USER_GREETS[n % len(USER_GREETS)]),
                _m("assistant", BOT_GREETS[n % len(BOT_GREETS)]),
                _m("user",      ORDER_MSGS[item][b_idx % len(ORDER_MSGS[item])]),
                _m("assistant", _confirm(item, price,
                                         BASKA_FORMS[n % len(BASKA_FORMS)],
                                         CONFIRMS[n % len(CONFIRMS)])),
                _m("user",      NO_MORE[n % len(NO_MORE)]),
                _m("assistant", ANLASILDI[n % len(ANLASILDI)]),
                _m("user",      BILL_REQUESTS[n % len(BILL_REQUESTS)]),
                _m("assistant", _bill(price, CLOSINGS[n % len(CLOSINGS)])),
            ))

    # ── Section B: İki ürün (20 × 2 = 40) ─────────────────────────────────────
    PAIRS = [
        ("Mercimek Çorbası",      "Izgara Köfte"),
        ("Mercimek Çorbası",      "Et Döner"),
        ("Mercimek Çorbası",      "Izgara Tavuk Salata"),
        ("Kremalı Mantar Çorbası","Izgara Köfte"),
        ("Kremalı Mantar Çorbası","Et Döner"),
        ("Kremalı Mantar Çorbası","Izgara Tavuk Salata"),
        ("Izgara Köfte",          "Fırın Sütlaç"),
        ("Izgara Köfte",          "Künefe"),
        ("Izgara Köfte",          "Yayık Ayran"),
        ("Et Döner",              "Fırın Sütlaç"),
        ("Et Döner",              "Künefe"),
        ("Et Döner",              "Limonata"),
        ("Izgara Tavuk Salata",   "Fırın Sütlaç"),
        ("Izgara Tavuk Salata",   "Yayık Ayran"),
        ("Izgara Tavuk Salata",   "Şalgam Suyu"),
        ("Fırın Sütlaç",          "Yayık Ayran"),
        ("Fırın Sütlaç",          "Limonata"),
        ("Künefe",                "Limonata"),
        ("Künefe",                "Yayık Ayran"),
        ("Yayık Ayran",           "Şalgam Suyu"),
    ]
    for p_idx, (item1, item2) in enumerate(PAIRS):
        p1, p2 = MENU[item1], MENU[item2]
        for b_idx in range(2):
            n = len(records)
            records.append(_rec(
                _m("system",    SYSTEM),
                _m("user",      USER_GREETS[n % len(USER_GREETS)]),
                _m("assistant", BOT_GREETS[n % len(BOT_GREETS)]),
                _m("user",      ORDER_MSGS[item1][b_idx % len(ORDER_MSGS[item1])]),
                _m("assistant", _confirm(item1, p1,
                                         BASKA_FORMS[n % len(BASKA_FORMS)],
                                         CONFIRMS[n % len(CONFIRMS)])),
                _m("user",      ORDER_MSGS[item2][(b_idx + 1) % len(ORDER_MSGS[item2])]),
                _m("assistant", _confirm(item2, p2,
                                         BASKA_FORMS[(n + 2) % len(BASKA_FORMS)],
                                         CONFIRMS[(n + 1) % len(CONFIRMS)])),
                _m("user",      NO_MORE[n % len(NO_MORE)]),
                _m("assistant", ANLASILDI[n % len(ANLASILDI)]),
                _m("user",      BILL_REQUESTS[n % len(BILL_REQUESTS)]),
                _m("assistant", _bill(p1 + p2, CLOSINGS[n % len(CLOSINGS)])),
            ))

    # ── Section C: Üç ürün (10 × 2 = 20) ──────────────────────────────────────
    TRIPLES = [
        ("Mercimek Çorbası",       "Izgara Köfte",        "Yayık Ayran"),
        ("Kremalı Mantar Çorbası", "Et Döner",            "Limonata"),
        ("Mercimek Çorbası",       "Izgara Tavuk Salata", "Fırın Sütlaç"),
        ("Kremalı Mantar Çorbası", "Izgara Köfte",        "Künefe"),
        ("Mercimek Çorbası",       "Et Döner",            "Şalgam Suyu"),
        ("Kremalı Mantar Çorbası", "Izgara Tavuk Salata", "Limonata"),
        ("Izgara Köfte",           "Fırın Sütlaç",        "Şalgam Suyu"),
        ("Et Döner",               "Künefe",              "Yayık Ayran"),
        ("Izgara Tavuk Salata",    "Fırın Sütlaç",        "Limonata"),
        ("Mercimek Çorbası",       "Izgara Köfte",        "Künefe"),
    ]
    for t_idx, (item1, item2, item3) in enumerate(TRIPLES):
        p1, p2, p3 = MENU[item1], MENU[item2], MENU[item3]
        for b_idx in range(2):
            n = len(records)
            records.append(_rec(
                _m("system",    SYSTEM),
                _m("user",      USER_GREETS[n % len(USER_GREETS)]),
                _m("assistant", BOT_GREETS[n % len(BOT_GREETS)]),
                _m("user",      ORDER_MSGS[item1][0]),
                _m("assistant", _confirm(item1, p1,
                                         BASKA_FORMS[n % len(BASKA_FORMS)],
                                         CONFIRMS[n % len(CONFIRMS)])),
                _m("user",      ORDER_MSGS[item2][1 % len(ORDER_MSGS[item2])]),
                _m("assistant", _confirm(item2, p2,
                                         BASKA_FORMS[(n + 1) % len(BASKA_FORMS)],
                                         CONFIRMS[(n + 1) % len(CONFIRMS)])),
                _m("user",      ORDER_MSGS[item3][2 % len(ORDER_MSGS[item3])]),
                _m("assistant", _confirm(item3, p3,
                                         BASKA_FORMS[(n + 2) % len(BASKA_FORMS)],
                                         CONFIRMS[(n + 2) % len(CONFIRMS)])),
                _m("user",      NO_MORE[n % len(NO_MORE)]),
                _m("assistant", ANLASILDI[n % len(ANLASILDI)]),
                _m("user",      BILL_REQUESTS[n % len(BILL_REQUESTS)]),
                _m("assistant", _bill(p1 + p2 + p3, CLOSINGS[n % len(CLOSINGS)])),
            ))

    # ── Section D: Adetli siparişler (5) ───────────────────────────────────────
    COUNT_ITEMS = [
        (2, "Mercimek Çorbası",   85,  "İki mercimek çorbası alayım.",    "2 Mercimek Çorbası"),
        (2, "Izgara Köfte",       240, "İki ızgara köfte istiyorum.",      "2 Izgara Köfte"),
        (3, "Yayık Ayran",        45,  "Üç ayran alayım.",                 "3 Yayık Ayran"),
        (2, "Künefe",             140, "İki künefe istiyorum.",             "2 Künefe"),
        (2, "Limonata",           70,  "İki limonata alabilir miyim?",     "2 Limonata"),
    ]
    for count, item, upr, order_user, label in COUNT_ITEMS:
        total = count * upr
        n = len(records)
        records.append(_rec(
            _m("system",    SYSTEM),
            _m("user",      USER_GREETS[n % len(USER_GREETS)]),
            _m("assistant", BOT_GREETS[n % len(BOT_GREETS)]),
            _m("user",      order_user),
            _m("assistant", f"Elbette, {label} {total} TL. "
                            f"{BASKA_FORMS[n % len(BASKA_FORMS)]}"),
            _m("user",      NO_MORE[n % len(NO_MORE)]),
            _m("assistant", ANLASILDI[n % len(ANLASILDI)]),
            _m("user",      BILL_REQUESTS[n % len(BILL_REQUESTS)]),
            _m("assistant", _bill(total, CLOSINGS[n % len(CLOSINGS)])),
        ))

    # ── Section E: Doğrudan hesap, ara "hayır" turu yok (5) ────────────────────
    DIRECT = [
        ("Et Döner",               "Limonata"),
        ("Izgara Köfte",           "Şalgam Suyu"),
        ("Izgara Tavuk Salata",    "Yayık Ayran"),
        ("Kremalı Mantar Çorbası", "Fırın Sütlaç"),
        ("Mercimek Çorbası",       "Künefe"),
    ]
    for item1, item2 in DIRECT:
        p1, p2 = MENU[item1], MENU[item2]
        n = len(records)
        records.append(_rec(
            _m("system",    SYSTEM),
            _m("user",      USER_GREETS[n % len(USER_GREETS)]),
            _m("assistant", BOT_GREETS[n % len(BOT_GREETS)]),
            _m("user",      ORDER_MSGS[item1][2 % len(ORDER_MSGS[item1])]),
            _m("assistant", _confirm(item1, p1,
                                     BASKA_FORMS[n % len(BASKA_FORMS)],
                                     CONFIRMS[n % len(CONFIRMS)])),
            _m("user",      ORDER_MSGS[item2][3 % len(ORDER_MSGS[item2])]),
            _m("assistant", _confirm(item2, p2,
                                     BASKA_FORMS[(n + 2) % len(BASKA_FORMS)],
                                     CONFIRMS[(n + 1) % len(CONFIRMS)])),
            _m("user",      BILL_REQUESTS[n % len(BILL_REQUESTS)]),
            _m("assistant", _bill(p1 + p2, CLOSINGS[n % len(CLOSINGS)])),
        ))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Yazıldı: {OUT}  ({len(records)} kayıt)")


if __name__ == "__main__":
    main()
