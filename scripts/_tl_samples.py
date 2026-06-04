#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TL yanlış bağlam ihlallerinden 15 örnek göster."""
import json, re, sys
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

def is_ok_context(user):
    u = _lower(user)
    if any(k in u for k in _PRICE_TRIGGERS):  return True
    if any(k in u for k in _BILL_TRIGGERS):   return True
    if (any(k in u for k in _ORDER_TRIGGERS)
            and not any(k in u for k in _CANCEL_TRIGGERS)): return True
    return False

PRICES = ["85", "95", "240", "280", "210", "100", "140", "45", "70", "50"]

path = Path("robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl")
records = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

examples = []
for rec in records:
    msgs = rec["messages"]
    for i, msg in enumerate(msgs):
        if msg["role"] != "assistant":
            continue
        user = next(
            (msgs[j]["content"] for j in range(i - 1, -1, -1) if msgs[j]["role"] == "user"),
            ""
        )
        if is_ok_context(user):
            continue
        a = _lower(msg["content"])
        tl_hit    = bool(re.search(r"\btl\b", a) or re.search(r"\blira\b", a))
        price_hit = any(re.search(rf"\b{p}\b", a) for p in PRICES)
        if tl_hit or price_hit:
            examples.append({"user": user[:120], "asst": msg["content"][:200]})
        if len(examples) >= 20:
            break
    if len(examples) >= 20:
        break

for i, ex in enumerate(examples, 1):
    print(f"--- Örnek {i} ---")
    print(f"USER: {ex['user']}")
    print(f"ASST: {ex['asst']}")
    print()
