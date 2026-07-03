#!/usr/bin/env python3
"""
audit_dataset.py — wbot dataset kural ihlali denetimi

Kullanım:
    python scripts/audit_dataset.py
    python scripts/audit_dataset.py --dataset robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl
    python scripts/audit_dataset.py --fix  # ihlalli satırları ayrı dosyaya yaz
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

_DATASET_DEFAULT = Path("robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl")

# Sistem promptu uzunluk eşikleri (karakter). Kanonik prompt 5460 karakter.
SYS_PROMPT_MIN_LEN = 1000            # altı: persona/kural içermeyen bozuk kayıt (ihlal)
SYS_PROMPT_SHORT_VARIANT_MAX = 4000  # 1000-4000 arası: kısa ama kurallı wbot_v2 varyantı (bilgi amaçlı)

# ── Kural tanımları ───────────────────────────────────────────────────────────

# Karşılama tetikleyicileri (user mesajında geçiyorsa)
# Not: "masaya" kaldırıldı — "Yan masaya daha hızlı baktınız" gibi şikayetleri önlemek için
_GREETING_TRIGGERS = ["merhaba", "selam", "hoş geldin", "günaydın", "iyi günler",
                       "iyi akşamlar", "kolay gelsin", "buyurun"]

# Genel menü sorusu (kategori adı GEÇMEDEN)
# Not: "ne yesem" ve "ne içsem" kaldırıldı — bunlar öneri talebi, genel menü sunusu değil
_MENU_TRIGGERS = ["ne var", "neler var", "menü", "ne yiyebilirim", "ne alabilirim",
                   "sipariş vermek"]

# Kategori adları (bunlar geçiyorsa karşılama kuralı uygulanmaz)
_CATEGORY_KEYWORDS = ["çorba", "ana yemek", "tatlı", "içecek"]

# Sipariş tetikleyicileri (DAR — yalnızca başka/getireyim check'leri için)
_ORDER_TRIGGERS = ["alayım", "istiyorum", "alabilir miyim", "alabilir miyiz",
                    "getir", "ver ", "verir misiniz", "sipariş"]

# Fiyat sorusu tetikleyicileri
_PRICE_TRIGGERS = ["kaç", "fiyat", "ne kadar", "kaç tl", "kaç lira", "ücret", "para",
                   "değeri", "tutarı", "maliyeti"]

# Bütçe/karşılaştırma soruları — fiyat söylemenin geçerli olduğu dolaylı bağlam
_BUDGET_TRIGGERS = [
    "ucuz", "pahalı", "uygun", "hesaplı", "bütçe", "bütçem",
    "liram var", "liran var", "liraya", "liramla",
    "tl var", "tl'm var", "tl bütçe",
    "en az", "en çok", "en pahalı", "en ucuz",
    "cebime", "karşılar mı", "doyar mı", "yeter mi",
    "borç", "borcum",
]

# Hesap tetikleyicileri — Türkçe morfoloji: "hesap" → "hesabı/hesabını/hesabımızı" (p→b)
_BILL_TRIGGERS = ["hesap", "hesab", "ödeyeyim", "ödeyeceğim", "ödemek istiyorum",
                  "toplam", "ödeme", "ödeyebilir", "ödeyelim", "ödeyebilirim",
                  "kapatalım", "kapatabilir misiniz", "çek gelsin", "adisyon"]

# İptal tetikleyicileri
_CANCEL_TRIGGERS = ["istemiyorum", "iptal", "çıkar", "kaldır", "geri al"]

# Takas tetikleyicileri — "yerine" hem iptal hem sipariş içerir, fiyat söylenebilir
_SWAP_TRIGGERS = ["yerine", "değiştir", "değiştirir misiniz", "değiştirebilir misiniz"]

# Menü ürün adları — fiilsiz örtük siparişleri (bare orders) tanımak için
_MENU_ITEM_TOKENS = [
    "mercimek", "mantar", "köfte", "döner", "tavuk salata", "salata",
    "sütlaç", "künefe", "limonata", "ayran", "şalgam", "kola",
]

# Sipariş onayı için menü ürünü tokenleri — "başka" check'i için güvenli liste.
# "et" ve "su" hariç (çok kısa, getirir/yeterli/sushi gibi kelimelerde yanlış eşleşiyor).
# "kola" ayrı: "kolay" ile karışmaması için _is_specific_order_turn içinde regex kullanılır.
_ORDER_FOOD_TOKENS = [
    "mercimek", "mantar", "köfte", "döner", "tavuk", "sütlaç", "künefe", "tatlı",
    "limonata", "ayran", "şalgam", "içecek", "salata", "ana yemek", "çorba",
]

# "başka" semantik eşdeğerleri — sipariş onayında bunlardan biri yeterli
_BASIT_EQUIVALENTS = [
    "başka",
    "eklemek istediğiniz",
    "ekleyeceğimiz",
    "ilaveten",
    "ekleyelim mi",      # "Siparişinize ekleyelim mi?" — ön-onay ama kabul
    "onaylıyor musunuz", # fiyat doğrulama adımı
]

# Off-menu / yönlendirme yanıt işaretçileri — "başka" ve "toplam" kuralından muaf
_REDIRECT_MARKERS = [
    "personelimize",
    "bilgim yok",
    "yardımcı olamıyorum",
]

# Diyet/alerji kısıt belirteçleri — spesifik soru, genel menü sunusu gerekmez
_DIETARY_MARKERS = [
    "gluten", "glüten",
    "alerji", "alerjen",
    "vejetaryen", "vegan",
    "etsiz", "et yemiyor", "et yemiyorum", "et olmayan", "et içermeyen",
    "sütsüz", "süt ürünü", "laktoz", "lakto",
    "helal", "soya",
    "diyet",
    "protein ağırlıklı",
    "sebze",
]

# Menü-dışı şikayet/öneri kalıpları — menü sunusu gerekmez
_OFFMENU_MARKERS = [
    "neden menüde yok",
    "yoksa bile",
    "menüde yok",
    "menüde yoksa",
    "menünüzde yok",
    "menünüzde yoksa",
]

# Kullanıcı vedası belirteçleri — karşılama değil, ayrılış
_FAREWELL_USER_MARKERS = [
    "kalkıyoruz", "çıkıyoruz", "gidiyoruz", "gidiyorum",
    "güle güle",
    "sağlıcakla",
    "ellerinize sağlık", "elinize sağlık",
    "iyi çalışmalar",
    "kaçalım",
    "veda",
    "keyifli bir yemekti",
]

# Acele/zaman baskısı — spesifik öneri isteniyor, 4 kategori sunusu değil
_URGENCY_MARKERS = [
    "acelem var", "acelem",
    "vaktim yok", "vaktim dar",
    "otobüs kalkacak",
    "uçağım",
    "koşturuyorum",
    "hızlı",      # "hızlı ne var?", "ne hızlı çıkar?" — zaman kısıtlı sorgu
    "çabuk ne",
]

# Öneri isteği niteleme belirteçleri — spesifik öneri, genel menü değil
_RECOMMENDATION_QUALIFIERS = [
    "hafif",
    "ağır olmayan",
    "öne çıkan",
    "ne iyi gidiyor",
    "en çok tercih",
    "karar veremiyorum",
    "karar veremedim",
    "doyurucu",
]

# Bot yanıtında veda belirteçleri — ayrılış yanıtı, menü sunusu beklenmez
_FAREWELL_RESPONSE_MARKERS = [
    "afiyet olsun",
    "tekrar bekleriz", "yine bekleriz", "tekrar bekliyoruz",
    "her zaman bekleriz",
    "iyi günler dileriz", "iyi akşamlar dileriz",
    "sağ olun",
]

# Adet güncelleme kalıpları ("iki tane yapalım", "ikiye düşürelim" vb.)
_QTY_TRIGGERS = [
    "iki tane", "bir tane", "üç tane", "dört tane",
    "iki adet", "bir adet", "üç adet",
    "ikiye", "üçe", "dörde",
    "yapalım", "düşürelim", "yükseltelim",
    "olsun",  # "çorbalar 4 olsun", "iki olsun" gibi adet güncelleme kalıpları
]

# Yasak ifadeler (assistant yanıtında asla geçmemeli)
_FORBIDDEN_PHRASES = [
    "siparişiniz onaylandı",
    "onaylanıyor",
    "kaydedildi",
]


def _lower(s: str) -> str:
    return s.lower().replace("i̇", "i").replace("İ", "i")


def _contains_any(text: str, keywords: list[str]) -> bool:
    t = _lower(text)
    return any(kw in t for kw in keywords)


def _contains_all(text: str, keywords: list[str]) -> bool:
    t = _lower(text)
    return all(kw in t for kw in keywords)


def _is_greeting_turn(user: str) -> bool:
    """Kullanıcı mesajı genel karşılama / açık menü sorusu mu?

    Yalnızca kısıtsız genel sorgular için True döner.
    Diyet, bütçe, acele, veda ve menü-dışı sorguları hariç tutar.
    """
    u = _lower(user)
    has_greeting = _contains_any(u, _GREETING_TRIGGERS)
    has_menu_q   = _contains_any(u, _MENU_TRIGGERS)
    # Kategori adı veya sipariş geçiyorsa bu kural uygulanmaz
    if _contains_any(u, _CATEGORY_KEYWORDS) or _contains_any(u, _ORDER_TRIGGERS):
        return False
    # Hesap/ödeme bağlamı — kapanış turu
    if _is_bill_turn(user):
        return False
    # Bütçe / fiyat bağlamı — spesifik öneri talebi
    if (_contains_any(u, _PRICE_TRIGGERS) or _contains_any(u, _BUDGET_TRIGGERS)
            or re.search(r'\btl\b', u)):
        return False
    # Diyet / alerji kısıtı — spesifik soru
    if _contains_any(u, _DIETARY_MARKERS):
        return False
    # Menü-dışı şikayet veya öneri
    if _contains_any(u, _OFFMENU_MARKERS):
        return False
    # Kullanıcı vedası — ayrılış turu
    if _contains_any(u, _FAREWELL_USER_MARKERS):
        return False
    # Acele / zaman baskısı — spesifik öneri isteniyor
    if _contains_any(u, _URGENCY_MARKERS):
        return False
    # Nitelenmiş öneri isteği — "hafif ne var?", "öne çıkan ne?" vb.
    if _contains_any(u, _RECOMMENDATION_QUALIFIERS):
        return False
    return has_greeting or has_menu_q


def _is_order_turn(user: str) -> bool:
    """Sipariş onayı beklenen tur — dar tanım (başka/getireyim check'leri için)."""
    return _contains_any(user, _ORDER_TRIGGERS) and not _contains_any(user, _CANCEL_TRIGGERS)


def _is_specific_order_turn(user: str) -> bool:
    """Belirli bir menü ürünü siparişi — 'başka' kuralı için dar ve güvenli tanım.

    Hem ORDER_TRIGGER hem de menü ürün tokeni içermeli.
    'kola' için word-boundary regex kullanılır ('kolay' ile karışmaması için).
    """
    if _contains_any(user, _CANCEL_TRIGGERS):
        return False
    if not _contains_any(user, _ORDER_TRIGGERS):
        return False
    u = _lower(user)
    if _contains_any(u, _ORDER_FOOD_TOKENS):
        return True
    if re.search(r'\bkola\b', u):
        return True
    return False


def _is_price_turn(user: str) -> bool:
    return _contains_any(user, _PRICE_TRIGGERS)


def _is_bill_turn(user: str) -> bool:
    u = _lower(user)
    # "hesaplı" → bütçe karşılaştırması; "hesap" substringi eşleşmesin
    u_checked = u.replace("hesaplı", "").replace("hesapli", "")
    return _contains_any(u_checked, _BILL_TRIGGERS)


def _is_valid_price_context(user: str) -> bool:
    """Fiyat söylemenin geçerli olduğu TÜM bağlamlar — geniş tanım (TL check için).

    Geçerli bağlamlar:
      1. Açık fiyat sorusu ("kaç TL", "fiyatı ne")
      2. Bütçe/karşılaştırma sorusu ("en ucuz", "100 liram var")
      3. Hesap/ödeme isteği ("hesabı alabilir miyim", "hesabı kapatalım")
      4. Düz sipariş ("köfte istiyorum")
      5. Takas ("köfte yerine ayran")
      6. İptal + yeni sipariş aynı anda ("şalgam iptal, köfte alayım")
      7. Fiilsiz örtük sipariş ("iki köfte", "bir salata")
      8. Adet güncelleme ("iki tane yapalım", "ikiye düşürelim")
    """
    u = _lower(user)
    if _contains_any(u, _PRICE_TRIGGERS):   return True
    if _contains_any(u, _BUDGET_TRIGGERS):  return True
    if _contains_any(u, _BILL_TRIGGERS):    return True
    if re.search(r'\btl\b', u):             return True  # user TL/para miktarı söylüyor
    if _is_order_turn(user):                return True
    if _contains_any(u, _SWAP_TRIGGERS):    return True
    if _contains_any(u, _QTY_TRIGGERS):     return True
    has_cancel = _contains_any(u, _CANCEL_TRIGGERS)
    has_order  = _contains_any(u, _ORDER_TRIGGERS)
    has_menu   = _contains_any(u, _MENU_ITEM_TOKENS)
    if has_cancel and (has_order or has_menu): return True
    if has_menu and not has_cancel:            return True
    return False


# ── Kural kontrolleri ─────────────────────────────────────────────────────────

def check_greeting_4cats(user: str, asst: str) -> str | None:
    """Karşılamada 4 kategori adı geçmeli."""
    if not _is_greeting_turn(user):
        return None
    a = _lower(asst)
    # Bot veda yanıtı döndürüyorsa menü sunusu beklenmez
    if _contains_any(a, _FAREWELL_RESPONSE_MARKERS):
        return None
    # Bot yönlendiriyor veya bilgisi yok
    if _contains_any(a, _REDIRECT_MARKERS):
        return None
    # Bot anlayamadı — karşılama yanıtı değil
    if "anlayamadım" in a:
        return None
    missing = [c for c in _CATEGORY_KEYWORDS if c not in a]
    if missing:
        return f"Karşılamada eksik kategori: {missing}"
    return None


def check_order_has_basit(user: str, asst: str) -> str | None:
    """Sipariş onayında 'başka' veya semantik eşdeğeri geçmeli."""
    if not _is_specific_order_turn(user):
        return None
    # Kullanıcı aynı mesajda hesap/ödeme de istiyorsa kapanış turu — 'başka' gerekmez
    if _is_bill_turn(user):
        return None
    a = _lower(asst)
    # Off-menu yönlendirme veya "anlayamadım" yanıtı: 'başka' gerekmez
    if _contains_any(a, _REDIRECT_MARKERS):
        return None
    # 'başka' veya kabul gören eşdeğerlerden biri yeterli
    if _contains_any(a, _BASIT_EQUIVALENTS):
        return None
    return "'başka' veya eşdeğeri eksik sipariş onayında"


def check_getireyim_mi(user: str, asst: str) -> str | None:
    """Sipariş onayında 'Getireyim mi?' yasak."""
    if not _is_order_turn(user):
        return None
    if "getireyim mi" in _lower(asst):
        return "'Getireyim mi?' yasağı ihlali (sipariş onayında)"
    return None


def check_tl_in_wrong_context(user: str, asst: str) -> str | None:
    """Fiyat/sipariş/hesap dışında 'TL' geçmemeli."""
    if _is_valid_price_context(user):
        return None
    a = _lower(asst)
    # "tl" substring kontrolü — kelimenin parçası değil mi diye bak
    # "memnuniyetle" gibi yanlış tetiklemeyi önle
    if re.search(r'\btl\b', a) or re.search(r'\blira\b', a):
        return "Fiyat bağlamı dışında 'TL/lira' kullanımı"
    # Sayısal fiyat kontrolü (menüdeki fiyatlar)
    prices = ["85", "95", "240", "280", "210", "100", "140", "45", "70", "50"]
    for p in prices:
        if re.search(rf'\b{p}\b', a):
            return f"Fiyat bağlamı dışında sayısal fiyat ({p}) kullanımı"
    return None


def check_forbidden_phrases(user: str, asst: str) -> str | None:
    """Yasak ifade kontrolü."""
    a = _lower(asst)
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in a:
            return f"Yasak ifade: '{phrase}'"
    return None


def check_markdown(user: str, asst: str) -> str | None:
    """Markdown/liste işareti yasak."""
    if re.search(r'(\*\*|##|^- |^\* )', asst, re.MULTILINE):
        return "Markdown/liste işareti kullanımı"
    return None


def check_sen_form(user: str, asst: str) -> str | None:
    """'sen' formu yasak — 'ister misiniz' / 'musunuz' ile karışmamalı."""
    a = _lower(asst)
    # Negatif lookahead ile sadece tekil formu yakala
    bad_patterns = [
        (r'ister misin(?!iz)', "ister misin"),
        (r'\bmusun(?!uz)\b', "musun"),
        (r'\bistiyorsun\b', "istiyorsun"),
        (r'\bsana\b', "sana"),
        (r'\bbeğendin\b', "beğendin"),
    ]
    for pattern, label in bad_patterns:
        if re.search(pattern, a):
            return f"Tekil hitap formu: '{label}'"
    return None


def check_hesap_format(user: str, asst: str) -> str | None:
    """Hesap yanıtında 'toplam' geçmeli — yalnızca tutar belirtildiğinde."""
    if not _is_bill_turn(user):
        return None
    a = _lower(asst)
    # Bot yönlendiriyor: tutarı bilmiyor, personele/kasaya gönderiyor → muaf
    if _contains_any(a, _REDIRECT_MARKERS):
        return None
    # Bot tutarı belirtmiyorsa (deferral: "hemen getiriyorum", "birazdan" vb.) → muaf
    if not re.search(r'\btl\b', a) and not re.search(r'\d{2,}', a):
        return None
    # Tutar var ama "toplam" yok → gerçek ihlal
    if "toplam" not in a:
        return "Hesap yanıtında 'toplam' eksik"
    return None


def check_system_prompt_length(record: dict) -> str | None:
    """Sistem promptu minimum uzunlukta olmalı — persona/kural içermeyen bozuk kayıtları yakalar."""
    messages = record.get("messages", [])
    if not messages or messages[0].get("role") != "system":
        return None
    length = len(messages[0].get("content", ""))
    if length < SYS_PROMPT_MIN_LEN:
        return f"Sistem promptu çok kısa ({length} karakter, minimum {SYS_PROMPT_MIN_LEN} bekleniyor)"
    return None


def check_system_prompt_short_variant(record: dict) -> str | None:
    """Bilgilendirici: kısa-ama-kurallı wbot_v2 varyantını ayrı raporlar, ihlal saymaz."""
    messages = record.get("messages", [])
    if not messages or messages[0].get("role") != "system":
        return None
    length = len(messages[0].get("content", ""))
    if SYS_PROMPT_MIN_LEN <= length < SYS_PROMPT_SHORT_VARIANT_MAX:
        return f"Kısa varyant sistem promptu ({length} karakter)"
    return None


CHECKS = [
    check_greeting_4cats,
    check_order_has_basit,
    check_getireyim_mi,
    check_tl_in_wrong_context,
    check_forbidden_phrases,
    check_markdown,
    check_sen_form,
    check_hesap_format,
]

CHECK_NAMES = [
    "Karşılama-4kategori",
    "Sipariş-başka",
    "Getireyim-mi yasağı",
    "TL-yanlış bağlam",
    "Yasak ifade",
    "Markdown",
    "Sen formu",
    "Hesap-toplam",
]


# ── Ana denetim ───────────────────────────────────────────────────────────────

def audit_record(record: dict, rec_idx: int) -> list[dict]:
    """Bir kayıttaki tüm ihlalleri döndür."""
    violations = []
    messages = record.get("messages", [])

    sys_result = check_system_prompt_length(record)
    if sys_result:
        violations.append({
            "record":  rec_idx,
            "turn":    "system",
            "check":   "Sistem-promptu-uzunluk",
            "detail":  sys_result,
            "user":    "",
            "asst":    messages[0]["content"][:120] if messages else "",
        })

    for i, msg in enumerate(messages):
        if msg["role"] != "assistant":
            continue
        # Bir önceki user mesajını bul
        user_msg = ""
        for j in range(i - 1, -1, -1):
            if messages[j]["role"] == "user":
                user_msg = messages[j]["content"]
                break
        asst_msg = msg["content"]
        for check_fn, check_name in zip(CHECKS, CHECK_NAMES):
            result = check_fn(user_msg, asst_msg)
            if result:
                violations.append({
                    "record":  rec_idx,
                    "turn":    i,
                    "check":   check_name,
                    "detail":  result,
                    "user":    user_msg[:80],
                    "asst":    asst_msg[:120],
                })
    return violations


def main():
    ap = argparse.ArgumentParser(description="Dataset kural ihlali denetimi")
    ap.add_argument("--dataset", default=str(_DATASET_DEFAULT))
    ap.add_argument("--fix", action="store_true",
                    help="İhlalli kayıtları violations.jsonl olarak yaz")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="Her ihlali tam göster")
    args = ap.parse_args()

    path = Path(args.dataset)
    if not path.exists():
        print(f"Dataset bulunamadı: {path}")
        return

    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"Dataset: {path}")
    print(f"Kayıt sayısı: {len(records)}\n")

    all_violations: list[dict] = []
    violated_records: set[int] = set()

    for i, rec in enumerate(records):
        viols = audit_record(rec, i)
        if viols:
            violated_records.add(i)
            all_violations.extend(viols)

    # ── Özet ──────────────────────────────────────────────────────────────
    by_check: dict[str, int] = defaultdict(int)
    for v in all_violations:
        by_check[v["check"]] += 1

    print("=" * 60)
    print("DENETIM SONUÇLARI")
    print("=" * 60)
    print(f"\nToplam ihlal      : {len(all_violations)}")
    print(f"İhlalli kayıt     : {len(violated_records)} / {len(records)}"
          f"  ({100*len(violated_records)//len(records)}%)")
    print(f"Temiz kayıt       : {len(records)-len(violated_records)} / {len(records)}"
          f"  ({100*(len(records)-len(violated_records))//len(records)}%)")

    print("\nKural bazında ihlal sayısı:")
    for name in CHECK_NAMES:
        count = by_check.get(name, 0)
        bar = "█" * min(count // 5, 40)
        print(f"  {name:<25} {count:>4}  {bar}")

    sys_len_count = by_check.get("Sistem-promptu-uzunluk", 0)
    bar = "█" * min(sys_len_count // 5, 40)
    print(f"  {'Sistem-promptu-uzunluk':<25} {sys_len_count:>4}  {bar}")

    # ── Bilgi (ihlal sayılmaz): kısa-ama-kurallı wbot_v2 varyantı ───────────
    short_variant_records: set[int] = {
        i for i, rec in enumerate(records) if check_system_prompt_short_variant(rec)
    }
    print(f"\n[Bilgi] Kısa varyant sistem promptu (ihlal SAYILMAZ): "
          f"{len(short_variant_records)} / {len(records)}")

    if args.verbose:
        print("\n" + "─" * 60)
        print("DETAYLI İHLALLER")
        print("─" * 60)
        for v in all_violations:
            print(f"\n[Kayıt {v['record']:4d} | Tur {v['turn']}] {v['check']}")
            print(f"  Kural  : {v['detail']}")
            print(f"  Kullanıcı : {v['user']}")
            print(f"  Asistan   : {v['asst']}")

    if args.fix:
        out = path.parent / (path.stem + "_violations.jsonl")
        bad_indices = violated_records
        with open(out, "w", encoding="utf-8") as f:
            for i in sorted(bad_indices):
                f.write(json.dumps(records[i], ensure_ascii=False) + "\n")
        print(f"\nİhlalli kayıtlar yazıldı: {out}  ({len(bad_indices)} kayıt)")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    main()
