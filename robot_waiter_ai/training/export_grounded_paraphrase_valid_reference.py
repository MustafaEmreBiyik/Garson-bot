from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml


_BASE = Path(__file__).resolve().parents[1]
RAW_PATH = _BASE / "datasets" / "raw" / "grounded_paraphrase_seed.yaml"
PROCESSED_DIR = _BASE / "datasets" / "processed"
VALID_PATH = PROCESSED_DIR / "grounded_paraphrase_valid.jsonl"
TRAIN_PATH = PROCESSED_DIR / "grounded_paraphrase_train.jsonl"
OUTPUT_PATH = _BASE / "evals" / "grounded_paraphrase_valid_reference.jsonl"


REQUIRED_REFERENCE_FIELDS = (
    "id",
    "intent",
    "canonical_response",
    "safe_paraphrase",
    "must_preserve_terms",
    "must_not_introduce",
    "notes",
)


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"JSONL file not found: {path}")

    records: List[Dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number} in {path}: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"Expected JSON object on line {line_number} in {path}.")
        records.append(record)
    return records


def _extract_ids(records: List[Dict[str, Any]], source_name: str) -> List[str]:
    ids: List[str] = []
    for idx, record in enumerate(records, start=1):
        metadata = record.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError(f"{source_name} record {idx} is missing dict metadata.")
        record_id = metadata.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError(f"{source_name} record {idx} is missing metadata.id.")
        ids.append(record_id)
    return ids


def _load_seed_examples(raw_path: Path) -> Dict[str, Dict[str, Any]]:
    if not raw_path.exists():
        raise FileNotFoundError(f"Grounded paraphrase seed file not found: {raw_path}")

    payload = yaml.safe_load(raw_path.read_text(encoding="utf-8")) or {}
    examples = payload.get("examples", [])
    if not isinstance(examples, list):
        raise ValueError("Expected 'examples' to be a list in grounded paraphrase seed YAML.")

    by_id: Dict[str, Dict[str, Any]] = {}
    for idx, example in enumerate(examples, start=1):
        if not isinstance(example, dict):
            raise ValueError(f"Seed example {idx} is not a mapping.")
        example_id = example.get("id")
        if not isinstance(example_id, str) or not example_id.strip():
            raise ValueError(f"Seed example {idx} is missing a valid id.")
        by_id[example_id] = example
    return by_id


def export_valid_reference(
    valid_path: Path = VALID_PATH,
    train_path: Path = TRAIN_PATH,
    raw_path: Path = RAW_PATH,
    output_path: Path = OUTPUT_PATH,
) -> int:
    valid_records = _load_jsonl(valid_path)
    train_records = _load_jsonl(train_path)
    valid_ids = _extract_ids(valid_records, "Valid split")
    train_ids = set(_extract_ids(train_records, "Train split"))

    overlap = sorted(set(valid_ids) & train_ids)
    if overlap:
        raise ValueError(f"Valid and train grounded paraphrase splits overlap: {', '.join(overlap)}")

    seed_by_id = _load_seed_examples(raw_path)

    missing_seed_ids = [record_id for record_id in valid_ids if record_id not in seed_by_id]
    if missing_seed_ids:
        joined = ", ".join(missing_seed_ids)
        raise ValueError(f"Valid split ids missing from grounded paraphrase seed: {joined}")

    exported_records: List[Dict[str, Any]] = []
    for record_id in valid_ids:
        example = seed_by_id[record_id]
        exported_records.append({field: example[field] for field in REQUIRED_REFERENCE_FIELDS})

    exported_ids = [record["id"] for record in exported_records]
    if exported_ids != valid_ids:
        raise ValueError("Exported grounded paraphrase reference ids do not match valid split ids.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in exported_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(exported_records)} records -> {output_path}")
    return len(exported_records)


def main() -> None:
    count = export_valid_reference()
    print(f"Grounded paraphrase valid reference export complete. Total valid references: {count}")


if __name__ == "__main__":
    main()
