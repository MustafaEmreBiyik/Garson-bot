from __future__ import annotations

import json
from pathlib import Path

import yaml

from robot_waiter_ai.evals.grounded_paraphrase_output_scorer import main as scorer_main
from robot_waiter_ai.evals.grounded_paraphrase_output_scorer import score_grounded_paraphrase_outputs
from robot_waiter_ai.training.export_grounded_paraphrase_valid_reference import export_valid_reference


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _write_seed(path: Path, examples: list[dict]) -> None:
    path.write_text(
        yaml.safe_dump({"examples": examples}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _example(example_id: str, intent: str, canonical: str, paraphrase: str, preserve: list[str]) -> dict:
    return {
        "id": example_id,
        "user_message": f"user_{example_id}",
        "intent": intent,
        "canonical_response": canonical,
        "safe_paraphrase": paraphrase,
        "must_preserve_terms": preserve,
        "must_not_introduce": [],
        "notes": f"notes_{example_id}",
    }


def test_export_file_is_created_and_matches_valid_split(tmp_path):
    raw_path = tmp_path / "seed.yaml"
    valid_path = tmp_path / "grounded_paraphrase_valid.jsonl"
    train_path = tmp_path / "grounded_paraphrase_train.jsonl"
    output_path = tmp_path / "valid_reference.jsonl"

    seed_examples = [
        _example("gpp_a", "greeting", "Merhaba", "Merhaba, hoş geldiniz.", ["Merhaba"]),
        _example("gpp_b", "price_question", "Fiyat: Ayran 45 TL.", "Fiyat bilgisi olarak Ayran 45 TL.", ["Fiyat", "45", "TL"]),
        _example("gpp_c", "off_topic", "Bu konuda yardımcı olamıyorum.", "Bu konuda yardımcı olamıyorum.", ["yardımcı olamıyorum"]),
    ]
    _write_seed(raw_path, seed_examples)
    _write_jsonl(train_path, [{"metadata": {"id": "gpp_a"}}])
    _write_jsonl(valid_path, [{"metadata": {"id": "gpp_b"}}, {"metadata": {"id": "gpp_c"}}])

    count = export_valid_reference(
        valid_path=valid_path,
        train_path=train_path,
        raw_path=raw_path,
        output_path=output_path,
    )

    assert output_path.exists()
    assert count == 2

    exported = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert [record["id"] for record in exported] == ["gpp_b", "gpp_c"]
    assert {record["id"] for record in exported}.isdisjoint({"gpp_a"})


def test_scorer_accepts_jsonl_reference_via_reference_argument(tmp_path):
    reference_path = tmp_path / "valid_reference.jsonl"
    outputs_path = tmp_path / "outputs.jsonl"

    _write_jsonl(
        reference_path,
        [
            {
                "id": "gpp_b",
                "intent": "price_question",
                "canonical_response": "Fiyat: Ayran 45 TL.",
                "safe_paraphrase": "Fiyat bilgisi olarak Ayran 45 TL.",
                "must_preserve_terms": ["Fiyat", "45", "TL"],
                "must_not_introduce": [],
                "notes": "price",
            }
        ],
    )
    _write_jsonl(outputs_path, [{"id": "gpp_b", "generated_paraphrase": "Fiyat bilgisi olarak Ayran 45 TL."}])

    report = score_grounded_paraphrase_outputs(outputs_path, reference_path=reference_path)
    exit_code = scorer_main(["--reference", str(reference_path), "--outputs", str(outputs_path)])

    assert report.total_reference_examples == 1
    assert report.passed == 1
    assert exit_code == 0


def test_default_full_seed_scorer_behavior_still_works(tmp_path):
    reference_path = tmp_path / "seed.yaml"
    outputs_path = tmp_path / "outputs.jsonl"

    _write_seed(
        reference_path,
        [_example("gpp_seed", "greeting", "Merhaba", "Merhaba, hoş geldiniz.", ["Merhaba"])],
    )
    _write_jsonl(outputs_path, [{"id": "gpp_seed", "generated_paraphrase": "Merhaba, hoş geldiniz."}])

    report = score_grounded_paraphrase_outputs(outputs_path, reference_path=reference_path)

    assert report.total_reference_examples == 1
    assert report.passed == 1
