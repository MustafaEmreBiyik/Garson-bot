#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D kategorisini (303) alt gruplara böl."""
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

# D = bu kombinasyonlara uymayan
good_markers = ["tabii", "hemen", "anlıyorum", "not aldım", "kaydettim",
                "peki", "hazırlıyoruz", "ekledim", "sipariş", "onayladım",
                "getireyim mi", "anlayamadım", "tekrar", "lütfen", "açıklar mısınız", "hangi"]
cat_d = [v for v in violations if not any(x in _lower(v["asst"]) for x in good_markers)]

# D'yi alt gruplara böl
d1_intent = []       # "sipariş vermek istiyorum" / "siparişe başlayalım" — niyeti bildirme
d2_close   = []      # "siparişim bu kadar" — kapanış
d3_offmenu = []      # off-menu öğe, bot "bilgim yok" / "personelimize" diyor
d4_nonfood = []      # gıda dışı "istiyorum" ("kilo vermek istiyorum")
d5_other   = []      # geri kalan

_INTENT_PHRASES = ["sipariş vermek", "siparişe başla", "sipariş verebilir miyim",
                   "sipariş verebilir miyiz", "sipariş almak"]
_CLOSE_PHRASES  = ["siparişim bu kadar", "siparişim tamam", "siparişim şimdilik",
                   "siparişim bugünlük", "siparişim efendim", "siparişim sağ olun",
                   "siparişim teşekkür", "siparişim masamız"]
_STAFF_PHRASES  = ["personelimize", "bilgim yok", "yardımcı olamıyorum"]

for v in cat_d:
    u = _lower(v["user"])
    a = _lower(v["asst"])
    if any(p in u for p in _INTENT_PHRASES):
        d1_intent.append(v)
    elif any(p in u for p in _CLOSE_PHRASES):
        d2_close.append(v)
    elif any(p in a for p in _STAFF_PHRASES):
        d3_offmenu.append(v)
    elif "istiyorum" in u and not any(food in u for food in
          ["köfte", "çorba", "döner", "salata", "tatlı", "içecek", "ayran",
           "limonata", "sütlaç", "künefe", "mantar", "mercimek", "şalgam", "kola"]):
        d4_nonfood.append(v)
    else:
        d5_other.append(v)

print(f"D toplam: {len(cat_d)}")
print(f"  D1 — sipariş-intent (niyeti bildirme): {len(d1_intent)}")
print(f"  D2 — sipariş kapanış ('bu kadar'):     {len(d2_close)}")
print(f"  D3 — off-menu öğe (personelimize):     {len(d3_offmenu)}")
print(f"  D4 — gıda dışı 'istiyorum':            {len(d4_nonfood)}")
print(f"  D5 — diğer:                            {len(d5_other)}")
print()

print("=" * 60)
print("D5 (diğer) örnekleri — tümü:")
for v in d5_other[:30]:
    print(f"\n  USER: {v['user'][:120]}")
    print(f"  ASST: {v['asst'][:200]}")

print()
print("=" * 60)
print("D4 (gıda dışı istiyorum) örnekleri:")
for v in d4_nonfood[:15]:
    print(f"\n  USER: {v['user'][:120]}")
    print(f"  ASST: {v['asst'][:200]}")
