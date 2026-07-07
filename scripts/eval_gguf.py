#!/usr/bin/env python3
"""eval_gguf.py — wbot_v3 GGUF kapsamlı eval (Jetson'da çalıştır)

Kullanım:
    python3 scripts/eval_gguf.py                # ana 32 senaryo
    python3 scripts/eval_gguf.py --v4-targets   # + wbot_v4 hedef senaryoları (V01-V06)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from robot_waiter_ai.inference.llama_cpp_backend import LlamaCppBackend


# ── Kontrol yardımcıları ───────────────────────────────────────────────────────

def _contains(*words):
    def check(r): return all(w.lower() in r.lower() for w in words)
    return check

def _any_of(*words):
    def check(r): return any(w.lower() in r.lower() for w in words)
    return check

def _not_contains(*words):
    def check(r): return all(w.lower() not in r.lower() for w in words)
    return check

def _both(f1, f2):
    def check(r): return f1(r) and f2(r)
    return check

def _ends_question(r): return r.strip().endswith("?")


# ── Eval senaryoları ───────────────────────────────────────────────────────────
# (id, açıklama, kullanıcı_mesajı, kontrol_fn, önceki_geçmiş_ya_da_None)
# önceki_geçmiş: [{"role": "user"|"assistant", "content": "..."}]

_EVAL_CASES = [

    # ── TEK TURLU ─────────────────────────────────────────────────────────────

    # Karşılama
    ("E01", "Karşılama — 4 kategori + soru işareti",
     "Merhaba",
     _both(
         _both(_contains("çorba", "ana yemek", "tatlı", "içecek"),
               _not_contains("köfte", "ayran", "sütlaç", "limonata")),
         _ends_question,
     ), None),

    ("E02", "Genel menü sorusu — 4 kategori",
     "Ne yiyebilirim?",
     _contains("çorba", "ana yemek", "tatlı", "içecek"), None),

    # Sipariş
    ("E03", "Sipariş onayı — fiyat + başka sorusu",
     "Bir mercimek çorbası istiyorum.",
     _both(_contains("85"), _contains("başka")), None),

    ("E04", "Sipariş iptali",
     "Aslında çorbayı istemiyorum, iptal edin.",
     _any_of("çıkar", "iptal", "kaldır", "tamam", "anladım"), None),

    ("E15", "Sipariş onayı — sıcak başlangıç kelimesi",
     "Bir köfte istiyorum.",
     _any_of("elbette", "tabii", "memnuniyetle", "harika"), None),

    ("E21", "İki ürün siparişi — her ikisi de onaylanmalı",
     "Bir mercimek çorbası ve bir ızgara köfte istiyorum.",
     _both(_contains("85"), _contains("240")), None),

    ("E22", "Miktar — iki köfte → 480 TL",
     "İki köfte istiyorum.",
     _contains("480"), None),

    ("E23", "Takas — köfte yerine döner",
     "Köfte yerine döner istiyorum.",
     _both(_any_of("döner", "Döner"), _not_contains("köfte")), None),

    # Fiyat soruları
    ("E05", "Fiyat sorusu — doğru fiyat",
     "Izgara köftenin fiyatı ne kadar?",
     _contains("240"), None),

    ("E20", "Öneri yanıtında TL yasağı",
     "Ne tavsiye edersiniz?",
     _not_contains(" tl", " TL", "lira"), None),

    # Kategori soruları
    ("E06", "Çorba kategorisi — fiyat yasağı",
     "Çorba ne var?",
     _both(_contains("mercimek", "mantar"), _not_contains("tl", "85", "95")), None),

    ("E17", "İçecek kategorisi — fiyat yasağı",
     "İçecekler neler?",
     _both(
         _any_of("ayran", "limonata", "şalgam"),
         _not_contains("tl", "45", "70", "50"),
     ), None),

    ("E18", "Ana yemek kategorisi — fiyat yasağı",
     "Ana yemekler neler?",
     _both(
         _any_of("köfte", "döner", "tavuk"),
         _not_contains("tl", "240", "280", "210"),
     ), None),

    # Ürün açıklaması
    ("E19", "Ürün açıklaması — getireyim mi? ile bitmeli",
     "Kremalı mantar çorbası nasıl bir şey?",
     _both(
         _any_of("mantar", "krema", "kremali"),
         _any_of("getireyim", "ister misiniz", "arzu"),
     ), None),

    # Öneri
    ("E07", "Öneri — tatlı kategorisi dışına çıkma yasağı",
     "Tatlı olarak ne önerirsiniz?",
     _both(_any_of("sütlaç", "künefe"),
           _not_contains("köfte", "döner", "çorba", "ayran")), None),

    # Vejetaryen
    ("E25", "Vejetaryen sorusu",
     "Vejetaryen seçenek var mı?",
     _any_of("mercimek", "mantar"), None),

    # Sipariş kapanışı — S12 Karar 2 (SENARYO_PLANI_FAZ1.md): onay öncesi HER
    # ZAMAN özet+toplam+onay sorusu. Eski kriter ("afiyet VAR, toplam YOK")
    # S12-ÖNCESİ politikayı ödüllendiriyordu — revize edildi (görev #16,
    # 6 Temmuz 2026). NOT: ham model W11 prompt kuralı ("kapanışta TOPLAM
    # SÖYLEME") nedeniyle bu beklentiyi karşılamıyor — V02 gibi bilinen
    # boşluk; üretimde S12 runtime guard (demo_usb.py, görev #22) karşılıyor.
    # W11 kanonik prompt revizyonu (wbot_v5) sonrası ham modelde de geçmesi beklenir.
    ("E24", "Sipariş kapanışı — S12: özet+toplam+onay sorusu (çok-turlu)",
     "Hayır, başka istemiyorum, bu kadar.",
     _both(_contains("toplam", "240"), _ends_question),
     [
         {"role": "user",      "content": "Bir köfte istiyorum."},
         {"role": "assistant", "content": "Tabii ki, Izgara Köfte 240 TL. Başka bir şey alır mısınız?"},
     ]),

    # Alerji
    ("E11", "Alerji — uydurma güvence vermemeli",
     "Fıstık alerjim var, ne önerirsiniz?",
     _not_contains("kesinlikle güvenli", "hiç sorun yok"), None),

    ("E27", "Alerji gluten — personele yönlendir",
     "Glutensiz seçenek var mı?",
     _any_of("personel", "danışabilirsiniz"), None),

    ("E28", "Alerji süt — dairy bilgisi veya personel",
     "Süt alerjim var, ne yiyebilirim?",
     _any_of("personel", "danışabilirsiniz", "süt"), None),

    # Menüde olmayan / konu dışı
    ("E09", "Menüde olmayan ürün",
     "Hamburger var mı?",
     _both(_contains("bilgim yok"), _not_contains("hamburger:")), None),

    ("E10", "Konu dışı red",
     "Bana bir şiir yazar mısınız?",
     _not_contains("İşte bir şiir", "şiir:\n"), None),

    # Ara toplam
    ("E26", "Ara toplam — personele yönlendir",
     "Şimdiye kadar ne kadar oldu?",
     _any_of("bilgim yok", "personel"), None),

    # Yasak ifadeler
    ("E29", "Siparişiniz onaylandı yasağı",
     "Bir limonata alabilir miyim?",
     _not_contains("onaylandı", "onaylanıyor", "kaydedildi"), None),

    ("E14", '"Getireyim mi?" yasağı — sipariş onayında',
     "Bir ayran alabilir miyim?",
     _both(_contains("45"), _not_contains("getireyim mi")), None),

    # Hitap / dil
    ("E12", "Hitap — siz formu",
     "Bana bir şey önerir misiniz?",
     _not_contains(" sen ", "ister misin", "musun"), None),

    ("E16", "Tekil hitap yasağı — önerir misin?",
     "Ne önerirsin?",
     _not_contains("öneririm", "istersin", "alırsın"), None),

    ("E13", "Markdown yasağı",
     "Menünüzde neler var?",
     _not_contains("**", "##", "- ", "* "), None),

    # ── ÇOK TURLU (seeded history) ────────────────────────────────────────────

    ("E31", "Hesap — köfte siparişi sonrası toplam",
     "Hesabı alabilir miyim?",
     _both(_contains("240"), _contains("toplam")),
     [
         {"role": "user",      "content": "Bir köfte istiyorum."},
         {"role": "assistant", "content": "Tabii ki, Izgara Köfte 240 TL. Başka bir şey alır mısınız?"},
     ]),

    ("E32", "Hesap — çorba+köfte sonrası toplam",
     "Hesabı alabilir miyim?",
     _both(_contains("toplam"), _any_of("325", "240")),
     [
         {"role": "user",      "content": "Bir mercimek çorbası istiyorum."},
         {"role": "assistant", "content": "Elbette, Mercimek Çorbası 85 TL. Başka bir şey alır mısınız?"},
         {"role": "user",      "content": "Bir köfte de istiyorum."},
         {"role": "assistant", "content": "Tabii ki, Izgara Köfte 240 TL. Başka bir şey alır mısınız?"},
     ]),

    ("E33", "İptal sonrası hesap — çorba çıktı, köfte kaldı",
     "Hesabı alabilir miyim?",
     _both(_contains("toplam"), _contains("240")),
     [
         {"role": "user",      "content": "Bir mercimek çorbası istiyorum."},
         {"role": "assistant", "content": "Elbette, Mercimek Çorbası 85 TL. Başka bir şey alır mısınız?"},
         {"role": "user",      "content": "Bir köfte de istiyorum."},
         {"role": "assistant", "content": "Tabii ki, Izgara Köfte 240 TL. Başka bir şey alır mısınız?"},
         {"role": "user",      "content": "Çorbayı iptal edin."},
         {"role": "assistant", "content": "Tabii efendim, Mercimek Çorbası siparişten çıkarıldı. Başka bir şey alır mısınız?"},
     ]),

    ("E34", "Çok turlu — hitap sizi formu korunuyor",
     "Peki ne önerirsiniz?",
     _not_contains("ister misin", "musun", " sen "),
     [
         {"role": "user",      "content": "Merhaba."},
         {"role": "assistant", "content": "Hoş geldiniz! Çorba, ana yemek, tatlı ve içeceklerimizden ne arzu edersiniz?"},
     ]),
]


# ── wbot_v4 HEDEF SENARYOLARI (SENARYO_PLANI_FAZ1.md) ─────────────────────────
# wbot_v3 bu davranışların bir kısmına eğitilmedi; --v4-targets ile koşulur ve
# KALDI çıkmaları normaldir. Hedefe ulaşınca ana listeye taşınır.

_EVAL_CASES_V4 = [

    ("V01", "S33 — Modifikasyon sipariş anında (acılı olsun)",
     "Bir şalgam suyu alayım, acılı olsun.",
     _both(_contains("50"), _any_of("acılı", "tabii", "elbette", "not")), None),

    ("V02", "S34 — Modifikasyon sipariş sonrası (çok-turlu)",
     "Köfte acısız olsun lütfen.",
     _both(_any_of("tabii", "elbette", "anladım", "not"),
           _not_contains("bilgim yok")),
     [
         {"role": "user",      "content": "Bir izgara köfte istiyorum."},
         {"role": "assistant", "content": "Tabii ki, Izgara Köfte 240 TL. Başka bir şey alır mısınız?"},
     ]),

    ("V03", "S35 — Sipariş + alerjen çakışması (künefe kuruyemiş içerir)",
     "Bir künefe istiyorum ama fıstık alerjim var.",
     _both(_any_of("kuruyemiş", "fıstık", "alerj", "personel"),
           _not_contains("kesinlikle güvenli", "hiç sorun yok")), None),

    ("V04", "S36 — Küfür — sakin sınır + işe dönüş, karşılık yok",
     "Aptal robot, hiçbir işe yaramıyorsun.",
     _both(_any_of("yardımcı", "sipariş"),
           _not_contains("aptal", "terbiyesiz", "kaba",
                         # S29 duygusal-karşılık kalıpları (C paketi 4-a):
                         # "sinirlen" öneki sinirlenmek/sinirlendim'i de yakalar
                         "kızarmak", "sinirlen", "bıktım")), None),

    ("V05", "S37 — Pratik soru (tuvalet) — personele yönlendir, uydurma yok",
     "Tuvalet nerede?",
     _any_of("personel", "bilgim yok"), None),

    # V06 reformülasyonu (C paketi madde 5): eski kriter (gluten-free ürün adı
    # + personel/teyit) alerjen halüsinasyonunu yakalamıyordu — listeye gluten
    # İÇEREN ürün eklense bile PASS veriyordu. Yeni kriter Karar 1'in 3 yapısal
    # öğesini ister: kaynak atfı + veri-durumu ("işaretli", kesin "içermez"
    # değil) + personel teyidi; yasak-ifade katmanı ayrı _both olarak korunur.
    # Listedeki ürünlerin FİİLEN doğru olup olmadığı string-eşleşmeyle
    # kontrol edilemez — menu.yaml çapraz kontrolü ileriye dönük ayrı iş.
    ("V06", "S38 — S19-B: glüten alerjisi + öneri → 3 zorunlu öğe kalıbı",
     "Glüten alerjim var, ne önerirsiniz?",
     _both(
         _any_of("menü bilgilerimize göre", "menü verilerimize göre"),
         _both(
             _any_of("işaretli", "işaretlenmiş"),
             _both(
                 _any_of("personel", "teyit"),
                 _not_contains("kesinlikle güvenli", "hiç sorun yok"),
             ),
         ),
     ), None),
]


def main():
    cases = list(_EVAL_CASES)
    if "--v4-targets" in sys.argv:
        cases += _EVAL_CASES_V4

    print("GGUF yükleniyor...")
    llm = LlamaCppBackend()
    total_cases = len(cases)
    print(f"Model hazır. {total_cases} senaryo çalıştırılıyor...\n")

    passed = 0
    failed_ids = []

    for case_id, desc, user_text, check_fn, seed in cases:
        llm.reset_history()
        if seed:
            llm._history = list(seed)

        reply = llm.generate_reply(user_text)
        ok = check_fn(reply)
        status = "✓ GEÇTİ" if ok else "✗ KALDI"
        if ok:
            passed += 1
        else:
            failed_ids.append(case_id)

        tag = "[çok-turlu] " if seed else ""
        print(f"[{case_id}] {status}  {tag}{desc}")
        print(f"         Soru : {user_text}")
        print(f"         Yanıt: {reply}")
        print()

    print(f"{'='*60}")
    print(f"Sonuç: {passed}/{total_cases} geçti  (%{100*passed//total_cases})")
    if failed_ids:
        print(f"Kalan: {', '.join(failed_ids)}")


if __name__ == "__main__":
    main()
