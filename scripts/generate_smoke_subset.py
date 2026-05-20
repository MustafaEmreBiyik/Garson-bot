#!/usr/bin/env python3
"""Generate a small, category‑balanced smoke‑audit subset.

Usage:
  python scripts/generate_smoke_subset.py \
    --source path/to/pure_qwen_restaurant_eval_200.jsonl \
    --dest path/to/smoke_subset.jsonl \
    --max-per-category N

The script reads the source JSONL, groups records by the ``category`` field, and writes up to ``N`` records from each category (preserving order). This yields a diverse subset (~N * #categories records) suitable for a quick sanity‑check on Jetson/GPU.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a category‑balanced smoke subset.")
    parser.add_argument("--source", required=True, help="Source JSONL eval file.")
    parser.add_argument("--dest", required=True, help="Destination JSONL file for the subset.")
    parser.add_argument("--max-per-category", type=int, default=3,
                        help="Maximum records to keep per category (default: 3).")
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    src_path = Path(args.source)
    dest_path = Path(args.dest)
    if not src_path.is_file():
        raise FileNotFoundError(f"Source file not found: {src_path}")
    # Group records by category while preserving original order per category.
    groups = defaultdict(list)
    with src_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            cat = rec.get("category", "__unknown__")
            groups[cat].append(rec)
    # Build the subset list.
    subset = []
    for cat, records in groups.items():
        subset.extend(records[: args.max_per_category])
    # Write out.
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with dest_path.open("w", encoding="utf-8") as out:
        for rec in subset:
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Created subset with {len(subset)} records (max {args.max_per_category} per category) at {dest_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
