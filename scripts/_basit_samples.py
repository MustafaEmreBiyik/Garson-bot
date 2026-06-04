#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sipariş-başka ihlallerini örnekle ve kategorize et."""
import json, re, sys
from collections import Counter
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def _lower(s):
    return s.lower().replace("i̇", "i").replace("İ", "i")

_ORDER_TRIGGERS = ["alayım", "istiyorum", "alabilir miyim", "alabilir miyiz",
                   "getir", "ver ", "verir misiniz", "sipariş"]
_CANCEL_TRIGGERS = ["istemiyorum", "iptal", "çıkar", "kaldır", "geri al"]

def _ca(text, kws):
    t = _lower(text)
    return any(k in t for k in kws)

def is_order_turn(user):
    return _ca(user, _ORDER_TRIGGERS) and not _ca(user, _CANCEL_TRIGGERS)

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
        if is_order_turn(user) and "başka" not in _lower(asst):
            violations.append({"user": user, "asst": asst})

print(f"Toplam Sipariş-başka ihlali: {len(violations)}\n")

# --- Asistanın cevabını kategorize et ---
# A: "getireyim mi" var (bilinen yasak — ayrı kural)
# B: sadece onay, "başka" yok ama "getireyim mi" de yok
# C: tamamen farklı cevap (yanlış bağlam?)
# D: user mesajı aslında sipariş değil (false positive)

cat_a = []  # "getireyim mi" var
cat_b = []  # normal onay ama "başka" eksik — gerçek ihlal
cat_c = []  # ilgisiz/farklı cevap
cat_d = []  # muhtemel false positive

for v in violations:
    a = _lower(v["asst"])
    u = _lower(v["user"])
    if "getireyim mi" in a:
        cat_a.append(v)
    elif any(x in a for x in ["tabii", "hemen", "anlıyorum", "not aldım", "kaydettim",
                                "peki", "hazırlıyoruz", "ekledim", "sipariş", "onayladım"]):
        cat_b.append(v)
    elif any(x in a for x in ["anlayamadım", "tekrar", "lütfen", "açıklar mısınız", "hangi"]):
        cat_c.append(v)
    else:
        cat_d.append(v)

print(f"A. 'Getireyim mi' var (zaten ayrı kural): {len(cat_a)}")
print(f"B. Normal sipariş onayı, 'başka' eksik (gerçek ihlal): {len(cat_b)}")
print(f"C. Anlayamadım/yönlendirme cevabı: {len(cat_c)}")
print(f"D. Kategorize edilemeyen: {len(cat_d)}")
print()

# --- B kategorisindeki asistan yanıt kalıpları ---
print("=" * 60)
print("B örnekleri — sipariş onayı ama 'başka' yok (ilk 20):")
print("=" * 60)
for v in cat_b[:20]:
    print(f"\n  USER: {v['user'][:100]}")
    print(f"  ASST: {v['asst'][:200]}")

print()
print("=" * 60)
print("D örnekleri — kategorize edilemeyen (ilk 15):")
print("=" * 60)
for v in cat_d[:15]:
    print(f"\n  USER: {v['user'][:100]}")
    print(f"  ASST: {v['asst'][:200]}")

# --- User kalıpları frekans analizi ---
print()
print("=" * 60)
print("En sık geçen ORDER_TRIGGER kalıpları (violations içinde):")
trigger_counts = Counter()
for v in violations:
    u = _lower(v["user"])
    for t in _ORDER_TRIGGERS:
        if t in u:
            trigger_counts[t] += 1
for trigger, count in trigger_counts.most_common():
    print(f"  {count:4d}x  '{trigger}'")
