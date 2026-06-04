#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Karşılama-4kategori ihlallerini kategorize et."""
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

_GREETING_TRIGGERS = ["merhaba", "selam", "hoş geldin", "günaydın", "iyi günler",
                       "iyi akşamlar", "kolay gelsin", "buyurun", "masaya"]
_MENU_TRIGGERS = ["ne var", "neler var", "menü", "ne yiyebilirim", "ne alabilirim",
                   "ne yesem", "ne içsem", "sipariş vermek"]
_CATEGORY_KEYWORDS = ["çorba", "ana yemek", "tatlı", "içecek"]
_ORDER_TRIGGERS = ["alayım", "istiyorum", "alabilir miyim", "alabilir miyiz",
                   "getir", "ver ", "verir misiniz", "sipariş"]

def is_greeting_turn(user):
    u = _lower(user)
    has_greeting = _ca(u, _GREETING_TRIGGERS)
    has_menu_q   = _ca(u, _MENU_TRIGGERS)
    has_category = _ca(u, _CATEGORY_KEYWORDS)
    has_order    = _ca(u, _ORDER_TRIGGERS)
    if has_category or has_order:
        return False
    return has_greeting or has_menu_q

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
        if not is_greeting_turn(user):
            continue
        a = _lower(asst)
        missing = [c for c in _CATEGORY_KEYWORDS if c not in a]
        if missing:
            violations.append({"user": user, "asst": asst, "missing": missing})

print(f"Toplam Karşılama-4kategori ihlali: {len(violations)}\n")

# ── Eksik kategori frekansı ────────────────────────────────────────────────────
missing_counter = Counter()
for v in violations:
    for m in v["missing"]:
        missing_counter[m] += 1

print("Eksik kategori dağılımı:")
for cat, cnt in missing_counter.most_common():
    print(f"  {cat:<15} {cnt}")
print()

# ── User trigger analizi ───────────────────────────────────────────────────────
trigger_counter = Counter()
for v in violations:
    u = _lower(v["user"])
    for t in _GREETING_TRIGGERS + _MENU_TRIGGERS:
        if t in u:
            trigger_counter[t] += 1

print("Hangi trigger'dan tetikleniyor:")
for t, cnt in trigger_counter.most_common():
    print(f"  {cnt:3d}x  '{t}'")
print()

# ── Kategorize et ─────────────────────────────────────────────────────────────
# A: Sadece selamlama (gerçek karşılama, kategorileri listelemiyor) — gerçek ihlal
# B: Genel menü sorusu (ne var, ne yiyebilirim) — bot kategori yerine özel yanıt veriyor
# C: Tek/iki kategori eksik — yarı-uyumlu yanıt
# D: Yanıt çok kısa veya bot anlayamadı
# E: Diğer

cat_a = []  # sadece selamlama
cat_b = []  # menü sorusu bağlamı
cat_c = []  # kısmen uyumlu (1-2 eksik)
cat_d = []  # kısa/anlayamadım
cat_e = []  # diğer

_GREETING_ONLY  = ["merhaba", "selam", "hoş geldin", "günaydın", "iyi günler",
                    "iyi akşamlar", "kolay gelsin", "buyurun", "masaya"]
_MENU_Q_ONLY    = ["ne var", "neler var", "menü", "ne yiyebilirim", "ne alabilirim",
                    "ne yesem", "ne içsem", "sipariş vermek"]
_CLARIFY_MARKS  = ["anlayamadım", "tekrar", "lütfen", "açıklar mısınız"]

for v in violations:
    u = _lower(v["user"])
    a = _lower(v["asst"])
    n_missing = len(v["missing"])

    if len(a) < 80:
        cat_d.append(v)
    elif _ca(a, _CLARIFY_MARKS):
        cat_d.append(v)
    elif n_missing <= 2 and _ca(u, _GREETING_ONLY):
        cat_a.append(v)
    elif _ca(u, _MENU_Q_ONLY):
        cat_b.append(v)
    elif n_missing <= 2:
        cat_c.append(v)
    else:
        cat_e.append(v)

print(f"A. Selamlama yanıtı, kategoriler eksik (gerçek ihlal?):  {len(cat_a)}")
print(f"B. Menü sorusu bağlamı (specific yanıt):                 {len(cat_b)}")
print(f"C. Kısmen uyumlu (1-2 eksik):                            {len(cat_c)}")
print(f"D. Kısa/anlayamadım yanıt:                               {len(cat_d)}")
print(f"E. Diğer:                                                 {len(cat_e)}")
print()

print("=" * 70)
print("A örnekleri — selamlama yanıtı (ilk 10):")
for v in cat_a[:10]:
    print(f"\n  USER:    {v['user'][:100]}")
    print(f"  ASST:    {v['asst'][:200]}")
    print(f"  EKSİK:   {v['missing']}")

print()
print("=" * 70)
print("B örnekleri — menü sorusu (ilk 10):")
for v in cat_b[:10]:
    print(f"\n  USER:    {v['user'][:100]}")
    print(f"  ASST:    {v['asst'][:200]}")
    print(f"  EKSİK:   {v['missing']}")

print()
print("=" * 70)
print("C örnekleri — kısmen uyumlu (tümü):")
for v in cat_c:
    print(f"\n  USER:    {v['user'][:100]}")
    print(f"  ASST:    {v['asst'][:200]}")
    print(f"  EKSİK:   {v['missing']}")

print()
print("=" * 70)
print("D örnekleri — kısa/anlayamadım (tümü):")
for v in cat_d:
    print(f"\n  USER:    {v['user'][:100]}")
    print(f"  ASST:    {v['asst'][:200]}")
    print(f"  EKSİK:   {v['missing']}")

print()
print("=" * 70)
print("E örnekleri — diğer (tümü):")
for v in cat_e:
    print(f"\n  USER:    {v['user'][:100]}")
    print(f"  ASST:    {v['asst'][:200]}")
    print(f"  EKSİK:   {v['missing']}")

# ── Yanıttaki var olan kategoriler frekansı ───────────────────────────────────
print()
print("=" * 70)
print("Yanıtta hangi kategoriler EN ÇOK geçiyor (violations'da):")
present_counter = Counter()
for v in violations:
    a = _lower(v["asst"])
    for c in _CATEGORY_KEYWORDS:
        if c in a:
            present_counter[c] += 1
for cat, cnt in present_counter.most_common():
    print(f"  {cat:<15} {cnt} kez mevcut  (97 ihlalde)")
