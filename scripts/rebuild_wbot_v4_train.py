#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rebuild_wbot_v4_train.py — wbot_v4 dataset birleştirme

wbot_v3_train.jsonl (3000, temiz base) + A paketi (490) + B paketi (115)
= 3605 kayıt → shuffle (seed=2027) → wbot_v4_train.jsonl

wbot_v3 birleştirmesinde kullanılan yöntemle aynı mantık (PROJE_DURUMU.md
"wbot_v3 Dataset Üretimi" bölümü): temiz base + yeni gen_*.py çıktıları,
tek seferde shuffle. C paketi (Gemini/Claude API, farklı ortam) bu
birleştirmenin kapsamı dışında — ileride ayrı bir turda eklenecek.

Çalıştır: python scripts/rebuild_wbot_v4_train.py
"""
import json
import random
import shutil
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path("robot_waiter_ai/datasets/processed")
BASE = DATA_DIR / "wbot_v3_train.jsonl"
BACKUP = DATA_DIR / "wbot_v4_base_backup.jsonl"
OUT = DATA_DIR / "wbot_v4_train.jsonl"

A_PACKAGE = [
    "wbot_v4_aciklama.jsonl",     # A1 — 150
    "wbot_v4_karmasik.jsonl",     # A2 — 150
    "wbot_v4_cokturlu.jsonl",     # A3 — 100
    "wbot_v4_kisa_onay.jsonl",    # A4 — 60
    "wbot_v4_duzeltme.jsonl",     # A5 — 30
]
B_PACKAGE = [
    "wbot_v4_belirsiz.jsonl",         # B1 — 20
    "wbot_v4_kotu_niyet.jsonl",       # B2 — 15
    "wbot_v4_modifikasyon.jsonl",     # B3 — 20
    "wbot_v4_alerjen_cakisma.jsonl",  # B4 — 15
    "wbot_v4_pratik_soru.jsonl",      # B5 — 10
    "wbot_v4_alerji_oneri.jsonl",     # B6 — 20
    "wbot_v4_siparis_durumu.jsonl",   # B7 — 15
]


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    if not BASE.exists():
        print(f"Base bulunamadı: {BASE}")
        return

    # ── 1. Yedek al ──────────────────────────────────────────────────────────
    shutil.copy(BASE, BACKUP)
    print(f"Yedek alındı: {BASE.name} → {BACKUP.name}")

    base_records = load_jsonl(BASE)
    print(f"Base: {len(base_records)} kayıt")

    # ── 2. A + B paketlerini yükle ───────────────────────────────────────────
    new_records: list[dict] = []
    print("\nA paketi:")
    for fname in A_PACKAGE:
        recs = load_jsonl(DATA_DIR / fname)
        print(f"  {fname:<28} {len(recs):>4} kayıt")
        new_records.extend(recs)

    print("B paketi:")
    for fname in B_PACKAGE:
        recs = load_jsonl(DATA_DIR / fname)
        print(f"  {fname:<28} {len(recs):>4} kayıt")
        new_records.extend(recs)

    print(f"\nYeni kayıt toplamı: {len(new_records)}")

    # ── 3. Birleştir + shuffle ───────────────────────────────────────────────
    all_records = base_records + new_records
    random.Random(2027).shuffle(all_records)
    print(f"Toplam (shuffle sonrası): {len(all_records)} kayıt")

    # ── 4. Yaz ────────────────────────────────────────────────────────────────
    with open(OUT, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\n✓ {len(all_records)} kayıt → {OUT}")


if __name__ == "__main__":
    main()
