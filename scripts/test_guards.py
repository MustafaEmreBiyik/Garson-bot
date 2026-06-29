"""
Guard 1 (STT düşük güven) + Guard 2 (menü-dışı sipariş) unit testleri.
demo_usb.py'ye bağımlılık yok — guard sabitlerini ve fonksiyonlarını
buraya kopyalar, sadece stdlib + yaml kullanır.
"""

import sys
import yaml
from pathlib import Path

# ── Sabitler (demo_usb.py'den kopyalandı) ────────────────────────────────────
_ORDER_VERBS = {
    "istiyorum", "istiyoruz", "ister misiniz", "alabilir miyim",
    "alabilir miyiz", "alayım", "alalım", "alır mısınız", "getirir misiniz",
    "getirin", "sipariş", "ver", "verir misiniz", "verin",
}
_QUANTITIES = {
    "bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5,
    "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10,
    "yarım": 0.5, "çift": 2, "tek": 1,
}
_STT_LANG_PROB_MIN   = 0.50
_STT_MIN_WORDS_FRESH = 2
_VAGUE_TERMS         = {"şey", "şeyler", "birşey", "birşeyler"}
_CONFIRM_STARTS      = {"evet", "hayır", "tabii", "tamam", "olur", "olmaz", "peki", "kesinlikle"}

# ── Menü yükle ───────────────────────────────────────────────────────────────
def _load_menu_lookup():
    menu_path = Path(__file__).parent.parent / "robot_waiter_ai" / "data" / "menu.yaml"
    with open(menu_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    items = data.get("menu", data.get("menu_items", [])) if isinstance(data, dict) else data
    lookup = []
    for item in items:
        aliases = [a.lower() for a in item.get("aliases", [])]
        aliases.append(item["name"].lower())
        lookup.append((aliases, item["name"], item["price"]))
    return lookup

def _match_items(text: str, lookup: list):
    t = text.lower().replace('̇', '')
    found = []
    for aliases, name, price in lookup:
        for alias in aliases:
            if alias in t:
                found.append((name, price, 1))
                break
    return found

# ── Guard fonksiyonları (demo_usb.py'den kopyalandı) ─────────────────────────
def _stt_low_confidence(result: dict, text: str, *, in_convo: bool) -> bool:
    lang_prob = result.get("language_probability", 1.0)
    if lang_prob < _STT_LANG_PROB_MIN:
        return True
    if not in_convo and len(text.split()) <= _STT_MIN_WORDS_FRESH:
        return True
    return False

def _is_off_menu_order(text: str, lookup: list, *, in_convo: bool) -> bool:
    t = text.lower().replace('̇', '')
    if not any(v in t for v in _ORDER_VERBS):
        return False
    if _match_items(t, lookup):
        return False
    if any(vague in t for vague in _VAGUE_TERMS):
        return False
    words = t.split()
    if not words or words[0] in _CONFIRM_STARTS:
        return False
    _STOPWORDS = {"bir", "de", "da", "ile", "ve", "mi", "mı", "mu", "mü",
                  "lütfen", "acaba", "bana", "bize", "buraya"}
    noise = _ORDER_VERBS | set(_QUANTITIES.keys()) | _STOPWORDS
    content_words = [w for w in words if w not in noise]
    return len(content_words) >= 1

# ── Testler ───────────────────────────────────────────────────────────────────
def run_tests():
    lookup = _load_menu_lookup()
    print(f"Menü yüklendi: {len(lookup)} ürün\n")

    passed = 0
    failed = 0

    def check(label, result, expected):
        nonlocal passed, failed
        ok = result == expected
        mark = "✓" if ok else "✗"
        status = "OK" if ok else f"FAIL (beklenen={expected}, gelen={result})"
        print(f"  {mark}  {label} → {status}")
        if ok:
            passed += 1
        else:
            failed += 1

    # ── Guard 1 ───────────────────────────────────────────────────────────────
    print("=== Guard 1: STT düşük güven ===")

    check("lang_prob=0.3 fresh",
          _stt_low_confidence({"language_probability": 0.3}, "adana kebap istiyorum", in_convo=False),
          True)

    check("lang_prob=0.4 in_convo",
          _stt_low_confidence({"language_probability": 0.4}, "evet", in_convo=True),
          True)

    check("1 kelime fresh ('al')",
          _stt_low_confidence({"language_probability": 0.9}, "al", in_convo=False),
          True)

    check("2 kelime fresh (≤ eşik)",
          _stt_low_confidence({"language_probability": 0.9}, "köfte ver", in_convo=False),
          True)

    check("'evet' in_convo → geçmeli",
          _stt_low_confidence({"language_probability": 0.9}, "evet", in_convo=True),
          False)

    check("'tamam' in_convo → geçmeli",
          _stt_low_confidence({"language_probability": 0.9}, "tamam", in_convo=True),
          False)

    check("Normal metin fresh → geçmeli",
          _stt_low_confidence({"language_probability": 0.95}, "mercimek çorbası alayım", in_convo=False),
          False)

    check("3 kelime fresh → geçmeli",
          _stt_low_confidence({"language_probability": 0.9}, "köfte istiyorum lütfen", in_convo=False),
          False)

    # ── Guard 2 ───────────────────────────────────────────────────────────────
    print("\n=== Guard 2: Menü-dışı sipariş ===")

    check("'Adana kebap istiyorum' → menü dışı",
          _is_off_menu_order("Adana kebap istiyorum", lookup, in_convo=False),
          True)

    check("'Pizza alabilir miyim' → menü dışı",
          _is_off_menu_order("Pizza alabilir miyim", lookup, in_convo=False),
          True)

    check("'Lahmacun getirin' → menü dışı",
          _is_off_menu_order("Lahmacun getirin", lookup, in_convo=False),
          True)

    check("'Köfte istiyorum' → menüde var, geçmeli",
          _is_off_menu_order("Köfte istiyorum", lookup, in_convo=False),
          False)

    check("'Birşey alayım' → belirsiz, geçmeli",
          _is_off_menu_order("Birşey alayım", lookup, in_convo=False),
          False)

    check("'Evet alayım' → onay başlangıcı, geçmeli",
          _is_off_menu_order("Evet alayım", lookup, in_convo=False),
          False)

    check("'İstiyorum' sadece fiil → geçmeli",
          _is_off_menu_order("İstiyorum", lookup, in_convo=False),
          False)

    check("'Merhaba iyi günler' → fiil yok, geçmeli",
          _is_off_menu_order("Merhaba iyi günler", lookup, in_convo=False),
          False)

    check("'Adana kebap ve ayran istiyorum' → ayran menüde, geçmeli",
          _is_off_menu_order("Adana kebap ve ayran istiyorum", lookup, in_convo=False),
          False)

    # ── Özet ─────────────────────────────────────────────────────────────────
    print(f"\n{'='*40}")
    print(f"Sonuç: {passed} geçti, {failed} başarısız")
    if failed:
        print("⚠  Bazı testler başarısız!")
        sys.exit(1)
    else:
        print("✅ Tüm testler geçti")

if __name__ == "__main__":
    run_tests()
