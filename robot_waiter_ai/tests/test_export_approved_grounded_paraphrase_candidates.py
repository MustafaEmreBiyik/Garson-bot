from __future__ import annotations

import hashlib
import json
from pathlib import Path

from robot_waiter_ai.training.export_approved_grounded_paraphrase_candidates import (
    export_approved_grounded_paraphrase_candidates,
    main,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_export_approved_grounded_paraphrase_candidates_exports_only_approved_rows(tmp_path):
    input_path = tmp_path / "menu_grounded_paraphrase_manual_pilot_10_reviewed.jsonl"
    output_path = tmp_path / "menu_grounded_paraphrase_approved_candidates_v1.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "id": "approved_1",
                "source": "menu_grounded_seed",
                "intent_category": "order_item",
                "menu_item_name": "Ayran",
                "user_message": "Bir Ayran alabilir miyim?",
                "canonical_response": "Ekledim: 1 x Ayran.",
                "safe_paraphrase": "1 x Ayran ekledim.",
                "candidate_type": "supported_menu_response",
                "must_preserve_terms": ["Ayran"],
                "must_not_introduce": ["unsupported menu items"],
                "semantic_review_status": "approved_semantic_review",
                "semantic_review_notes": "ok",
                "approved_for_processed_candidate": True,
                "paraphrase_status": "accepted_manual_paraphrase",
                "include_for_processed_dataset": False,
            },
            {
                "id": "rejected_1",
                "source": "menu_grounded_seed",
                "intent_category": "ask_allergy",
                "menu_item_name": "Ayran",
                "user_message": "Ayran güvenli mi?",
                "canonical_response": "Lütfen mutfakla teyit ediniz.",
                "safe_paraphrase": "Tamamen güvenli.",
                "candidate_type": "supported_menu_response",
                "must_preserve_terms": ["Lütfen mutfakla teyit ediniz."],
                "must_not_introduce": ["allergy safety guarantees"],
                "semantic_review_status": "rejected_weakens_allergy_caution",
                "semantic_review_notes": "reject",
                "approved_for_processed_candidate": False,
                "paraphrase_status": "accepted_manual_paraphrase",
                "include_for_processed_dataset": False,
            },
            {
                "id": "approved_but_empty",
                "source": "menu_grounded_seed",
                "intent_category": "ask_price",
                "menu_item_name": "Ayran",
                "user_message": "Ayran ne kadar?",
                "canonical_response": "Fiyat: 45.00 TL",
                "safe_paraphrase": "",
                "candidate_type": "supported_menu_response",
                "must_preserve_terms": ["45.00 TL"],
                "must_not_introduce": ["new prices"],
                "semantic_review_status": "approved_semantic_review",
                "semantic_review_notes": "bad",
                "approved_for_processed_candidate": True,
                "paraphrase_status": "accepted_manual_paraphrase",
                "include_for_processed_dataset": False,
            },
        ],
    )

    processed_paths = [
        Path(__file__).resolve().parents[2] / "robot_waiter_ai/datasets/processed/waiter_sft_train.jsonl",
        Path(__file__).resolve().parents[2] / "robot_waiter_ai/datasets/processed/waiter_sft_valid.jsonl",
        Path(
            str(Path(__file__).resolve().parents[2]) + "/robot_waiter_ai/datasets/processed/grounded_paraphrase_train.jsonl"
        ),
        Path(
            str(Path(__file__).resolve().parents[2]) + "/robot_waiter_ai/datasets/processed/grounded_paraphrase_valid.jsonl"
        ),
    ]
    before_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in processed_paths}

    summary = export_approved_grounded_paraphrase_candidates(
        input_path=input_path,
        output_path=output_path,
    )

    assert summary["input_records_read"] == 3
    assert summary["approved_records_exported"] == 1
    assert summary["skipped_records"] == 2
    assert output_path.exists()
    assert output_path.name == "menu_grounded_paraphrase_approved_candidates_v1.jsonl"

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 1
    assert rows[0]["id"] == "approved_1"
    assert rows[0]["include_for_processed_dataset"] is False
    assert rows[0]["export_status"] == "approved_intermediate_candidate"

    after_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in processed_paths}
    assert before_hashes == after_hashes


def test_main_prints_summary(capsys, tmp_path):
    input_path = tmp_path / "menu_grounded_paraphrase_manual_pilot_10_reviewed.jsonl"
    output_path = tmp_path / "menu_grounded_paraphrase_approved_candidates_v1.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "id": "approved_1",
                "source": "menu_grounded_seed",
                "intent_category": "order_item",
                "menu_item_name": "Ayran",
                "user_message": "Bir Ayran alabilir miyim?",
                "canonical_response": "Ekledim: 1 x Ayran.",
                "safe_paraphrase": "1 x Ayran ekledim.",
                "candidate_type": "supported_menu_response",
                "must_preserve_terms": ["Ayran"],
                "must_not_introduce": ["unsupported menu items"],
                "semantic_review_status": "approved_semantic_review",
                "semantic_review_notes": "ok",
                "approved_for_processed_candidate": True,
                "paraphrase_status": "accepted_manual_paraphrase",
                "include_for_processed_dataset": False,
            }
        ],
    )

    exit_code = main(["--input", str(input_path), "--output", str(output_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Approved grounded paraphrase candidate export complete." in captured.out
    assert "Approved records exported: 1" in captured.out
