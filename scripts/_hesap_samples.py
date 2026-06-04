#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hesap-toplam ihlallerini kategorize et."""
import json, re, sys
from collections import Counter
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def _lower(s):
    return s.lower().replace("i̇", "i").replace("İ", "i")

def _ca(text, kws):
    t = _lower(text)
    return any(k in t for k in kws)

_BILL_TRIGGERS = ["hesap", "hesab", "ödeyeyim", "ödeyeceğim", "ödemek istiyorum",
                  "toplam", "ödeme", "ödeyebilir", "ödeyelim", "ödeyebilirim",
                  "kapatalım", "kapatabilir misiniz", "çek gelsin", "adisyon"]

def is_bill_turn(user):
    return _ca(user, _BILL_TRIGGERS)

path = Path("robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl")
records = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

violations = []
for rec in records:
    msgs = rec["messages"]
    for i, msg in enumerate(msgs):
        if msg["role"] != "assistant":
            continue
        user = next((msgs[j]["content"] for j in range(i-1,-1,-1) if msgs[j]["role"]=="user"), "")
        asst = msg["content"]
        if is_bill_turn(user) and "toplam" not in _lower(asst):
            violations.append({"user": user, "asst": asst})

print(f"Toplam Hesap-toplam ihlali: {len(violations)}\n")

# Kategorize et
# A: Bot "Bu konuda bilgim yok / personelimize" diyor — yanlış pozitif mı?
# B: Bot doğru davranıyor ama "toplam" yerine "tutar" / "TL" kullanıyor
# C: Bot başka yanıt veriyor (anlayamadım, tekrar vb.)
# D: Gerçek ihlal — hesap yanıtı ama "toplam" yok

cat_a = []  # redirect
cat_b = []  # tutar/TL ama toplam yok
cat_c = []  # anlayamadım / tekrar
cat_d = []  # diğer / gerçek ihlal

_REDIRECT = ["personelimize", "bilgim yok", "yardımcı olamıyorum"]
_CLARIFY  = ["anlayamadım", "tekrar", "lütfen açıklar", "hangi masanın"]

for v in violations:
    a = _lower(v["asst"])
    if _ca(a, _REDIRECT):
        cat_a.append(v)
    elif _ca(a, _CLARIFY):
        cat_c.append(v)
    elif re.search(r'\btl\b', a) or "tutar" in a or "lira" in a:
        cat_b.append(v)
    else:
        cat_d.append(v)

print(f"A. Redirect 'personelimize/bilgim yok' (false positive?): {len(cat_a)}")
print(f"B. 'TL/tutar' var ama 'toplam' yok:                       {len(cat_b)}")
print(f"C. Anlayamadım/tekrar yanıtı:                              {len(cat_c)}")
print(f"D. Diğer (potansiyel gerçek ihlal):                       {len(cat_d)}")
print()

print("=" * 60)
print("A örnekleri (ilk 8) — redirect:")
for v in cat_a[:8]:
    print(f"  USER: {v['user'][:100]}")
    print(f"  ASST: {v['asst'][:150]}")
    print()

print("=" * 60)
print("B örnekleri (tümü) — TL/tutar ama toplam yok:")
for v in cat_b:
    print(f"  USER: {v['user'][:100]}")
    print(f"  ASST: {v['asst'][:150]}")
    print()

print("=" * 60)
print("C örnekleri — anlayamadım:")
for v in cat_c:
    print(f"  USER: {v['user'][:100]}")
    print(f"  ASST: {v['asst'][:150]}")
    print()

print("=" * 60)
print("D örnekleri — diğer/gerçek ihlal (tümü):")
for v in cat_d:
    print(f"  USER: {v['user'][:100]}")
    print(f"  ASST: {v['asst'][:150]}")
    print()

# User mesajı frekans analizi
print("=" * 60)
print("En sık A kategorisi user kalıpları:")
counter = Counter()
for v in cat_a:
    u = _lower(v["user"]).strip()[:60]
    counter[u] += 1
for pattern, count in counter.most_common(15):
    print(f"  {count:3d}x  {pattern}")
