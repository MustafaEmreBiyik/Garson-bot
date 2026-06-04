#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kalan 50 TL ihlalini ve 'Sipariş-başka' artışını göster."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# audit_dataset'teki güncel fonksiyonları yeniden tanımla (import yerine)
import importlib.util, types

spec = importlib.util.spec_from_file_location(
    "audit", Path("scripts/audit_dataset.py")
)
audit = importlib.util.load_from_spec(spec) if hasattr(importlib.util, "load_from_spec") else None

# ── Manuel re-impl (import yerine güvenli yol) ───────────────────────────────
def _lower(s):
    return s.lower().replace("i̇", "i").replace("İ", "i")

_PRICE_TRIGGERS  = ["kaç", "fiyat", "ne kadar", "kaç tl", "kaç lira", "ücret", "para",
                    "değeri", "tutarı", "maliyeti"]
_ORDER_TRIGGERS  = ["alayım", "istiyorum", "alabilir miyim", "alabilir miyiz",
                    "getir", "ver ", "verir misiniz", "sipariş",
                    "ekle", "ekleyin", "ekleyebilir", "rica ediyorum",
                    "olsun", "alalım", "alacağım", "alabilir miyiz"]
_BILL_TRIGGERS   = ["hesap", "hesab", "ödeyeyim", "ödeyeceğim", "ödemek istiyorum",
                    "toplam", "ödeme", "ödeyebilir", "ödeyelim", "ödeyebilirim",
                    "kapatalım", "kapatabilir misiniz", "çek gelsin", "adisyon"]
_CANCEL_TRIGGERS = ["istemiyorum", "iptal", "çıkar", "kaldır", "geri al"]
_SWAP_TRIGGERS   = ["yerine", "değiştir", "değiştirir misiniz", "değiştirebilir misiniz"]
_MENU_ITEM_TOKENS = ["mercimek", "mantar", "köfte", "döner", "tavuk salata", "sütlaç",
                     "künefe", "limonata", "ayran", "şalgam", "kola"]
PRICES = ["85", "95", "240", "280", "210", "100", "140", "45", "70", "50"]

def _ca(text, kws):
    t = _lower(text)
    return any(k in t for k in kws)

def is_ok(user):
    u = _lower(user)
    if _ca(u, _PRICE_TRIGGERS): return True
    if _ca(u, _BILL_TRIGGERS):  return True
    has_swap   = _ca(u, _SWAP_TRIGGERS)
    has_cancel = _ca(u, _CANCEL_TRIGGERS)
    has_order  = _ca(u, _ORDER_TRIGGERS)
    has_menu   = _ca(u, _MENU_ITEM_TOKENS)
    if has_swap: return True
    if has_cancel and (has_order or has_menu): return True
    if has_order and not has_cancel: return True
    if has_menu and not has_cancel: return True
    return False

def has_tl(asst):
    a = _lower(asst)
    if re.search(r"\btl\b", a) or re.search(r"\blira\b", a): return True
    return any(re.search(rf"\b{p}\b", a) for p in PRICES)

path = Path("robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl")
records = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

tl_violations = []
basika_new = []  # "başka" yok, önceden yakalanmayan turn'ler

for rec in records:
    msgs = rec["messages"]
    for i, msg in enumerate(msgs):
        if msg["role"] != "assistant": continue
        user = next((msgs[j]["content"] for j in range(i-1,-1,-1) if msgs[j]["role"]=="user"), "")
        asst = msg["content"]

        # TL ihlal
        if not is_ok(user) and has_tl(asst):
            tl_violations.append({"user": user[:120], "asst": asst[:200]})

        # "başka" eksik — swap veya cancel+order bağlamında
        if (_ca(_lower(user), _SWAP_TRIGGERS) or
                (_ca(_lower(user), _CANCEL_TRIGGERS) and
                 (_ca(_lower(user), _ORDER_TRIGGERS) or _ca(_lower(user), _MENU_ITEM_TOKENS)))):
            if "başka" not in _lower(asst):
                basika_new.append({"user": user[:120], "asst": asst[:200]})

print("=" * 60)
print(f"Kalan TL ihlali: {len(tl_violations)}")
print()
print("─" * 60)
print("TL İHLALLERİ (tümü):")
for i, ex in enumerate(tl_violations, 1):
    print(f"\n  [{i}] USER: {ex['user']}")
    print(f"      ASST: {ex['asst']}")

print()
print("=" * 60)
print(f"'Başka' eksik — swap/cancel+order turnlerinde (ilk 10):")
for ex in basika_new[:10]:
    print(f"\n  USER: {ex['user']}")
    print(f"  ASST: {ex['asst']}")
