#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rebuild_wbot_v5_train.py — wbot_v5 dataset birleştirme

wbot_v4_train.jsonl (3605, temiz base) + C paketi (182) = 3787 kayıt
→ shuffle (seed=2028) → wbot_v5_train.jsonl

W11 kapanış kuralı düzeltmesi bu birleştirmenin kapsamı DIŞINDA — o
_SYSTEM_TEMPLATE'e (inference zamanı, training script short_prompt=True
ile dataset'in system alanını yok sayıyor) uygulandı. Bu script yalnızca
C paketinin 182 yeni assistant-örneğini eğitime katmak için; kayıtların
system alanına dokunulmuyor (wbot_v3/v4 emsaliyle aynı yöntem).

Çalıştır: python scripts/rebuild_wbot_v5_train.py
"""
import json
import random
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path("robot_waiter_ai/datasets/processed")
BASE = DATA_DIR / "wbot_v4_train.jsonl"
OUT = DATA_DIR / "wbot_v5_train.jsonl"

C_PACKAGE = [
    "wbot_c_modifikasyon_sonrasi.jsonl",  # 20
    "wbot_c_kufur_genisletme.jsonl",      # 18
    "wbot_c_alerji_kalip.jsonl",          # 24
    "wbot_c_eskalasyon.jsonl",            # 20
    "wbot_c_anti_hallusinasyon.jsonl",    # 100
]


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    if not BASE.exists():
        print(f"Base bulunamadı: {BASE}")
        return

    base_records = load_jsonl(BASE)
    print(f"Base: {len(base_records)} kayıt")

    print("\nC paketi:")
    new_records: list[dict] = []
    for fname in C_PACKAGE:
        recs = load_jsonl(DATA_DIR / fname)
        print(f"  {fname:<34} {len(recs):>4} kayıt")
        new_records.extend(recs)

    print(f"\nYeni kayıt toplamı: {len(new_records)}")

    all_records = base_records + new_records
    random.Random(2028).shuffle(all_records)
    print(f"Toplam (shuffle sonrası): {len(all_records)} kayıt")

    with open(OUT, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\n✓ {len(all_records)} kayıt → {OUT}")


if __name__ == "__main__":
    main()
