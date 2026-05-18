from __future__ import annotations

import json
from pathlib import Path

import yaml

from robot_waiter_ai.evals.grounded_paraphrase_output_scorer import (
    format_grounded_paraphrase_report,
    load_grounded_paraphrase_output_records,
    main,
    score_grounded_paraphrase_outputs,
)


BASE_DIR = Path(__file__).resolve().parents[1]
VALID_REFERENCE_PATH = BASE_DIR / "evals" / "grounded_paraphrase_valid_reference.jsonl"
VALID_OUTPUTS_PATH = BASE_DIR / "evals" / "sample_grounded_paraphrase_valid_outputs.jsonl"
FULL_SEED_OUTPUTS_PATH = BASE_DIR / "evals" / "sample_grounded_paraphrase_outputs.jsonl"


def _write_jsonl(tmp_path: Path, records: list[dict]) -> Path:
    output_path = tmp_path / "grounded_outputs.jsonl"
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return output_path


def _write_reference_file(tmp_path: Path, examples: list[dict]) -> Path:
    reference_path = tmp_path / "grounded_paraphrase_seed.yaml"
    reference_path.write_text(
        yaml.safe_dump({"examples": examples}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return reference_path


def _reference_example() -> dict:
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


def test_loads_valid_grounded_paraphrase_outputs(tmp_path):
    output_path = _write_jsonl(
        tmp_path,
        [{"id": "fixture_001", "generated_paraphrase": "Fiyat bilgisi olarak Ayran 45 TL tutuyor."}],
    )

    records = load_grounded_paraphrase_output_records(output_path)

    assert len(records) == 1
    assert records[0]["id"] == "fixture_001"


def test_invalid_record_detection(tmp_path):
    reference_path = _write_reference_file(tmp_path, [_reference_example()])
    output_path = _write_jsonl(tmp_path, [{"id": "fixture_001"}])

    report = score_grounded_paraphrase_outputs(output_path, reference_path=reference_path)

    assert report.invalid_output_records == 1


def test_missing_output_detection(tmp_path):
    reference_path = _write_reference_file(tmp_path, [_reference_example()])
    output_path = _write_jsonl(tmp_path, [])

    report = score_grounded_paraphrase_outputs(output_path, reference_path=reference_path)

    assert report.missing_outputs == 1
    assert report.results[0].status == "missing"


def test_preserve_term_failure(tmp_path):
    reference_path = _write_reference_file(tmp_path, [_reference_example()])
    output_path = _write_jsonl(
        tmp_path,
        [{"id": "fixture_001", "generated_paraphrase": "Ayran burada listeleniyor."}],
    )

    report = score_grounded_paraphrase_outputs(output_path, reference_path=reference_path)

    assert report.failed == 1
    assert "Missing preserve term: Fiyat" in report.results[0].reasons


def test_forbidden_term_failure(tmp_path):
    example = _reference_example()
    example["intent"] = "unavailable_item"
    example["canonical_response"] = "Pizza menümüzde bulunmuyor."
    example["must_preserve_terms"] = ["Pizza", "bulunmuyor"]
    example["must_not_introduce"] = ["Pizza var"]
    reference_path = _write_reference_file(tmp_path, [example])
    output_path = _write_jsonl(
        tmp_path,
        [{"id": "fixture_001", "generated_paraphrase": "Pizza var ve hemen hazırlayabiliriz."}],
    )

    report = score_grounded_paraphrase_outputs(output_path, reference_path=reference_path)

    assert report.failed == 1
    assert "Contains forbidden term: Pizza var" in report.results[0].reasons


def test_pass_rate_calculation(tmp_path):
    first = _reference_example()
    second = {
        **_reference_example(),
        "id": "fixture_002",
        "intent": "allergen_question",
        "canonical_response": "Alerji konusunda dikkatli olalım. Lütfen içerikleri mutfakla teyit edelim.",
        "safe_paraphrase": "Alerji durumunda içerikleri mutfakla teyit ederek ilerleyelim.",
        "must_preserve_terms": ["Alerji", "teyit"],
        "must_not_introduce": ["kesinlikle güvenli"],
    }
    reference_path = _write_reference_file(tmp_path, [first, second])
    output_path = _write_jsonl(
        tmp_path,
        [
            {"id": "fixture_001", "generated_paraphrase": "Fiyat bilgisi olarak Ayran 45 TL tutuyor."},
            {"id": "fixture_002", "generated_paraphrase": "Bu ürün kesinlikle güvenli."},
        ],
    )

    report = score_grounded_paraphrase_outputs(output_path, reference_path=reference_path)

    assert report.total_reference_examples == 2
    assert report.passed == 1
    assert report.failed == 1
    assert report.pass_rate == 50.0


def test_cli_report_function_returns_structured_result(tmp_path):
    reference_path = _write_reference_file(tmp_path, [_reference_example()])
    output_path = _write_jsonl(
        tmp_path,
        [{"id": "fixture_001", "generated_paraphrase": "Fiyat bilgisi olarak Ayran 45 TL tutuyor."}],
    )

    report = score_grounded_paraphrase_outputs(output_path, reference_path=reference_path)
    rendered = format_grounded_paraphrase_report(report)
    exit_code = main(["--outputs", str(output_path), "--reference-path", str(reference_path)])

    assert report.total_reference_examples == 1
    assert "Grounded Paraphrase Output Evaluation Report" in rendered
    assert exit_code == 0


def test_validation_sample_outputs_cover_all_valid_reference_ids():
    reference_ids = {
        json.loads(line)["id"]
        for line in VALID_REFERENCE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    output_ids = {
        json.loads(line)["id"]
        for line in VALID_OUTPUTS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    assert reference_ids
    assert output_ids == reference_ids


def test_validation_sample_scores_all_outputs_with_no_missing_and_one_intentional_failure():
    report = score_grounded_paraphrase_outputs(
        outputs_path=VALID_OUTPUTS_PATH,
        reference_path=VALID_REFERENCE_PATH,
    )
    reference_count = sum(
        1 for line in VALID_REFERENCE_PATH.read_text(encoding="utf-8").splitlines() if line.strip()
    )
    sample_records = [
        json.loads(line)
        for line in VALID_OUTPUTS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    intentional_failures = {
        record["id"]
        for record in sample_records
        if record.get("metadata", {}).get("intentional_failure") is True
    }

    assert report.total_reference_examples == reference_count
    assert report.matched_outputs == reference_count
    assert report.missing_outputs == 0
    assert report.failed >= 1
    assert intentional_failures
    assert any(result.id in intentional_failures and result.status == "failed" for result in report.results)


def test_default_full_seed_sample_behavior_remains_backward_compatible():
    report = score_grounded_paraphrase_outputs(outputs_path=FULL_SEED_OUTPUTS_PATH)
    full_seed_count = sum(
        1
        for line in (BASE_DIR / "datasets" / "raw" / "grounded_paraphrase_seed.yaml").read_text(encoding="utf-8").splitlines()
        if line.startswith("- id:")
    )

    assert report.total_reference_examples == full_seed_count
    assert report.matched_outputs == 5
    assert report.invalid_output_records == 0
