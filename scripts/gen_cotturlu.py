#!/usr/bin/env python3
"""gen_cotturlu.py — 150 Çok turlu konuşma örneği üretir.

Sections:
  A (60): 4 ürün sıralı sipariş + hesap  — 30 dörtlü × 2 stil
  B (50): 3 ürün + ara ürün sorusu + hesap — 25 üçlü × 2 stil
  C (40): 5 ürün sıralı sipariş + hesap  — 20 beşli × 2 stil
Total: 150
"""

import json
from pathlib import Path

OUT = Path("robot_waiter_ai/datasets/processed/wbot_v3_cotturlu.jsonl")

SYSTEM = (
    "Sen bir restoran garson robotusun. Türkçe konuşuyorsun. "
    "Menüde şunlar var: Mercimek Çorbası 85 TL, Kremalı Mantar Çorbası 95 TL, "
    "Izgara Köfte 240 TL, Et Döner 280 TL, Izgara Tavuk Salata 210 TL, "
    "Fırın Sütlaç 100 TL, Künefe 140 TL, Yayık Ayran 45 TL, Limonata 70 TL, "
    "Şalgam Suyu 50 TL."
)

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

# Tüm formlar _BASIT_EQUIVALENTS ile eşleşiyor
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

# Ürün soruları — ORDER_TRIGGER / GREETING_TRIGGER / BILL_TRIGGER içermiyor
MID_QA = [
    ("Sütlaç büyük porsiyonlu mu?",
     "Evet, doyurucu bir porsiyon sunuyoruz."),
    ("Künefe sıcak servis ediliyor mu?",
     "Evet, sıcak servis edilmektedir."),
    ("Döner pirinçle mi geliyor?",
     "Döner yanında pilav ile servistedir."),
    ("Köfte ızgarada mı hazırlanıyor?",
     "Evet, taze ızgara köftedir."),
    ("Tavuk salata hangi malzemeleri içeriyor?",
     "Marul, domates, salatalık ve ızgara tavuk içermektedir."),
    ("Ayran büyük boy mu?",
     "Standart boy bardakta servis edilmektedir."),
    ("Limonata taze mi sıkılıyor?",
     "Evet, taze limonla hazırlanmaktadır."),
    ("Mercimek çorbası kremalı mı?",
     "Mercimek çorbasımız krema içermemektedir."),
    ("Şalgam suyu çok acı mı?",
     "Orta yoğunlukta, tadı dengelidir."),
    ("Mantar çorbası sütlü mü?",
     "Kremalı mantar çorbasında krema kullanılmaktadır."),
    ("Sütlaç soğuk mu servis ediliyor?",
     "Fırın sütlaç ılık servis edilmektedir."),
    ("Künefe tek kişilik mi?",
     "Evet, tek kişilik porsiyon olarak servistedir."),
    ("Salata sos ile mi geliyor?",
     "Zeytinyağı ve limon sosuyla servis edilmektedir."),
    ("Köfte büyük porsiyonlu mu?",
     "Doyurucu bir porsiyondur."),
    ("Döner et mi?",
     "Evet, menümüzdeki döner et döneridir."),
]


def _m(role: str, content: str) -> dict:
    return {"role": role, "content": content}


def _confirm(item: str, price: int, baska: str, pos: str) -> str:
    return f"{pos}, {item} {price} TL. {baska}"


def _bill(total: int, closing: str) -> str:
    return f"Toplam {total} TL. {closing}"


def main() -> None:
    records: list[dict] = []

    # ── Section A: 4-item orders (30 × 2 = 60) ─────────────────────────────────
    # 30 dörtlü: 2 çorba × 3 ana yemek × 2 tatlı × 3 içecek = 36 kombinasyondan 30 seçim
    QUADS = [
        ("Mercimek Çorbası",       "Izgara Köfte",        "Fırın Sütlaç",  "Yayık Ayran"),
        ("Mercimek Çorbası",       "Izgara Köfte",        "Künefe",         "Limonata"),
        ("Mercimek Çorbası",       "Et Döner",            "Fırın Sütlaç",  "Şalgam Suyu"),
        ("Mercimek Çorbası",       "Et Döner",            "Künefe",         "Yayık Ayran"),
        ("Mercimek Çorbası",       "Izgara Tavuk Salata", "Fırın Sütlaç",  "Limonata"),
        ("Mercimek Çorbası",       "Izgara Tavuk Salata", "Künefe",         "Şalgam Suyu"),
        ("Kremalı Mantar Çorbası", "Izgara Köfte",        "Fırın Sütlaç",  "Limonata"),
        ("Kremalı Mantar Çorbası", "Izgara Köfte",        "Künefe",         "Şalgam Suyu"),
        ("Kremalı Mantar Çorbası", "Et Döner",            "Fırın Sütlaç",  "Yayık Ayran"),
        ("Kremalı Mantar Çorbası", "Et Döner",            "Künefe",         "Limonata"),
        ("Kremalı Mantar Çorbası", "Izgara Tavuk Salata", "Fırın Sütlaç",  "Şalgam Suyu"),
        ("Kremalı Mantar Çorbası", "Izgara Tavuk Salata", "Künefe",         "Yayık Ayran"),
        ("Mercimek Çorbası",       "Izgara Köfte",        "Fırın Sütlaç",  "Şalgam Suyu"),
        ("Mercimek Çorbası",       "Izgara Köfte",        "Künefe",         "Yayık Ayran"),
        ("Mercimek Çorbası",       "Et Döner",            "Fırın Sütlaç",  "Limonata"),
        ("Kremalı Mantar Çorbası", "Izgara Köfte",        "Fırın Sütlaç",  "Yayık Ayran"),
        ("Kremalı Mantar Çorbası", "Et Döner",            "Fırın Sütlaç",  "Limonata"),
        ("Kremalı Mantar Çorbası", "Izgara Tavuk Salata", "Fırın Sütlaç",  "Limonata"),
        ("Mercimek Çorbası",       "Izgara Tavuk Salata", "Fırın Sütlaç",  "Yayık Ayran"),
        ("Mercimek Çorbası",       "Izgara Tavuk Salata", "Künefe",         "Limonata"),
        ("Kremalı Mantar Çorbası", "Izgara Köfte",        "Künefe",         "Limonata"),
        ("Kremalı Mantar Çorbası", "Et Döner",            "Künefe",         "Yayık Ayran"),
        ("Mercimek Çorbası",       "Izgara Köfte",        "Fırın Sütlaç",  "Limonata"),
        ("Kremalı Mantar Çorbası", "Et Döner",            "Fırın Sütlaç",  "Şalgam Suyu"),
        ("Mercimek Çorbası",       "Et Döner",            "Künefe",         "Limonata"),
        ("Kremalı Mantar Çorbası", "Izgara Tavuk Salata", "Künefe",         "Şalgam Suyu"),
        ("Mercimek Çorbası",       "Izgara Köfte",        "Künefe",         "Şalgam Suyu"),
        ("Kremalı Mantar Çorbası", "Izgara Köfte",        "Fırın Sütlaç",  "Şalgam Suyu"),
        ("Mercimek Çorbası",       "Et Döner",            "Fırın Sütlaç",  "Yayık Ayran"),
        ("Kremalı Mantar Çorbası", "Izgara Tavuk Salata", "Künefe",         "Limonata"),
    ]
    for items4 in QUADS:
        i1, i2, i3, i4 = items4
        p1, p2, p3, p4 = MENU[i1], MENU[i2], MENU[i3], MENU[i4]
        total = p1 + p2 + p3 + p4
        for b_idx in range(2):
            n = len(records)
            records.append({"messages": [
                _m("system",    SYSTEM),
                _m("user",      USER_GREETS[n % len(USER_GREETS)]),
                _m("assistant", BOT_GREETS[n % len(BOT_GREETS)]),
                _m("user",      ORDER_MSGS[i1][0]),
                _m("assistant", _confirm(i1, p1,
                                         BASKA_FORMS[n % len(BASKA_FORMS)],
                                         CONFIRMS[n % len(CONFIRMS)])),
                _m("user",      ORDER_MSGS[i2][1 % len(ORDER_MSGS[i2])]),
                _m("assistant", _confirm(i2, p2,
                                         BASKA_FORMS[(n + 1) % len(BASKA_FORMS)],
                                         CONFIRMS[(n + 1) % len(CONFIRMS)])),
                _m("user",      ORDER_MSGS[i3][2 % len(ORDER_MSGS[i3])]),
                _m("assistant", _confirm(i3, p3,
                                         BASKA_FORMS[(n + 2) % len(BASKA_FORMS)],
                                         CONFIRMS[(n + 2) % len(CONFIRMS)])),
                _m("user",      ORDER_MSGS[i4][3 % len(ORDER_MSGS[i4])]),
                _m("assistant", _confirm(i4, p4,
                                         BASKA_FORMS[(n + 3) % len(BASKA_FORMS)],
                                         CONFIRMS[(n + 3) % len(CONFIRMS)])),
                _m("user",      NO_MORE[n % len(NO_MORE)]),
                _m("assistant", ANLASILDI[n % len(ANLASILDI)]),
                _m("user",      BILL_REQUESTS[n % len(BILL_REQUESTS)]),
                _m("assistant", _bill(total, CLOSINGS[n % len(CLOSINGS)])),
            ]})

    # ── Section B: 3 ürün + ara soru (25 × 2 = 50) ─────────────────────────────
    # gen_hesap.py Section C'deki 10 üçlüyle örtüşmeyen 25 yeni üçlü
    TRIPLETS_B = [
        ("Mercimek Çorbası",       "Izgara Köfte",        "Limonata"),
        ("Mercimek Çorbası",       "Izgara Köfte",        "Şalgam Suyu"),
        ("Mercimek Çorbası",       "Et Döner",            "Fırın Sütlaç"),
        ("Mercimek Çorbası",       "Et Döner",            "Yayık Ayran"),
        ("Mercimek Çorbası",       "Et Döner",            "Limonata"),
        ("Mercimek Çorbası",       "Izgara Tavuk Salata", "Künefe"),
        ("Mercimek Çorbası",       "Izgara Tavuk Salata", "Yayık Ayran"),
        ("Mercimek Çorbası",       "Izgara Tavuk Salata", "Şalgam Suyu"),
        ("Mercimek Çorbası",       "Fırın Sütlaç",        "Yayık Ayran"),
        ("Mercimek Çorbası",       "Fırın Sütlaç",        "Limonata"),
        ("Kremalı Mantar Çorbası", "Izgara Köfte",        "Yayık Ayran"),
        ("Kremalı Mantar Çorbası", "Izgara Köfte",        "Limonata"),
        ("Kremalı Mantar Çorbası", "Izgara Köfte",        "Şalgam Suyu"),
        ("Kremalı Mantar Çorbası", "Et Döner",            "Fırın Sütlaç"),
        ("Kremalı Mantar Çorbası", "Et Döner",            "Yayık Ayran"),
        ("Kremalı Mantar Çorbası", "Et Döner",            "Şalgam Suyu"),
        ("Kremalı Mantar Çorbası", "Izgara Tavuk Salata", "Fırın Sütlaç"),
        ("Kremalı Mantar Çorbası", "Izgara Tavuk Salata", "Yayık Ayran"),
        ("Kremalı Mantar Çorbası", "Izgara Tavuk Salata", "Künefe"),
        ("Kremalı Mantar Çorbası", "Izgara Tavuk Salata", "Şalgam Suyu"),
        ("Izgara Köfte",           "Et Döner",            "Fırın Sütlaç"),
        ("Izgara Köfte",           "Et Döner",            "Künefe"),
        ("Izgara Köfte",           "Izgara Tavuk Salata", "Yayık Ayran"),
        ("Et Döner",               "Izgara Tavuk Salata", "Şalgam Suyu"),
        ("Izgara Köfte",           "Künefe",              "Şalgam Suyu"),
    ]
    for items3 in TRIPLETS_B:
        i1, i2, i3 = items3
        p1, p2, p3 = MENU[i1], MENU[i2], MENU[i3]
        total = p1 + p2 + p3
        for b_idx in range(2):
            n = len(records)
            q_user, q_bot = MID_QA[n % len(MID_QA)]
            records.append({"messages": [
                _m("system",    SYSTEM),
                _m("user",      USER_GREETS[n % len(USER_GREETS)]),
                _m("assistant", BOT_GREETS[n % len(BOT_GREETS)]),
                _m("user",      ORDER_MSGS[i1][b_idx % len(ORDER_MSGS[i1])]),
                _m("assistant", _confirm(i1, p1,
                                         BASKA_FORMS[n % len(BASKA_FORMS)],
                                         CONFIRMS[n % len(CONFIRMS)])),
                _m("user",      q_user),
                _m("assistant", q_bot),
                _m("user",      ORDER_MSGS[i2][(b_idx + 1) % len(ORDER_MSGS[i2])]),
                _m("assistant", _confirm(i2, p2,
                                         BASKA_FORMS[(n + 1) % len(BASKA_FORMS)],
                                         CONFIRMS[(n + 1) % len(CONFIRMS)])),
                _m("user",      ORDER_MSGS[i3][(b_idx + 2) % len(ORDER_MSGS[i3])]),
                _m("assistant", _confirm(i3, p3,
                                         BASKA_FORMS[(n + 2) % len(BASKA_FORMS)],
                                         CONFIRMS[(n + 2) % len(CONFIRMS)])),
                _m("user",      NO_MORE[n % len(NO_MORE)]),
                _m("assistant", ANLASILDI[n % len(ANLASILDI)]),
                _m("user",      BILL_REQUESTS[n % len(BILL_REQUESTS)]),
                _m("assistant", _bill(total, CLOSINGS[n % len(CLOSINGS)])),
            ]})

    # ── Section C: 5-item orders (20 × 2 = 40) ─────────────────────────────────
    QUINTS = [
        ("Mercimek Çorbası",       "Izgara Köfte",        "Fırın Sütlaç",       "Yayık Ayran",  "Şalgam Suyu"),
        ("Kremalı Mantar Çorbası", "Et Döner",            "Künefe",              "Limonata",     "Yayık Ayran"),
        ("Kremalı Mantar Çorbası", "Izgara Tavuk Salata", "Fırın Sütlaç",       "Yayık Ayran",  "Künefe"),
        ("Mercimek Çorbası",       "Izgara Köfte",        "Et Döner",            "Fırın Sütlaç", "Limonata"),
        ("Kremalı Mantar Çorbası", "Izgara Köfte",        "Izgara Tavuk Salata", "Künefe",       "Yayık Ayran"),
        ("Mercimek Çorbası",       "Et Döner",            "Izgara Tavuk Salata", "Fırın Sütlaç", "Şalgam Suyu"),
        ("Kremalı Mantar Çorbası", "Izgara Köfte",        "Fırın Sütlaç",       "Limonata",     "Şalgam Suyu"),
        ("Mercimek Çorbası",       "Izgara Köfte",        "Künefe",              "Yayık Ayran",  "Limonata"),
        ("Kremalı Mantar Çorbası", "Et Döner",            "Fırın Sütlaç",       "Şalgam Suyu",  "Limonata"),
        ("Mercimek Çorbası",       "Izgara Tavuk Salata", "Künefe",              "Limonata",     "Yayık Ayran"),
        ("Kremalı Mantar Çorbası", "Izgara Köfte",        "Et Döner",            "Künefe",       "Şalgam Suyu"),
        ("Mercimek Çorbası",       "Izgara Köfte",        "Izgara Tavuk Salata", "Fırın Sütlaç", "Yayık Ayran"),
        ("Kremalı Mantar Çorbası", "Et Döner",            "Izgara Tavuk Salata", "Künefe",       "Limonata"),
        ("Mercimek Çorbası",       "Et Döner",            "Fırın Sütlaç",       "Yayık Ayran",  "Şalgam Suyu"),
        ("Kremalı Mantar Çorbası", "Izgara Köfte",        "Fırın Sütlaç",       "Künefe",       "Limonata"),
        ("Mercimek Çorbası",       "Izgara Tavuk Salata", "Fırın Sütlaç",       "Limonata",     "Şalgam Suyu"),
        ("Kremalı Mantar Çorbası", "Et Döner",            "Künefe",              "Yayık Ayran",  "Şalgam Suyu"),
        ("Mercimek Çorbası",       "Izgara Köfte",        "Künefe",              "Limonata",     "Şalgam Suyu"),
        ("Kremalı Mantar Çorbası", "Izgara Tavuk Salata", "Fırın Sütlaç",       "Yayık Ayran",  "Şalgam Suyu"),
        ("Mercimek Çorbası",       "Et Döner",            "Izgara Tavuk Salata", "Künefe",       "Yayık Ayran"),
    ]
    for items5 in QUINTS:
        i1, i2, i3, i4, i5 = items5
        p1, p2, p3, p4, p5 = MENU[i1], MENU[i2], MENU[i3], MENU[i4], MENU[i5]
        total = p1 + p2 + p3 + p4 + p5
        for b_idx in range(2):
            n = len(records)
            records.append({"messages": [
                _m("system",    SYSTEM),
                _m("user",      USER_GREETS[n % len(USER_GREETS)]),
                _m("assistant", BOT_GREETS[n % len(BOT_GREETS)]),
                _m("user",      ORDER_MSGS[i1][0]),
                _m("assistant", _confirm(i1, p1,
                                         BASKA_FORMS[n % len(BASKA_FORMS)],
                                         CONFIRMS[n % len(CONFIRMS)])),
                _m("user",      ORDER_MSGS[i2][1 % len(ORDER_MSGS[i2])]),
                _m("assistant", _confirm(i2, p2,
                                         BASKA_FORMS[(n + 1) % len(BASKA_FORMS)],
                                         CONFIRMS[(n + 1) % len(CONFIRMS)])),
                _m("user",      ORDER_MSGS[i3][2 % len(ORDER_MSGS[i3])]),
                _m("assistant", _confirm(i3, p3,
                                         BASKA_FORMS[(n + 2) % len(BASKA_FORMS)],
                                         CONFIRMS[(n + 2) % len(CONFIRMS)])),
                _m("user",      ORDER_MSGS[i4][3 % len(ORDER_MSGS[i4])]),
                _m("assistant", _confirm(i4, p4,
                                         BASKA_FORMS[(n + 3) % len(BASKA_FORMS)],
                                         CONFIRMS[(n + 3) % len(CONFIRMS)])),
                _m("user",      ORDER_MSGS[i5][4 % len(ORDER_MSGS[i5])]),
                _m("assistant", _confirm(i5, p5,
                                         BASKA_FORMS[(n + 4) % len(BASKA_FORMS)],
                                         CONFIRMS[(n + 4) % len(CONFIRMS)])),
                _m("user",      NO_MORE[n % len(NO_MORE)]),
                _m("assistant", ANLASILDI[n % len(ANLASILDI)]),
                _m("user",      BILL_REQUESTS[n % len(BILL_REQUESTS)]),
                _m("assistant", _bill(total, CLOSINGS[n % len(CLOSINGS)])),
            ]})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Yazıldı: {OUT}  ({len(records)} kayıt)")


if __name__ == "__main__":
    main()
