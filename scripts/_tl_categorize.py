#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
'Gerçek ihlal' olarak etiketlenenleri kategorilere ayır:
  A. Takas/iptal+sipariş (aslında doğru — fiyat söylenebilir)
  B. Fiilsiz düz sipariş ("iki köfte" gibi)
  C. Gerçek ihlal — öneri/tanıtım/sohbet bağlamında TL
"""
import json, re, sys
from collections import Counter
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def _lower(s):
    return s.lower().replace("i̇", "i").replace("İ", "i")

_PRICE_TRIGGERS  = ["kaç", "fiyat", "ne kadar", "kaç tl", "kaç lira", "ücret", "para"]
_ORDER_TRIGGERS  = ["alayım", "istiyorum", "alabilir miyim", "alabilir miyiz",
                    "getir", "ver ", "verir misiniz", "sipariş"]
_BILL_TRIGGERS   = ["hesap", "ödeyeyim", "ödeyeceğim", "ödemek istiyorum", "toplam"]
_CANCEL_TRIGGERS = ["istemiyorum", "iptal", "çıkar", "kaldır", "geri al", "yerine"]
PRICES = ["85", "95", "240", "280", "210", "100", "140", "45", "70", "50"]

# ── Menü ürün adları (alias dahil) ───────────────────────────────────────────
MENU_ITEMS = [
    "mercimek çorbası", "mercimek", "mantar çorbası", "mantar",
    "izgara köfte", "köfte", "et döner", "döner",
    "izgara tavuk salata", "tavuk salata", "tavuk",
    "fırın sütlaç", "sütlaç", "künefe",
    "limonata", "ayran", "şalgam", "kola", "su"
]

def is_ok_original(user):
    u = _lower(user)
    if any(k in u for k in _PRICE_TRIGGERS):  return True
    if any(k in u for k in _BILL_TRIGGERS):   return True
    if (any(k in u for k in _ORDER_TRIGGERS)
            and not any(k in u for k in _CANCEL_TRIGGERS)): return True
    return False

def has_tl(asst):
    a = _lower(asst)
    if re.search(r"\btl\b", a) or re.search(r"\blira\b", a): return True
    return any(re.search(rf"\b{p}\b", a) for p in PRICES)

def is_swap_or_cancel_order(user):
    """Takas/iptal+yeni sipariş mi? (fiyat söylenebilir bağlam)"""
    u = _lower(user)
    has_cancel = any(k in u for k in _CANCEL_TRIGGERS)
    has_order  = any(k in u for k in _ORDER_TRIGGERS)
    has_menu   = any(item in u for item in MENU_ITEMS)
    # "yerine" veya (iptal + sipariş fiili) veya sadece iptal+menü ürünü
    if "yerine" in u and has_menu:         return True
    if has_cancel and has_order:           return True
    if has_cancel and has_menu:            return True  # "iptal, iki köfte"
    return False

def is_bare_order(user):
    """Fiilsiz ama menü ürünü geçiyor (örtük sipariş)."""
    u = _lower(user)
    if any(k in u for k in _ORDER_TRIGGERS):  return False  # fiil var, başka kategoriye girer
    if any(k in u for k in _CANCEL_TRIGGERS): return False
    return any(item in u for item in MENU_ITEMS)

path = Path("robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl")
records = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

cat_a = []  # takas/iptal+sipariş → aslında doğru
cat_b = []  # fiilsiz düz sipariş → aslında doğru
cat_c = []  # gerçek ihlal

for rec in records:
    msgs = rec["messages"]
    for i, msg in enumerate(msgs):
        if msg["role"] != "assistant":
            continue
        user = next(
            (msgs[j]["content"] for j in range(i - 1, -1, -1) if msgs[j]["role"] == "user"),
            ""
        )
        if is_ok_original(user) or not has_tl(msg["content"]):
            continue

        if is_swap_or_cancel_order(user):
            cat_a.append({"user": user[:100], "asst": msg["content"][:180]})
        elif is_bare_order(user):
            cat_b.append({"user": user[:100], "asst": msg["content"][:180]})
        else:
            cat_c.append({"user": user[:100], "asst": msg["content"][:180]})

print("=" * 60)
print("TL İHLAL KATEGORİZASYONU")
print("=" * 60)
print(f"A. Takas/iptal+sipariş (aslında DOĞRU veri): {len(cat_a)}")
print(f"B. Fiilsiz düz sipariş (aslında DOĞRU veri): {len(cat_b)}")
print(f"C. Gerçek ihlal (öneri/sohbet bağlamı):      {len(cat_c)}")
print(f"   TOPLAM audit'in 'ihlal' dediği:           {len(cat_a)+len(cat_b)+len(cat_c)}")
print()

print("─" * 60)
print("A örnekleri (ilk 5) — takas/iptal:")
for ex in cat_a[:5]:
    print(f"  USER: {ex['user']}")
    print(f"  ASST: {ex['asst']}")
    print()

print("─" * 60)
print("B örnekleri (ilk 5) — fiilsiz sipariş:")
for ex in cat_b[:5]:
    print(f"  USER: {ex['user']}")
    print(f"  ASST: {ex['asst']}")
    print()

print("─" * 60)
print("C örnekleri — GERÇEK İHLALLER (ilk 15):")
for ex in cat_c[:15]:
    print(f"  USER: {ex['user']}")
    print(f"  ASST: {ex['asst']}")
    print()
