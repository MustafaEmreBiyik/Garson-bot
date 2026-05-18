from __future__ import annotations

import hashlib
import json
from pathlib import Path

from robot_waiter_ai.training.review_taskmaster_canonical_preview import (
    review_canonical_preview,
    main,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_review_canonical_preview_marks_bad_match_and_duplicates(tmp_path):
    input_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_canonical_preview.jsonl"
    output_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_canonical_reviewed.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "food-1",
                "turn_index": 0,
                "original_text": "orig-1",
                "candidate_category": "order_item",
                "turkish_adapted_user_message": "Sipariş vermek istiyorum.",
                "adaptation_notes": "accepted",
                "canonical_response_preview": "Siparişe eklemek istediğiniz ürünü yazar mısınız?",
                "deterministic_status": "add_item",
                "preview_status": "needs_review",
                "include_for_grounded_paraphrase_dataset": False,
                "preview_notes": "",
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "food-2",
                "turn_index": 1,
                "original_text": "orig-2",
                "candidate_category": "order_item",
                "turkish_adapted_user_message": "Sipariş vermek istiyorum.",
                "adaptation_notes": "duplicate",
                "canonical_response_preview": "Siparişe eklemek istediğiniz ürünü yazar mısınız?",
                "deterministic_status": "add_item",
                "preview_status": "needs_review",
                "include_for_grounded_paraphrase_dataset": False,
                "preview_notes": "",
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "food-3",
                "turn_index": 2,
                "original_text": "orig-3",
                "candidate_category": "order_item",
                "turkish_adapted_user_message": "Bir kişilik sipariş vermek istiyorum.",
                "adaptation_notes": "bad match",
                "canonical_response_preview": "Hangi ürünü çıkarmak istersiniz?",
                "deterministic_status": "remove_item",
                "preview_status": "needs_review",
                "include_for_grounded_paraphrase_dataset": False,
                "preview_notes": "",
            },
        ],
    )

    processed_paths = [
        Path("C:/Users/Emre/Desktop/Garson-bot/robot_waiter_ai/datasets/processed/waiter_sft_train.jsonl"),
        Path("C:/Users/Emre/Desktop/Garson-bot/robot_waiter_ai/datasets/processed/waiter_sft_valid.jsonl"),
        Path(
            "C:/Users/Emre/Desktop/Garson-bot/robot_waiter_ai/datasets/processed/grounded_paraphrase_train.jsonl"
        ),
        Path(
            "C:/Users/Emre/Desktop/Garson-bot/robot_waiter_ai/datasets/processed/grounded_paraphrase_valid.jsonl"
        ),
    ]
    before_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in processed_paths
    }

    summary = review_canonical_preview(input_path=input_path, output_path=output_path)

    assert summary["input_records_read"] == 3
    assert output_path.exists()
    assert output_path.name == "taskmaster_food_ordering_adaptation_pilot_canonical_reviewed.jsonl"

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 3

    approved = [row for row in rows if row["canonical_review_status"] == "approved_canonical_preview"]
    duplicates = [row for row in rows if row["canonical_review_status"] == "rejected_duplicate_low_value"]
    bad = [row for row in rows if row["canonical_review_status"] == "rejected_bad_deterministic_match"]

    assert len(approved) == 1
    assert approved[0]["include_for_grounded_paraphrase_dataset"] is True
    assert len(duplicates) == 1
    assert duplicates[0]["include_for_grounded_paraphrase_dataset"] is False
    assert len(bad) == 1
    assert bad[0]["include_for_grounded_paraphrase_dataset"] is False
    assert "remove_item" in bad[0]["canonical_review_notes"]

    after_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in processed_paths
    }
    assert before_hashes == after_hashes


def test_main_prints_summary(capsys, tmp_path):
    input_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_canonical_preview.jsonl"
    output_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_canonical_reviewed.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "food-1",
                "turn_index": 0,
                "original_text": "orig-1",
                "candidate_category": "order_item",
                "turkish_adapted_user_message": "Sipariş vermek istiyorum.",
                "adaptation_notes": "accepted",
                "canonical_response_preview": "Siparişe eklemek istediğiniz ürünü yazar mısınız?",
                "deterministic_status": "add_item",
                "preview_status": "needs_review",
                "include_for_grounded_paraphrase_dataset": False,
                "preview_notes": "",
            }
        ],
    )

    exit_code = main(["--input", str(input_path), "--output", str(output_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Taskmaster canonical review complete." in captured.out
    assert "approved_canonical_preview: 1" in captured.out
