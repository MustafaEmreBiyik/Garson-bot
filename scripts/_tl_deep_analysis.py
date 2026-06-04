#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TL ihlal kategorilerini derinlemesine analiz et.
Hangi user kalıpları audit'in yanlış pozitif ürettiğini bulur,
gerçek ihlalleri (öneri/tanıtım/sohbet bağlamı) ortaya çıkarır.
"""
import json, re, sys
from collections import Counter
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def _lower(s):
    return s.lower().replace("i̇", "i").replace("İ", "i")

# ── Audit script'teki orijinal tetikleyiciler ────────────────────────────────
_PRICE_TRIGGERS  = ["kaç", "fiyat", "ne kadar", "kaç tl", "kaç lira", "ücret", "para"]
_ORDER_TRIGGERS  = ["alayım", "istiyorum", "alabilir miyim", "alabilir miyiz",
                    "getir", "ver ", "verir misiniz", "sipariş"]
_BILL_TRIGGERS   = ["hesap", "ödeyeyim", "ödeyeceğim", "ödemek istiyorum", "toplam"]
_CANCEL_TRIGGERS = ["istemiyorum", "iptal", "çıkar", "kaldır", "geri al", "yerine"]

# ── Genişletilmiş bill/price tetikleyiciler ──────────────────────────────────
_BILL_EXTENDED = [
    "hesap", "hesabı", "hesabi", "ödeme", "ödemek", "ödeyeyim",
    "ödeyeceğim", "ödemek istiyorum", "toplam", "ücret öde",
    "parayı öde", "kapat", "çek hesab"
]
_PRICE_EXTENDED = [
    "kaç", "fiyat", "ne kadar", "kaç tl", "kaç lira", "ücret", "para",
    "değeri", "maliyeti", "tutarı", "tutar"
]

def is_ok_original(user):
    u = _lower(user)
    if any(k in u for k in _PRICE_TRIGGERS):  return True
    if any(k in u for k in _BILL_TRIGGERS):   return True
    if (any(k in u for k in _ORDER_TRIGGERS)
            and not any(k in u for k in _CANCEL_TRIGGERS)): return True
    return False

def is_ok_extended(user):
    u = _lower(user)
    if any(k in u for k in _PRICE_EXTENDED):  return True
    if any(k in u for k in _BILL_EXTENDED):   return True
    if (any(k in u for k in _ORDER_TRIGGERS)
            and not any(k in u for k in _CANCEL_TRIGGERS)): return True
    return False

PRICES = ["85", "95", "240", "280", "210", "100", "140", "45", "70", "50"]

def has_tl(asst):
    a = _lower(asst)
    if re.search(r"\btl\b", a) or re.search(r"\blira\b", a): return True
    return any(re.search(rf"\b{p}\b", a) for p in PRICES)

path = Path("robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl")
records = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

false_positives = []   # audit diyor ihlal ama aslında doğru
real_violations = []   # gerçekten yanlış bağlamda TL
user_counter = Counter()

for rec in records:
    msgs = rec["messages"]
    for i, msg in enumerate(msgs):
        if msg["role"] != "assistant":
            continue
        user = next(
            (msgs[j]["content"] for j in range(i - 1, -1, -1) if msgs[j]["role"] == "user"),
            ""
        )
        if not has_tl(msg["content"]):
            continue
        ok_orig = is_ok_original(user)
        ok_ext  = is_ok_extended(user)

        if ok_orig:
            continue  # audit zaten temiz sayıyor, atla

        if ok_ext and not ok_orig:
            # audit yanlış pozitif: orijinal yakaladı ama genişletilmiş temiz
            false_positives.append({"user": user[:120], "asst": msg["content"][:200]})
        elif not ok_ext:
            # gerçek ihlal: her iki versiyonda da yakalandı
            real_violations.append({"user": user[:120], "asst": msg["content"][:200]})
            # user kalıbını say
            u_short = _lower(user).strip()[:60]
            user_counter[u_short] += 1

print("=" * 60)
print(f"Toplam kayıt: {len(records)}")
print(f"Audit'in 'ihlal' dediği ama aslında DOĞRU (yanlış pozitif): {len(false_positives)}")
print(f"Gerçek TL ihlalleri (öneri/tanıtım/sohbet bağlamı): {len(real_violations)}")
print()

print("─" * 60)
print("YANLIŞ POZİTİF örnekler (ilk 5):")
for ex in false_positives[:5]:
    print(f"  USER: {ex['user']}")
    print(f"  ASST: {ex['asst']}")
    print()

print("─" * 60)
print("GERÇEK İHLAL örnekler (ilk 15):")
for ex in real_violations[:15]:
    print(f"  USER: {ex['user']}")
    print(f"  ASST: {ex['asst']}")
    print()

print("─" * 60)
print("En sık gerçek ihlal user kalıpları (Top 20):")
for pattern, count in user_counter.most_common(20):
    print(f"  {count:4d}x  {pattern}")
