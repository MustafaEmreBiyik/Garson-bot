#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_is_specific_order_turn ile düzeltme sonrası kaç ihlal kalır?
Mevcut: 353 → Beklenen: gerçek veri ihlalleri
"""
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

_ORDER_TRIGGERS = ["alayım", "istiyorum", "alabilir miyim", "alabilir miyiz",
                   "getir", "ver ", "verir misiniz", "sipariş"]
_CANCEL_TRIGGERS = ["istemiyorum", "iptal", "çıkar", "kaldır", "geri al"]

# Menü ürünleri + kategori adları (özgün + genişletilmiş)
_ORDER_FOOD_TOKENS = [
    # Çorbalar
    "mercimek", "mantar", "çorba",
    # Ana yemekler
    "köfte", "döner", "tavuk", "et",
    # Tatlılar
    "sütlaç", "künefe", "tatlı",
    # İçecekler
    "limonata", "ayran", "şalgam", "kola", "su", "içecek",
    # Genel
    "salata", "ana yemek",
]

def is_order_turn_OLD(user):
    """Eski (geniş) tanım."""
    return _ca(user, _ORDER_TRIGGERS) and not _ca(user, _CANCEL_TRIGGERS)

def is_specific_order_turn_NEW(user):
    """Yeni (dar) tanım — menü ürünü gerektirir."""
    if _ca(user, _CANCEL_TRIGGERS):
        return False
    if not _ca(user, _ORDER_TRIGGERS):
        return False
    return _ca(user, _ORDER_FOOD_TOKENS)

path = Path("robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl")
records = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

old_viols = []
new_viols = []

for rec in records:
    msgs = rec["messages"]
    for i, msg in enumerate(msgs):
        if msg["role"] != "assistant":
            continue
        user = next((msgs[j]["content"] for j in range(i-1,-1,-1) if msgs[j]["role"]=="user"), "")
        asst = msg["content"]
        if is_order_turn_OLD(user) and "başka" not in _lower(asst):
            old_viols.append({"user": user, "asst": asst})
        if is_specific_order_turn_NEW(user) and "başka" not in _lower(asst):
            new_viols.append({"user": user, "asst": asst})

print(f"ESKİ 'Sipariş-başka' ihlali: {len(old_viols)}")
print(f"YENİ 'Sipariş-başka' ihlali: {len(new_viols)}")
print(f"Düşen (false positive): {len(old_viols) - len(new_viols)}")
print()

print("=" * 60)
print("YENİ ihlaller — TÜMÜ:")
print("=" * 60)
for i, v in enumerate(new_viols, 1):
    print(f"\n[{i:3d}] USER: {v['user'][:120]}")
    print(f"      ASST: {v['asst'][:200]}")
