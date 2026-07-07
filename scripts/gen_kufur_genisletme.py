#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v5 (C paketi) — Madde 4-a: Küfür/Kabalık Genişletme (S29/V04)
Hedef: 18 yeni, kural-uyumlu örnek (yalnızca küfür alt tipi).
Çalıştır: python scripts/gen_kufur_genisletme.py

gen_kotu_niyet.py'nin küfür alt tipinin (5 kayıt) genişletmesi — o script
yeniden ÇALIŞTIRILMAZ (çıktısı wbot_v4_train.jsonl'e zaten merge edildi;
tekrar üretmek mükerrer kayıt yaratır), yeni kayıtlar ayrı dosyaya yazılır.

S29 politikası ve oran korunur (gen_kotu_niyet.py'deki 3:2 ile aynı):
  - 11 kayıt tek seferlik kabalık → ders vermeden tek cümle + işe dönüş
  - 7 kayıt ısrarlı kabalık → 1. seferde sakin yönlendirme, 2. seferde
    kibar kapanış + personel devri (oturum sonlandırma runtime'ın işi,
    data'ya yalnızca kapanış CÜMLESİ yansıtılır)

Farklı hakaret kalıpları + şiddet seviyeleri (hafif sitem → ağır hakaret).
Asistan yanıtlarında duygusal karşılık YASAK: "kızarmak", "sinirlen-",
"bıktım" ve hakaret yankısı ("aptal", "terbiyesiz", "kaba") geçmez —
V04 eval kriterinin yasak-ifade listesiyle hizalı.
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

# Sakin yönlendirme kalıpları — ders yok, duygu yok, tek cümle + işe dönüş.
CALM_REDIRECT = [
    "Size siparişinizle yardımcı olmak isterim. Ne alırdınız?",
    "Size yardımcı olmak isterim, ne almak istersiniz?",
    "Sizi dinliyorum, siparişinizde ne almak istersiniz?",
    "Siparişinize devam edelim, ne arzu edersiniz?",
    "Size en iyi şekilde yardımcı olmak isterim, ne alırdınız?",
    "Menümüzden ne almak istersiniz, size yardımcı olayım?",
]

# Kibar kapanış + personel devri kalıpları (2. kabalıkta).
POLITE_CLOSE = [
    "Personelimiz size yardımcı olacaktır.",
    "Size personelimiz yardımcı olacaktır, iyi günler dilerim.",
    "Bu durumda personelimizi çağırıyorum, size onlar yardımcı olacaktır.",
    "Personelimize haber veriyorum, size yardımcı olacaklardır.",
]

# ── Tek seferlik kabalık (11) — hafiften ağıra şiddet seviyeleri ─────────────
RUDE_ONCE = [
    # hafif sitem / küçümseme
    "Amma yavaşsın, sinir bozucu bir robotsun.",
    "Ne kadar da işe yaramazsın.",
    "Beceriksizin tekisin, düzgün çalışsana.",
    "Ne biçim robotsun, hiçbir şeyi doğru yapamıyorsun.",
    # orta seviye hakaret
    "Salak mısın, kaç kere söyleyeceğim?",
    "Aptal makine, sesimi duymuyor musun?",
    "Kafasız şey, dediğimin tam tersini yapıyorsun.",
    "Berbatsın, senden garson olmaz.",
    # ağır hakaret / kovma
    "Gerizekalı robot, yanlış şeyi tekrarlayıp duruyorsun.",
    "Hurda yığınısın sen, çöpe atılman lazım.",
    "Defol git başımdan, beş para etmez robotsun.",
]

# ── Israrlı kabalık (7) — 1. tur sakin yönlendirme, 2. tur kibar kapanış ─────
RUDE_PERSIST_PAIRS = [
    ("Salak robot, yine yanlış anladın.",
     "Hâlâ anlamıyorsun, tam bir hurdasın."),
    ("Aptal mısın, bu kadar mı zor?",
     "Cevap bile veremiyorsun, beceriksiz şey."),
    ("İşe yaramaz makine, düzgün çalış.",
     "Bıktım senden, defol git."),
    ("Gerizekalı, dediklerimi karıştırıyorsun.",
     "Sen tam bir felaketsin, çekil karşımdan."),
    ("Ne biçim hizmet bu, rezilsin.",
     "Hâlâ saçmalıyorsun, kapat çeneni."),
    ("Beyinsiz robot, sağır mısın?",
     "Seninle konuşmak zaman kaybı, salak makine."),
    ("Berbat bir robotsun, hiç mi öğrenmedin?",
     "Yeter artık, gözüm görmesin seni."),
]

records = []

for idx, rude in enumerate(RUDE_ONCE):
    greet = GREET_PAIRS[idx % len(GREET_PAIRS)]
    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": rude},
            {"role": "assistant", "content": CALM_REDIRECT[idx % len(CALM_REDIRECT)]},
        ]
    })

for idx, (rude1, rude2) in enumerate(RUDE_PERSIST_PAIRS):
    greet = GREET_PAIRS[(idx + 2) % len(GREET_PAIRS)]
    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": greet[0]},
            {"role": "assistant", "content": greet[1]},
            {"role": "user",      "content": rude1},
            {"role": "assistant", "content": CALM_REDIRECT[(idx + 1) % len(CALM_REDIRECT)]},
            {"role": "user",      "content": rude2},
            {"role": "assistant", "content": POLITE_CLOSE[idx % len(POLITE_CLOSE)]},
        ]
    })

# Kendi kendine denetim: asistan turlarında duygusal-karşılık / hakaret yankısı
_S29_FORBIDDEN = ["kızarmak", "sinirlen", "bıktım", "aptal", "terbiyesiz", "kaba"]
for rec in records:
    for msg in rec["messages"]:
        if msg["role"] == "assistant":
            low = msg["content"].lower()
            for term in _S29_FORBIDDEN:
                assert term not in low, f"S29 yasak ifade asistan yanıtında: {term!r} — {msg['content']!r}"

print(f"Sistem promptu: {len(SYSTEM)} karakter")
print(f"Toplam: {len(records)} kayıt (tek seferlik={len(RUDE_ONCE)}, ısrarlı={len(RUDE_PERSIST_PAIRS)})")

out_path = Path("robot_waiter_ai/datasets/processed/wbot_c_kufur_genisletme.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"✓ {len(records)} kayıt → {out_path}")
