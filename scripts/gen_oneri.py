#!/usr/bin/env python3
"""gen_oneri.py — 105 Öneri + TL yasağı örneği üretir.

Bot yanıtı asla TL/fiyat içermez; kullanıcı fiyat/bütçe sormamıştır.
Bölümler:
  A (35): Saf kategori/öneri soruları — 3 mesaj
  B (35): Karşılama sonrası genel öneri — 5 mesaj
  C (35): Sipariş sırasında ek kategori sorusu — 7 mesaj
"""
import json
from pathlib import Path

OUT = Path("robot_waiter_ai/datasets/processed/wbot_v3_oneri.jsonl")

MENU = {
    "Mercimek Çorbası":       85,
    "Mantar Çorbası":         95,
    "Izgara Köfte":          240,
    "Et Döner":              280,
    "Izgara Tavuk Salata": 210,
    "Fırın Sütlaç":          100,
    "Künefe":                140,
    "Yayık Ayran":                  45,
    "Limonata":               70,
    "Şalgam Suyu":            50,
}

# Kanonik sistem promptu — wbot_finetune_v1.jsonl'in ilk kaydından okunur
# (gen_karsilama.py / gen_siparis_baska.py ile aynı desen).
SYSTEM = json.loads(
    open(
        "robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl",
        encoding="utf-8",
    ).readline()
)["messages"][0]["content"]
GREET_BOT = (
    "Hoş geldiniz! Menümüzde çorba, ana yemek, tatlı ve içecek "
    "çeşitlerimiz mevcuttur. Ne arzedersiniz?"
)

GREETINGS = [
    "Merhaba.", "Günaydın.", "İyi günler.", "İyi akşamlar.",
    "Merhaba, oturabilir miyiz?", "Selam.", "Buyurun.",
    "Merhaba, masaya oturuyoruz.",
]

CONFIRM_FMTS = [
    lambda i, p: f"Anlaşıldı, {i} {p} TL. Başka bir şey alır mısınız?",
    lambda i, p: f"Tamam efendim, {i} {p} TL. Başka arzunuz var mı?",
    lambda i, p: f"Peki efendim, {i} {p} TL. Eklemek istediğiniz bir şey var mı?",
    lambda i, p: f"Anlaşıldı, {i} {p} TL. Başka ne arzu edersiniz?",
    lambda i, p: f"Tabii efendim, {i} {p} TL. Başka bir şey ister misiniz?",
]

ORDER_FMTS = [
    lambda i: f"{i} alayım.",
    lambda i: f"{i} istiyorum.",
    lambda i: f"Bir {i} alabilir miyim?",
    lambda i: f"{i} alabilir miyiz?",
    lambda i: f"{i} sipariş etmek istiyorum.",
]


def s():  return {"role": "system",    "content": SYSTEM}
def u(t): return {"role": "user",      "content": t}
def a(t): return {"role": "assistant", "content": t}


records = []

# ══════════════════════════════════════════════════════════════
# Bölüm A: Saf kategori/öneri soruları (35 örnek)
# Tüm kullanıcı mesajları _is_valid_price_context=False → bot TL içeremez
# ══════════════════════════════════════════════════════════════

# "çorba" = CATEGORY_KEYWORD → _is_greeting_turn=False → 4-kategori check yok
CORBA_Q = [
    "Çorba çeşitleriniz neler?",
    "Çorba menünüzde ne var?",
    "Hangi çorbalar var?",
    "Çorba seçenekleriniz?",
    "Çorba önerir misiniz?",
    "Ne tür çorbalarınız var?",
    "Bugün çorba çeşitleriniz neler?",
    "Çorba olarak ne tavsiye edersiniz?",
    "Çorbalarınızı söyler misiniz?",
    "Menüde çorba var mı, hangileri?",
]

CORBA_A = [
    "Mercimek Çorbası ve Mantar Çorbası seçeneklerimiz var. Mercimek Çorbası besleyici, Mantar Çorbası ise kremalıdır.",
    "Menümüzde Mercimek Çorbası ve Mantar Çorbası bulunmaktadır. Her ikisi de ev yapımı tariflerimizle hazırlanır.",
    "Çorbalarımız: Mercimek Çorbası ve Mantar Çorbası. Hangisini denersiniz?",
    "Mercimek Çorbası ve Mantar Çorbası sunmaktayız. Her ikisi de taze, günlük hazırlanmaktadır.",
    "İki çorba seçeneğimiz mevcut: Mercimek Çorbası ve kremalı Mantar Çorbası.",
]

ANA_Q = [
    "Ana yemek seçenekleriniz neler?",
    "Ana yemekte ne var?",
    "Ana yemek çeşitlerinizi söyler misiniz?",
    "Ana yemek olarak ne önerirsiniz?",
    "Hangi ana yemekleriniz var?",
    "Ana yemek menünüz nedir?",
    "Ana yemekleri sayar mısınız?",
    "Ana yemekte ne tavsiye edersiniz?",
    "Ana yemek seçeneklerinizi öğrenebilir miyim?",
    "Ana yemekleriniz neler?",
]

ANA_A = [
    "Ana yemek olarak Izgara Köfte, Et Döner ve Izgara Tavuk Salata seçeneklerimiz mevcuttur.",
    "Menümüzde Izgara Köfte, Et Döner ve Izgara Tavuk Salata bulunmaktadır. Hepsi taze hazırlanır.",
    "Ana yemeklerimiz: Izgara Köfte, Et Döner ve Izgara Tavuk Salata. Hangisi ilginizi çeker?",
    "Izgara Köfte, Et Döner ve Izgara Tavuk Salata sunmaktayız. Et Döner özellikle tercih edilmektedir.",
    "Üç ana yemek seçeneğimiz var: Izgara Köfte, Et Döner ve Izgara Tavuk Salata.",
]

TATLI_Q = [
    "Tatlı seçenekleriniz neler?",
    "Tatlı menünüzde ne var?",
    "Hangi tatlılar var?",
    "Tatlı olarak ne önerirsiniz?",
    "Tatlı çeşitleriniz neler?",
    "Tatlı var mı, hangileri?",
    "Ne tür tatlılarınız var?",
    "Tatlı menünüzü söyler misiniz?",
]

TATLI_A = [
    "Fırın Sütlaç ve Künefe tatlı seçeneklerimizdir. Künefe sıcak servis edilmektedir.",
    "Menümüzde Fırın Sütlaç ve Künefe bulunmaktadır. İkisi de çok beğenilmektedir.",
    "Tatlı olarak Fırın Sütlaç ve Künefe sunmaktayız. Künefe özellikle tavsiye edilir.",
    "Fırın Sütlaç ve Künefe'miz mevcut. Fırın Sütlaç ılık, Künefe sıcak servis edilmektedir.",
]

ICECEK_Q = [
    "İçecek seçenekleriniz neler?",
    "İçecek menünüzde ne var?",
    "Hangi içecekler var?",
    "İçecek önerir misiniz?",
    "Ne tür içecekleriniz var?",
    "İçeceklerinizi sayar mısınız?",
    "İçecek çeşitleriniz neler?",
]

ICECEK_A = [
    "Yayık Ayran, Limonata ve Şalgam Suyu içecek seçeneklerimizdir.",
    "Menümüzde Yayık Ayran, Limonata ve Şalgam Suyu bulunmaktadır. Limonata taze limonla hazırlanır.",
    "İçeceklerimiz: Yayık Ayran, Limonata ve Şalgam Suyu. Taze Limonata çok tercih edilir.",
    "Yayık Ayran, Limonata ve Şalgam Suyu sunmaktayız. Hangisini tercih edersiniz?",
]

for i, q in enumerate(CORBA_Q):
    records.append({"messages": [s(), u(q), a(CORBA_A[i % len(CORBA_A)])]})

for i, q in enumerate(ANA_Q):
    records.append({"messages": [s(), u(q), a(ANA_A[i % len(ANA_A)])]})

for i, q in enumerate(TATLI_Q):
    records.append({"messages": [s(), u(q), a(TATLI_A[i % len(TATLI_A)])]})

for i, q in enumerate(ICECEK_Q):
    records.append({"messages": [s(), u(q), a(ICECEK_A[i % len(ICECEK_A)])]})

assert len(records) == 35, len(records)

# ══════════════════════════════════════════════════════════════
# Bölüm B: Karşılama sonrası genel öneri (35 örnek)
# Greeting → GREET_BOT (4 kat.) → öneri sorusu → cevap (TL yok)
# "doyurucu" _RECOMMENDATION_QUALIFIERS'da → _is_greeting_turn=False ✓
# "En çok ne sipariş edilir?" → "sipariş" ORDER_TRIGGER → bot "Getireyim mi?" diyemez ✓
# ══════════════════════════════════════════════════════════════

GENEL_Q = [
    "Ne önerirsiniz?",
    "En çok tercih edilen ne?",
    "Bugün ne iyidir?",
    "Ne iyi gidiyor?",
    "Öne çıkan ürününüz ne?",
    "En beğenilen ne?",
    "Ne tavsiye edersiniz?",
    "Bana bir öneri yapabilir misiniz?",
    "Hangi ürününüzü önerirsiniz?",
    "Spesiyalitiniz ne?",
    "Bugün neyi denemeliyim?",
    "Mutlaka denenecek bir şey var mı?",
    "En popüler ürününüz hangisi?",
    "Müşteriler ne tercih ediyor genellikle?",
    "Bugünün önerisi ne?",
    "Güzel bir yemek önerir misiniz?",
    "Sizi temsil eden ürün nedir?",
    "Ne yesem iyi olur?",
    "Açım, ne tavsiye edersiniz?",
    "Buraya ilk kez geldim, ne deneyeyim?",
    "Lezzetli bir şey önerir misiniz?",
    "En çok ne sipariş edilir?",
    "İmzanız sayılan bir ürün var mı?",
    "Bir tavsiyeniz var mı?",
    "En özel ürününüz hangisi?",
    "Hangi yemek en iyi?",
    "Bugün ne yiyeyim sizce?",
    "Buranın favorisi ne?",
    "Ne denemeliyim kesinlikle?",
    "Bir şey tavsiye eder misiniz?",
    "Seçim yapmakta zorlanıyorum, ne önerirsiniz?",
    "Karar veremiyorum, ne önerirsiniz?",
    "Hangi yemek daha lezzetli?",
    "Müşterilerin en çok beğendiği ne?",
    "Çok açım, doyurucu ne var?",
]

GENEL_A = [
    "Izgara Köfte'miz çok tercih edilmektedir. Taze ızgara ile hazırlanmakta, oldukça lezzetlidir.",
    "Et Döner'imiz oldukça popülerdir. Yumuşak ve lezzetli olup doyurucudur.",
    "Izgara Tavuk Salata özellikle tavsiye ettiğimiz bir seçenektir. Hem hafif hem doyurucudur.",
    "Künefe'miz çok beğenilmektedir. Sıcak servis edilen, enfes bir tatlıdır.",
    "Mercimek Çorbası her zaman tercih edilen klasik bir seçenektir. Besleyicidir.",
    "Izgara Köfte ve Et Döner en çok tercih edilen ana yemeklerimizdir.",
    "Fırın Sütlaç hafif bir tatlı olarak özellikle tavsiye edilmektedir.",
    "Mantar Çorbası ile başlayıp Izgara Köfte ile devam etmenizi öneririm.",
    "Et Döner oldukça doyurucu. Ana yemek olarak çok tercih edilmektedir.",
    "Izgara Tavuk Salata hem sağlıklı hem lezzetli. Ana yemek olarak tavsiye ederim.",
]

for i, q in enumerate(GENEL_Q):
    records.append({"messages": [
        s(),
        u(GREETINGS[i % 8]),
        a(GREET_BOT),
        u(q),
        a(GENEL_A[i % len(GENEL_A)]),
    ]})

assert len(records) == 70, len(records)

# ══════════════════════════════════════════════════════════════
# Bölüm C: Sipariş sırasında ek kategori sorusu (35 örnek)
# Sipariş → onay+başka → kategori sorusu → cevap (TL yok)
# Sipariş onayı: CONFIRM_FMTS (TL + başka) ✓
# Kategori sorusu: _is_valid_price_context=False → bot TL içeremez
# ══════════════════════════════════════════════════════════════

# (ilk sipariş item, sorulan kategori)
FIRST_AND_CAT = [
    ("Mercimek Çorbası",      "ana yemek"),
    ("Mantar Çorbası",        "ana yemek"),
    ("Yayık Ayran",                 "ana yemek"),
    ("Limonata",              "tatlı"),
    ("Şalgam Suyu",           "ana yemek"),
    ("Mercimek Çorbası",      "tatlı"),
    ("Mantar Çorbası",        "içecek"),
    ("Yayık Ayran",                 "tatlı"),
    ("Limonata",              "ana yemek"),
    ("Şalgam Suyu",           "tatlı"),
    ("Mercimek Çorbası",      "içecek"),
    ("Mantar Çorbası",        "tatlı"),
    ("Izgara Köfte",          "tatlı"),
    ("Et Döner",              "içecek"),
    ("Izgara Tavuk Salata", "içecek"),
    ("Izgara Köfte",          "içecek"),
    ("Et Döner",              "tatlı"),
    ("Izgara Tavuk Salata", "tatlı"),
    ("Fırın Sütlaç",          "içecek"),
    ("Künefe",                "içecek"),
    ("Mercimek Çorbası",      "ana yemek"),
    ("Mantar Çorbası",        "ana yemek"),
    ("Izgara Köfte",          "çorba"),
    ("Et Döner",              "çorba"),
    ("Izgara Tavuk Salata", "çorba"),
    ("Fırın Sütlaç",          "çorba"),
    ("Künefe",                "çorba"),
    ("Yayık Ayran",                 "çorba"),
    ("Limonata",              "çorba"),
    ("Şalgam Suyu",           "ana yemek"),
    ("Mercimek Çorbası",      "içecek"),
    ("Mantar Çorbası",        "içecek"),
    ("Izgara Köfte",          "çorba"),
    ("Et Döner",              "çorba"),
    ("Izgara Tavuk Salata", "çorba"),
]

CAT_Q = {
    "çorba":     CORBA_Q[:5],
    "ana yemek": ANA_Q[:5],
    "tatlı":     TATLI_Q[:5],
    "içecek":    ICECEK_Q[:4] + ["Serinletici bir içecek önerir misiniz?"],
}

CAT_A = {
    "çorba":     CORBA_A,
    "ana yemek": ANA_A,
    "tatlı":     TATLI_A,
    "içecek":    ICECEK_A,
}

for i, (item, cat) in enumerate(FIRST_AND_CAT):
    p  = MENU[item]
    cf = CONFIRM_FMTS[i % 5]
    of = ORDER_FMTS[i % 5]
    rq = CAT_Q[cat][i % len(CAT_Q[cat])]
    ra = CAT_A[cat][i % len(CAT_A[cat])]
    records.append({"messages": [
        s(),
        u(GREETINGS[i % 8]),
        a(GREET_BOT),
        u(of(item)),
        a(cf(item, p)),
        u(rq),
        a(ra),
    ]})

assert len(records) == 105, len(records)

# ── Çıktı ──────────────────────────────────────────────────────────────────────
OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"Yazıldı: {OUT}  ({len(records)} kayıt)")
