#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_is_greeting_turn + check_greeting_4cats düzeltme simülasyonu.
Mevcut: 97 → Beklenen: ~10 gerçek ihlal
"""
import json, re, sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def _lower(s):
    return s.lower().replace("i̇", "i").replace("İ", "i")

def _ca(text, kws):
    t = _lower(text)
    return any(k in t for k in kws)

# ── Mevcut sabitler ────────────────────────────────────────────────────────────
_GREETING_TRIGGERS = ["merhaba", "selam", "hoş geldin", "günaydın", "iyi günler",
                       "iyi akşamlar", "kolay gelsin", "buyurun"]
#  ^^^ "masaya" kaldırıldı — "Yan masaya daha hızlı baktınız" gibi şikayetleri önle

_MENU_TRIGGERS = ["ne var", "neler var", "menü", "ne yiyebilirim", "ne alabilirim",
                   "sipariş vermek"]
#  ^^^ "ne yesem" ve "ne içsem" kaldırıldı — öneri talebi, genel menü değil

_CATEGORY_KEYWORDS = ["çorba", "ana yemek", "tatlı", "içecek"]
_ORDER_TRIGGERS = ["alayım", "istiyorum", "alabilir miyim", "alabilir miyiz",
                   "getir", "ver ", "verir misiniz", "sipariş"]
_CANCEL_TRIGGERS = ["istemiyorum", "iptal", "çıkar", "kaldır", "geri al"]
_BILL_TRIGGERS   = ["hesap", "hesab", "ödeyeyim", "ödeyeceğim", "ödemek istiyorum",
                    "toplam", "ödeme", "ödeyebilir", "ödeyelim", "ödeyebilirim",
                    "kapatalım", "kapatabilir misiniz", "çek gelsin", "adisyon"]
_PRICE_TRIGGERS  = ["kaç", "fiyat", "ne kadar", "kaç tl", "kaç lira", "ücret", "para",
                    "değeri", "tutarı", "maliyeti"]
_BUDGET_TRIGGERS = ["ucuz", "pahalı", "uygun", "hesaplı", "bütçe", "bütçem",
                    "liram var", "liran var", "liraya", "liramla",
                    "tl var", "tl'm var", "tl bütçe",
                    "en az", "en çok", "en pahalı", "en ucuz",
                    "cebime", "karşılar mı", "doyar mı", "yeter mi",
                    "borç", "borcum"]

# ── YENİ sabitler ──────────────────────────────────────────────────────────────
_DIETARY_MARKERS = [
    "gluten", "glüten",
    "alerji", "alerjen", "allerji",
    "vejetaryen", "vegan",
    "etsiz", "et yemiyor", "et yemiyorum", "et olmayan", "et içermeyen",
    "sütsüz", "süt ürünü", "laktoz", "lakto",
    "helal", "soya",
    "diyet",
    "protein ağırlıklı",
    "sebze",
]

_OFFMENU_MARKERS = [
    "neden menüde yok",
    "yoksa bile",
    "menüde yok",
    "menüde yoksa",
    "menünüzde yok",
    "menünüzde yoksa",
]

_FAREWELL_USER_MARKERS = [
    "kalkıyoruz", "çıkıyoruz", "gidiyoruz", "gidiyorum",
    "güle güle",
    "sağlıcakla",
    "ellerinize sağlık", "elinize sağlık",
    "iyi çalışmalar",
    "kaçalım",
    "veda",
    "keyifli bir yemekti",
]

_URGENCY_MARKERS = [
    "acelem var", "acelem",
    "vaktim yok", "vaktim dar",
    "otobüs kalkacak",
    "uçağım",
    "koşturuyorum",
    "hızlı ne var", "hızlı ne yiy",
    "çabuk ne var",
    "hızlıca ne",
]

_FAREWELL_RESPONSE_MARKERS = [
    "afiyet olsun",
    "tekrar bekleriz", "yine bekleriz", "tekrar bekliyoruz",
    "her zaman bekleriz",
    "iyi günler dileriz", "iyi akşamlar dileriz",
    "sağ olun",
]

_REDIRECT_MARKERS = [
    "personelimize",
    "bilgim yok",
    "yardımcı olamıyorum",
]

_RECOMMENDATION_QUALIFIERS = [
    "hafif",              # "hafif ama doyurucu ne var?"
    "ağır olmayan",       # "çok ağır olmayan ne var?"
    "öne çıkan",          # "menüden öne çıkan ne var?"
    "ne iyi gidiyor",     # "menüde ne iyi gidiyor?"
    "en çok tercih",      # "en çok tercih edilen"
    "karar veremiyorum",  # "menüye bakıyorum ama karar veremiyorum"
    "karar veremedim",
    "doyurucu",           # "hafif ama doyurucu"
]


# ── ESKİ is_greeting_turn ──────────────────────────────────────────────────────
def is_greeting_OLD(user):
    u = _lower(user)
    _G = ["merhaba", "selam", "hoş geldin", "günaydın", "iyi günler",
          "iyi akşamlar", "kolay gelsin", "buyurun", "masaya"]  # masaya dahil
    _M = ["ne var", "neler var", "menü", "ne yiyebilirim", "ne alabilirim",
          "ne yesem", "ne içsem", "sipariş vermek"]              # ne yesem dahil
    has_greeting = any(g in u for g in _G)
    has_menu_q   = any(m in u for m in _M)
    has_category = _ca(u, _CATEGORY_KEYWORDS)
    has_order    = _ca(u, _ORDER_TRIGGERS)
    if has_category or has_order:
        return False
    return has_greeting or has_menu_q


# ── YENİ is_greeting_turn ─────────────────────────────────────────────────────
def is_greeting_NEW(user):
    u = _lower(user)
    has_greeting = _ca(u, _GREETING_TRIGGERS)
    has_menu_q   = _ca(u, _MENU_TRIGGERS)
    has_category = _ca(u, _CATEGORY_KEYWORDS)
    has_order    = _ca(u, _ORDER_TRIGGERS)

    if has_category or has_order:
        return False
    # Hesap/veda bağlamı
    if _ca(u, _BILL_TRIGGERS):
        return False
    # Bütçe/fiyat bağlamı
    if _ca(u, _PRICE_TRIGGERS) or _ca(u, _BUDGET_TRIGGERS):
        return False
    if re.search(r'\btl\b', u):
        return False
    # Diyet/alerji kısıtı — spesifik soru, genel menü değil
    if _ca(u, _DIETARY_MARKERS):
        return False
    # Off-menu şikayet/öneri
    if _ca(u, _OFFMENU_MARKERS):
        return False
    # Veda bağlamı — kullanıcı mesajında
    if _ca(u, _FAREWELL_USER_MARKERS):
        return False
    # Acele/zaman baskısı — spesifik öneri isteniyor
    if _ca(u, _URGENCY_MARKERS):
        return False
    # Öneri isteği belirteçleri
    if _ca(u, _RECOMMENDATION_QUALIFIERS):
        return False

    return has_greeting or has_menu_q


def check_greeting_OLD(user, asst):
    if not is_greeting_OLD(user):
        return None
    missing = [c for c in _CATEGORY_KEYWORDS if c not in _lower(asst)]
    if missing:
        return f"EKSİK: {missing}"
    return None


def check_greeting_NEW(user, asst):
    if not is_greeting_NEW(user):
        return None
    a = _lower(asst)
    # Veda yanıtı — menü sunusu beklenmez
    if _ca(a, _FAREWELL_RESPONSE_MARKERS):
        return None
    # Bot yönlendiriyor
    if _ca(a, _REDIRECT_MARKERS):
        return None
    # Bot anlayamadı
    if "anlayamadım" in a:
        return None
    missing = [c for c in _CATEGORY_KEYWORDS if c not in a]
    if missing:
        return f"EKSİK: {missing}"
    return None


# ── Simülasyon ─────────────────────────────────────────────────────────────────
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
        if check_greeting_OLD(user, asst):
            old_viols.append({"user": user, "asst": asst})
        if check_greeting_NEW(user, asst):
            new_viols.append({"user": user, "asst": asst})

print(f"ESKİ Karşılama-4kategori ihlali: {len(old_viols)}")
print(f"YENİ Karşılama-4kategori ihlali: {len(new_viols)}")
print(f"Düşen (false positive): {len(old_viols) - len(new_viols)}")
print()

print("=" * 70)
print("YENİ ihlaller — TÜMÜ:")
print("=" * 70)
for i, v in enumerate(new_viols, 1):
    a = _lower(v["asst"])
    missing = [c for c in _CATEGORY_KEYWORDS if c not in a]
    print(f"\n[{i:3d}] USER:    {v['user'][:110]}")
    print(f"      ASST:    {v['asst'][:180]}")
    print(f"      EKSİK:   {missing}")
