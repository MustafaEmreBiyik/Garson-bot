from __future__ import annotations

import json
from pathlib import Path

from robot_waiter_ai.evals.grounded_paraphrase_output_scorer import score_grounded_paraphrase_outputs
from robot_waiter_ai.training.export_grounded_paraphrase_output_template import (
    BACKEND_PLACEHOLDER,
    SOURCE_REFERENCE,
    export_output_template,
)


BASE_DIR = Path(__file__).resolve().parents[1]
VALID_REFERENCE_PATH = BASE_DIR / "evals" / "grounded_paraphrase_valid_reference.jsonl"
OUTPUT_TEMPLATE_PATH = BASE_DIR / "evals" / "grounded_paraphrase_valid_output_template.jsonl"


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_export_file_is_created_and_matches_valid_reference(tmp_path):
    reference_path = tmp_path / "valid_reference.jsonl"
    output_path = tmp_path / "output_template.jsonl"
    reference_records = [
        {
            "id": "gpp_a",
            "intent": "greeting",
            "canonical_response": "Merhaba",
            "safe_paraphrase": "Merhaba, hoş geldiniz.",
            "must_preserve_terms": ["Merhaba"],
            "must_not_introduce": [],
            "notes": "a",
        },
        {
            "id": "gpp_b",
            "intent": "price_question",
            "canonical_response": "Fiyat: Ayran 45 TL.",
            "safe_paraphrase": "Fiyat bilgisi olarak Ayran 45 TL.",
            "must_preserve_terms": ["Fiyat", "45", "TL"],
            "must_not_introduce": [],
            "notes": "b",
        },
    ]
    _write_jsonl(reference_path, reference_records)

    count = export_output_template(reference_path=reference_path, output_path=output_path)

    assert output_path.exists()
    assert count == len(reference_records)

    template_records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert [record["id"] for record in template_records] == [record["id"] for record in reference_records]
    assert all(record["generated_paraphrase"] == "" for record in template_records)
    assert all(record["backend_name"] == BACKEND_PLACEHOLDER for record in template_records)


def test_template_metadata_contains_required_fields():
    reference_ids = [
        json.loads(line)["id"]
        for line in VALID_REFERENCE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    template_records = [
        json.loads(line)
        for line in OUTPUT_TEMPLATE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(template_records) == len(reference_ids)
    assert [record["id"] for record in template_records] == reference_ids

    for record in template_records:
        assert record["generated_paraphrase"] == ""
        assert record["backend_name"] == BACKEND_PLACEHOLDER
        metadata = record["metadata"]
        assert metadata["intent"]
        assert metadata["source_reference"] == SOURCE_REFERENCE
        assert metadata["fill_instructions"]
        assert metadata["canonical_response"]
        assert isinstance(metadata["must_preserve_terms"], list)
        assert isinstance(metadata["must_not_introduce"], list)


def test_empty_template_scores_as_failed_not_invalid():
    report = score_grounded_paraphrase_outputs(
        outputs_path=OUTPUT_TEMPLATE_PATH,
        reference_path=VALID_REFERENCE_PATH,
    )
    reference_count = sum(
        1 for line in VALID_REFERENCE_PATH.read_text(encoding="utf-8").splitlines() if line.strip()
    )

    assert report.total_reference_examples == reference_count
    assert report.matched_outputs == reference_count
    assert report.missing_outputs == 0
    assert report.invalid_output_records == 0
    assert report.passed == 0
    assert report.failed == reference_count
    assert all(result.status == "failed" for result in report.results)
    assert all("Generated paraphrase is empty." in result.reasons for result in report.results)
