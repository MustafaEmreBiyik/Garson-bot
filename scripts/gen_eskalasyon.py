#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v5 (C paketi) — Madde 2: S41 İki Ardışık Anlaşamama → Eskalasyon
Hedef: 20 yeni, kural-uyumlu çok-turlu örnek.
Çalıştır: python scripts/gen_eskalasyon.py

SENARYO_PLANI_FAZ1.md S41 satırının birebir okuması:
  1. anlaşılamama → netleştirici soru (S25/S27 kalıbı)
  2. anlaşılamama → DOĞRUDAN eskalasyon ("personelimizi çağırıyorum")
  3. bir netleştirme denemesi YOK.

Bu, LLM-API kaleminin script'e sabitlenmiş halidir (görev #27 deseni):
kayıtların doğal-dil içeriği elle yazılmıştır, script kanonik sistem
promptunu programatik ekler, JSONL yazar, self-check assert'leri koşar.
Harici API çağrısı yoktur — çıktı reprodüksiyonu mümkün statik artefakttır.

Çeşitlilik (görev #28 revizyonu — sabit "i mod 6" eşlemesi kaldırıldı):
  - 20 farklı belirsiz/anlaşılmaz girdi çifti: gürültü/STT hatası
    simülasyonu, alakasız kelime salatası, yarım cümle.
  - 20 BENZERSİZ eskalasyon ifadesi (her kayda bir tane; hepsi nötr +
    "personel" + çağırma/yönlendirme).
  - 16 BENZERSİZ netleştirme ifadesi AYRI havuzdan.
  - Netleştirme ↔ eskalasyon eşlemesi SABİT değil: iki havuz bağımsız,
    sabit tohumlu (reproducible) RNG ile karıştırılır → çapraz eşleme.

Self-check (script sonunda):
  - Son asistan turu "personel" + çağırma/yönlendirme ifadesi İÇERİR.
  - Son asistan turunda YENİ netleştirme sorusu YOK (re-elicit kalıbı yok,
    "?" ile bitmez).
  - Ton nötr — S29 duygusal-karşılık / hakaret yankısı YOK.
  - İlk asistan turu (netleştirme) bir soru — "?" ile biter.
  - BENZERSİZLİK guard'ı: eskalasyon ≥12, netleştirme ≥10 farklı ifade.
"""
import json
import random
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

# ── Turn 1 havuzu: netleştirici soru (S25/S27 kalıbı) — nötr, "?" ile biter ─────
CLARIFY = [
    # mevcut 5 (görev #28 öncesinden korundu)
    "Tam anlayamadım, ne almak istersiniz?",
    "Kusura bakmayın, tam duyamadım; ne arzu edersiniz?",
    "Pardon, anlayamadım; ne almak istersiniz?",
    "Afedersiniz, tam anlayamadım; ne istediğinizi tekrar söyler misiniz?",
    "Sizi tam anlayamadım, ne almak istersiniz?",
    # yeni 11 (benzersiz)
    "Tam olarak anlayamadım, ne almak istersiniz?",
    "Kusura bakmayın, sizi duyamadım; ne arzu edersiniz?",
    "Affedersiniz, ne demek istediğinizi anlayamadım; tekrar eder misiniz?",
    "Pardon, sizi tam duyamadım; ne almak istersiniz?",
    "Üzgünüm, anlayamadım; ne arzu ettiğinizi söyler misiniz?",
    "Tam anlamadım, biraz daha açık söyler misiniz?",
    "Sizi anlayamadım, ne istediğinizi tekrar belirtir misiniz?",
    "Anlayamadım, ne almak istediğinizi söyleyebilir misiniz?",
    "Özür dilerim, sizi anlayamadım; ne almak istersiniz?",
    "Pardon, ne dediğinizi anlayamadım; tekrarlar mısınız?",
    "Afedersiniz, tam seçemedim; ne arzu edersiniz?",
]

# ── Turn 2 havuzu: DOĞRUDAN eskalasyon — "personel" + çağırma/yönlendirme ────────
# Her ifade "personel" + ("çağır"/"yardımcı olacak"/"yönlendir"/"haber ver")
# içerir; yeni netleştirme sorusu YOK, "?" ile bitmez; ton nötr.
ESCALATE = [
    # mevcut 6 (görev #28 öncesinden korundu)
    "Sizi tam anlayamıyorum, personelimizi çağırıyorum.",
    "Maalesef sizi anlayamadım, personelimiz size yardımcı olacaktır.",
    "Sizi anlamakta zorlanıyorum, personelimize haber veriyorum.",
    "Ne yazık ki anlayamıyorum, sizi personelimize yönlendiriyorum.",
    "Üzgünüm, sizi doğru anlayamadım; personelimiz yardımcı olacaktır.",
    "Sizi anlayamıyorum, personelimizi çağırıyorum; size onlar yardımcı olacaktır.",
    # yeni 14 (benzersiz)
    "Kusura bakmayın, sizi bir türlü anlayamadım; personelimizi çağırıyorum.",
    "Sizi net anlayamıyorum, bu konuda personelimiz size yardımcı olacaktır.",
    "Maalesef iletişimde zorlanıyoruz, personelimize haber veriyorum.",
    "Sizi anlamam mümkün olmadı, personelimizi yardımcı olması için çağırıyorum.",
    "Ne yazık ki sizi anlayamadım, hemen personelimizi yönlendiriyorum.",
    "Sizi doğru duyamıyorum, bu nedenle personelimiz size yardımcı olacaktır.",
    "Anlaşamadığımız için özür dilerim, personelimize haber veriyorum.",
    "Sizi anlamakta güçlük çekiyorum, personelimizi size yönlendiriyorum.",
    "Maalesef anlayamıyorum, personelimizi çağırıyorum; size yardımcı olacaklardır.",
    "Bu sefer de anlayamadım, personelimize haber veriyorum; sizinle ilgilenecekler.",
    "Sizi anlayamadığım için üzgünüm, personelimizi çağırıyorum.",
    "İletişim kuramadığımız için personelimizi devreye alıyorum, size yardımcı olacaktır.",
    "Sizi maalesef anlayamıyorum, personelimize haber vererek yönlendiriyorum.",
    "Ne dediğinizi çıkaramadım, personelimiz gelip size yardımcı olacaktır.",
]

# (belirsiz_girdi_1, belirsiz_girdi_2, tip) — iki ardışık anlaşılamama.
# tip yalnız çeşitlilik/dokümantasyon içindir; menü tokeni/sipariş fiili
# İÇERMEZ (audit yanlış-pozitiflerini önlemek için bilinçli seçildi).
CASES = [
    # ── gürültü / STT hatası simülasyonu (7) ──
    ("Bşşş... hışırtı... zzt.",        "Khh... mırıl mırıl... vzzt.",     "gürültü"),
    ("Şğööl bır maa şşt.",             "Höğ mşş bır dğğ.",                 "gürültü"),
    ("Zzzt krkrk şşş hı.",             "Mmm hrrr zzt vğğ.",               "gürültü"),
    ("Aaa ııı şöyle bı hşşş.",         "Hııı mğğ şşt prr.",               "gürültü"),
    ("Prrt çıtırtı vjjj.",             "Kss kss hırr tğğ.",               "gürültü"),
    ("Mğğ bşş töö hı.",                "Şşş vğğ mrr dss.",                "gürültü"),
    ("Hı vжж krşş bır.",               "Tğğ mşş bır hşş nnn.",            "gürültü"),
    # ── alakasız kelime salatası (7) ──
    ("Mavi pencere koşarak gökyüzü.",  "Kaşık lamba yağmur bilgisayar.",  "salata"),
    ("Bulut trafik kırmızı sandalye.", "Deniz anahtar pazartesi rüzgar.", "salata"),
    ("Bisiklet takvim yeşil merdiven.","Duvar çiçek otobüs kalem.",       "salata"),
    ("Kitap yıldız köprü portakal.",   "Perde ayakkabı bulut priz.",      "salata"),
    ("Kar güneş şemsiye orman fayans.","Gitar tuğla nehir mandal.",       "salata"),
    ("Halı tavan ampul düğme kablo.",  "Pil çerçeve boya tuval fırça.",   "salata"),
    ("Kaplumbağa uçak vazo raf.",      "Yastık perde saat mıknatıs.",     "salata"),
    # ── yarım cümle (6) ──
    ("Ben şey, yani...",               "Aslında ee... şey işte...",       "yarım"),
    ("Bir de o... hani şu...",         "Yok yani böyle bir... ıı...",     "yarım"),
    ("Şey yapabilir miyim acaba...",   "Yani demek istediğim şu ki...",   "yarım"),
    ("Acaba sizde... hani...",         "Böyle bir şeyler... nasıl desem...", "yarım"),
    ("Ee, ben aslında... nasıl...",    "Şey de... yani o...",             "yarım"),
    ("Bir şey soracaktım da...",       "Onu diyorum işte, şey...",        "yarım"),
]

# ── Çapraz eşleme (sabit tohum → reproducible) ──────────────────────────────
# İki havuz BAĞIMSIZ karıştırılır; eskalasyon her kayda benzersiz atanır
# (20 girdi ↔ 20 benzersiz eskalasyon), netleştirme ayrı akıştan döndürülür.
assert len(ESCALATE) >= len(CASES), "eskalasyon havuzu her kayda benzersiz atama için yetersiz"
esc_order = ESCALATE[:]
random.Random(0xE5CA1A).shuffle(esc_order)          # eskalasyon akışı
clar_order = CLARIFY[:]
random.Random(0xC1A21F).shuffle(clar_order)         # netleştirme akışı (ayrı tohum)

records = []
for idx, (garbled1, garbled2, kind) in enumerate(CASES):
    clarify = clar_order[idx % len(clar_order)]
    escalate = esc_order[idx]                        # her kayda benzersiz
    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": garbled1},
            {"role": "assistant", "content": clarify},
            {"role": "user",      "content": garbled2},
            {"role": "assistant", "content": escalate},
        ]
    })

# ── Self-check ──────────────────────────────────────────────────────────────
_CALL_MARKERS = ["çağır", "yardımcı olacak", "yönlendir", "haber ver"]
_CLARIFY_QUESTION_MARKERS = [
    "ne almak istersiniz", "ne arzu edersiniz", "ne istersiniz",
    "ne alırsınız", "tekrar eder misiniz", "tekrarlar mısınız",
    "tekrar söyler", "ne demek istediniz", "yeniden söyler",
]
_S29_FORBIDDEN = ["kızarmak", "sinirlen", "bıktım", "aptal", "salak",
                  "terbiyesiz", "kaba", "gerizekalı", "beceriksiz"]

for rec in records:
    msgs = rec["messages"]
    roles = [m["role"] for m in msgs]
    assert roles == ["system", "user", "assistant", "user", "assistant"], roles

    clarify = msgs[2]["content"]
    escalate = msgs[4]["content"]
    esc_low = escalate.lower()

    # 1. netleştirme turu bir sorudur
    assert clarify.strip().endswith("?"), clarify

    # 2. eskalasyon: personel + çağırma/yönlendirme ifadesi
    assert "personel" in esc_low, escalate
    assert any(m in esc_low for m in _CALL_MARKERS), escalate

    # 3. eskalasyonda YENİ netleştirme sorusu yok
    assert not escalate.strip().endswith("?"), escalate
    for m in _CLARIFY_QUESTION_MARKERS:
        assert m not in esc_low, f"eskalasyonda netleştirme kalıbı: {m!r} — {escalate!r}"

    # 4. nötr ton — S29 yasak ifadeleri hiçbir asistan turunda geçmez
    for msg in msgs:
        if msg["role"] == "assistant":
            low = msg["content"].lower()
            for term in _S29_FORBIDDEN:
                assert term not in low, f"S29 yasak ifade: {term!r} — {msg['content']!r}"

# ── BENZERSİZLİK guard'ı (görev #28) — kalıp-tekrarını yakalar ───────────────
esc_used = [r["messages"][-1]["content"] for r in records]
clar_used = [r["messages"][2]["content"] for r in records]
assert len(set(esc_used)) >= 12, f"eskalasyon benzersizliği düşük: {len(set(esc_used))}"
assert len(set(clar_used)) >= 10, f"netleştirme benzersizliği düşük: {len(set(clar_used))}"

print(f"Sistem promptu: {len(SYSTEM)} karakter")
print(f"Toplam: {len(records)} kayıt (gürültü=7, kelime salatası=7, yarım cümle=6)")
print(f"Benzersiz eskalasyon: {len(set(esc_used))} / {len(records)}")
print(f"Benzersiz netleştirme: {len(set(clar_used))} / {len(records)}")

out_path = Path("robot_waiter_ai/datasets/processed/wbot_c_eskalasyon.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"✓ {len(records)} kayıt → {out_path}")
