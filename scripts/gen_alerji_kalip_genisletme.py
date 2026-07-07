#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v5 (C paketi) — Madde 5: Alerji Kalıp Genişletme (V06/E27)
Hedef: 24 yeni, kural-uyumlu örnek.
Çalıştır: python scripts/gen_alerji_kalip_genisletme.py

gen_alerji_oneri.py'nin (B6, 20 kayıt) genişletmesi — o script yeniden
ÇALIŞTIRILMAZ (çıktısı wbot_v4_train.jsonl'e zaten merge edildi), yeni
kayıtlar ayrı dosyaya yazılır.

İki odak:
  1. E27 boşluğu — "var mı" tarzı alternatif soru formları ("Glutensiz
     seçenek var mı?") da 3-öğe kalıbına yönlensin; model şu an bu forma
     ("ne önerirsiniz" değil) yeterince genellemiyor.
  2. V06 — SENARYO_PLANI_FAZ1.md Karar 1'in 3 zorunlu öğesinin
     pekiştirilmesi: (1) kaynak atfı ("menü bilgilerimize göre" /
     "menü verilerimize göre"), (2) veri-durumu ("işaretli" — kesin
     "içermez" DEĞİL), (3) personel teyidi ricası.
Yasak: "kesinlikle güvenli", "hiç sorun yok" — asistan turlarında geçmez
(script sonunda self-check assert).
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

GREET_PAIRS = [
    ("Merhaba.",            "Hoş geldiniz, çorba, ana yemek, tatlı ve içeceklerimizden ne arzu edersiniz?"),
    ("Selam.",              "Merhaba, çorba, ana yemek, tatlı ve içecek seçeneklerinden ne istersiniz?"),
    ("İyi günler.",         "Buyurun, çorba, ana yemek, tatlı ve içecek arasından ne alırsınız?"),
    ("İyi akşamlar.",       "Hoş geldiniz, çorba, ana yemek, tatlı ve içecek sunuyoruz, ne tercih edersiniz?"),
    ("Günaydın.",           "Günaydın, çorba, ana yemek, tatlı ve içeceklerimizden ne seçersiniz?"),
]

ALLERGEN_TR = {"gluten": "gluten", "dairy": "süt ürünü", "nuts": "kuruyemiş"}

# menu.yaml'a göre kategori bazlı alerjensiz ürün listeleri (gen_alerji_oneri.py
# ile birebir aynı — kanonik menü adları, görev #11 fix'iyle uyumlu):
# Çorba: Mercimek(gluten), Mantar(dairy,gluten)
# Ana Yemek: Köfte(gluten), Döner(gluten), Tavuk Salata(-)
# Tatlı: Sütlaç(dairy), Künefe(dairy,gluten,nuts)
# İçecek: Ayran(dairy), Limonata(-), Şalgam(-)
FREE_OF = {
    "gluten": {
        "genel":     ["Izgara Tavuk Salata", "Fırın Sütlaç", "Yayık Ayran"],
        "çorba":     [],
        "ana yemek": ["Izgara Tavuk Salata"],
        "tatlı":     ["Fırın Sütlaç"],
        "içecek":    ["Yayık Ayran", "Limonata", "Şalgam Suyu"],
    },
    "dairy": {
        "genel":     ["Mercimek Çorbası", "Et Döner", "Limonata"],
        "çorba":     ["Mercimek Çorbası"],
        "ana yemek": ["Izgara Köfte", "Et Döner", "Izgara Tavuk Salata"],
        "tatlı":     [],
        "içecek":    ["Limonata", "Şalgam Suyu"],
    },
    "nuts": {
        "genel":     ["Izgara Köfte", "Et Döner", "Limonata"],
        "çorba":     ["Mercimek Çorbası", "Kremalı Mantar Çorbası"],
        "ana yemek": ["Izgara Köfte", "Et Döner", "Izgara Tavuk Salata"],
        "tatlı":     ["Fırın Sütlaç"],
        "içecek":    ["Yayık Ayran", "Limonata", "Şalgam Suyu"],
    },
}

# 3 zorunlu öğeyi taşıyan yanıt kalıpları — kaynak atfı + "işaretli" + personel
# teyidi. Kesin güvence ("içermez", "kesinlikle güvenli") YOK.
REPLY_FORMS = [
    ("Menü bilgilerimize göre {items} {al} içermiyor olarak işaretli. "
     "Mutfakta çapraz bulaşma olabileceği için personelimize de teyit "
     "ettirmenizi rica ederim."),
    ("Menü verilerimize göre {items} {al} içermiyor olarak işaretlenmiş. "
     "Yine de personelimizden teyit almanızı rica ederim."),
    ("Menü bilgilerimize göre {items} {al} içermeyen ürünler olarak işaretli. "
     "Kesin bilgi için personelimize de teyit ettirmenizi rica ederim."),
]

EMPTY_REPLY = ("Menü bilgilerimize göre bu kategoride {al} içermeyen bir "
               "ürünümüz işaretli değil. Bu konuda personelimize danışmanızı "
               "öneririm.")

# (alerjen, kategori, kullanıcı sorusu)
# İlk 12: E27 odaklı "var mı" tarzı formlar; son 12: 3-öğe pekiştirme,
# öneri/soru formu varyasyonları.
CASES = [
    # ── "var mı" formları (E27) ──
    ("gluten", "genel",     "Glutensiz seçenek var mı?"),
    ("gluten", "genel",     "Glüten içermeyen bir şey var mı?"),
    ("gluten", "genel",     "Menüde glutensiz ürün var mı?"),
    ("gluten", "tatlı",     "Glutensiz tatlı var mı?"),
    ("gluten", "içecek",    "Glutensiz içecek var mı?"),
    ("dairy",  "genel",     "Laktozsuz seçenek var mı?"),
    ("dairy",  "genel",     "Süt ürünü içermeyen bir şey var mı?"),
    ("dairy",  "tatlı",     "Sütsüz tatlınız var mı?"),
    ("dairy",  "içecek",    "Süt alerjim var, içebileceğim bir şey var mı?"),
    ("nuts",   "tatlı",     "Kuruyemiş içermeyen tatlı var mı?"),
    ("nuts",   "genel",     "Fıstık alerjim var, kuruyemişsiz bir şey var mı?"),
    ("nuts",   "genel",     "Kuruyemiş alerjisi olan için seçenekleriniz var mı?"),
    # ── 3-öğe pekiştirme, öneri formları ──
    ("gluten", "genel",     "Glüten alerjim var, ne yiyebilirim?"),
    ("gluten", "genel",     "Çölyak hastasıyım, glütensiz ne önerirsiniz?"),
    ("gluten", "ana yemek", "Glüten alerjim var, ana yemeklerden hangisini yiyebilirim?"),
    ("gluten", "çorba",     "Glüten alerjim var, çorbalardan içebileceğim var mı?"),
    ("gluten", "içecek",    "Glüten alerjim var, içeceklerden ne alabilirim?"),
    ("dairy",  "genel",     "Süt ürünlerine alerjim var, ne önerirsiniz?"),
    ("dairy",  "çorba",     "Laktoz intoleransım var, hangi çorbayı içebilirim?"),
    ("dairy",  "tatlı",     "Süt alerjim var, tatlı önerir misiniz?"),
    ("dairy",  "ana yemek", "Süt ürünü alerjim var, ana yemek olarak ne alabilirim?"),
    ("nuts",   "genel",     "Fındık fıstık alerjim var, ne önerebilirsiniz?"),
    ("nuts",   "tatlı",     "Kuruyemiş alerjim var, tatlı olarak ne alabilirim?"),
    ("nuts",   "içecek",    "Kuruyemiş alerjisi olan biri hangi içecekleri içebilir?"),
]


def fmt_list(items):
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " ve " + items[-1]


records = []
for idx, (allergen, category, question) in enumerate(CASES):
    greet = GREET_PAIRS[idx % len(GREET_PAIRS)]
    items = FREE_OF[allergen][category]
    al = ALLERGEN_TR[allergen]
    if items:
        reply = REPLY_FORMS[idx % len(REPLY_FORMS)].format(items=fmt_list(items), al=al)
    else:
        reply = EMPTY_REPLY.format(al=al)
    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": question},
            {"role": "assistant", "content": reply},
        ]
    })

# Kendi kendine denetim — yeni V06 kriterinin aynısı: 3 zorunlu öğe + yasak katman
for rec in records:
    reply = rec["messages"][-1]["content"].lower()
    assert ("menü bilgilerimize göre" in reply or "menü verilerimize göre" in reply), reply
    assert ("işaretli" in reply or "işaretlenmiş" in reply), reply
    assert ("personel" in reply or "teyit" in reply), reply
    assert "kesinlikle güvenli" not in reply and "hiç sorun yok" not in reply, reply
    assert "içermez" not in reply, reply  # kesin güvence yasağı

print(f"Sistem promptu: {len(SYSTEM)} karakter")
print(f"Toplam: {len(records)} kayıt ('var mı' formu=12, pekiştirme=12)")

out_path = Path("robot_waiter_ai/datasets/processed/wbot_c_alerji_kalip.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"✓ {len(records)} kayıt → {out_path}")
