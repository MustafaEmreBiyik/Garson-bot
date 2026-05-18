from __future__ import annotations

import json
from pathlib import Path

import yaml

from robot_waiter_ai.training.grounded_paraphrase_builder import build
from robot_waiter_ai.training.grounded_paraphrase_validator import validate


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_PATH = BASE_DIR / "datasets" / "raw" / "grounded_paraphrase_seed.yaml"


def _write_seed(path: Path, examples: list[dict]) -> None:
    path.write_text(
        yaml.safe_dump({"examples": examples}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _valid_example() -> dict:
    return {
        "id": "fixture_001",
        "user_message": "Ayranın fiyatı nedir?",
        "intent": "price_question",
        "canonical_response": "Fiyat: Ayran 45 TL.",
        "safe_paraphrase": "Fiyat bilgisi olarak Ayran 45 TL tutuyor.",
        "must_preserve_terms": ["Fiyat", "Ayran", "45", "TL"],
        "must_not_introduce": [],
        "notes": "Valid price paraphrase fixture.",
    }


def test_validator_accepts_valid_seed():
    total, error_count, errors = validate(RAW_PATH)
    assert total >= 80
    assert error_count == 0, "\n".join(errors)


def test_validator_rejects_missing_required_fields(tmp_path):
    bad = _valid_example()
    del bad["safe_paraphrase"]
    raw_path = tmp_path / "bad.yaml"
    _write_seed(raw_path, [bad])

    total, error_count, errors = validate(raw_path)
    assert total == 1
    assert error_count >= 1
    assert any("Missing required field" in error for error in errors)


def test_validator_rejects_missing_preserve_terms(tmp_path):
    bad = _valid_example()
    bad["safe_paraphrase"] = "Ayran burada listeleniyor."
    raw_path = tmp_path / "bad.yaml"
    _write_seed(raw_path, [bad])

    total, error_count, errors = validate(raw_path)
    assert total == 1
    assert error_count >= 1
    assert any("missing preserve term" in error for error in errors)


def test_validator_rejects_forbidden_introduced_terms(tmp_path):
    bad = _valid_example()
    bad["must_not_introduce"] = ["100 TL"]
    bad["safe_paraphrase"] = "Fiyat bilgisi olarak Ayran 45 TL değil, 100 TL."
    raw_path = tmp_path / "bad.yaml"
    _write_seed(raw_path, [bad])

    total, error_count, errors = validate(raw_path)
    assert total == 1
    assert error_count >= 1
    assert any("contains forbidden term" in error for error in errors)


def test_builder_writes_train_and_valid_jsonl(tmp_path):
    raw_path = tmp_path / "seed.yaml"
    examples = []
    for idx in range(10):
        example = _valid_example().copy()
        example["id"] = f"fixture_{idx:03d}"
        example["notes"] = f"Note {idx}"
        examples.append(example)
    _write_seed(raw_path, examples)

    out_dir = tmp_path / "processed"
    build(raw_path=raw_path, out_dir=out_dir)

    train_file = out_dir / "grounded_paraphrase_train.jsonl"
    valid_file = out_dir / "grounded_paraphrase_valid.jsonl"
    assert train_file.exists()
    assert valid_file.exists()

    train_lines = train_file.read_text(encoding="utf-8").strip().splitlines()
    valid_lines = valid_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(train_lines) > 0
    assert len(valid_lines) > 0
    assert len(train_lines) + len(valid_lines) == len(examples)


def test_builder_preserves_metadata(tmp_path):
    raw_path = tmp_path / "seed.yaml"
    example = _valid_example()
    example["id"] = "fixture_meta"
    example["notes"] = "Metadata preservation test."
    _write_seed(raw_path, [example, {**example, "id": "fixture_meta_2"}])

    out_dir = tmp_path / "processed"
    build(raw_path=raw_path, out_dir=out_dir)

    train_file = out_dir / "grounded_paraphrase_train.jsonl"
    first_record = json.loads(train_file.read_text(encoding="utf-8").splitlines()[0])
    assert first_record["metadata"]["id"].startswith("fixture_meta")
    assert first_record["metadata"]["intent"] == "price_question"
    assert first_record["metadata"]["notes"]
