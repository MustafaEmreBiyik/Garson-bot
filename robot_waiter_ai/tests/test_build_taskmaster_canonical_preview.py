from __future__ import annotations

import hashlib
import json
from pathlib import Path

from robot_waiter_ai.training.build_taskmaster_canonical_preview import (
    build_canonical_preview,
    main,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_build_canonical_preview_exports_only_accepted_rows(tmp_path):
    input_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_accepted.jsonl"
    output_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_canonical_preview.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "food-1",
                "turn_index": 0,
                "original_text": "I'd like to order.",
                "candidate_category": "order_item",
                "turkish_adapted_user_message": "Sipariş vermek istiyorum.",
                "adaptation_status": "accepted_adapted",
                "adaptation_notes": "accepted",
                "include_for_future_grounded_generation": True,
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "food-2",
                "turn_index": 1,
                "original_text": "Rejected row",
                "candidate_category": "order_item",
                "turkish_adapted_user_message": "",
                "adaptation_status": "rejected_out_of_scope",
                "adaptation_notes": "rejected",
                "include_for_future_grounded_generation": False,
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "food-3",
                "turn_index": 2,
                "original_text": "Accepted but empty",
                "candidate_category": "order_item",
                "turkish_adapted_user_message": "",
                "adaptation_status": "accepted_adapted",
                "adaptation_notes": "invalid",
                "include_for_future_grounded_generation": True,
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "restaurant_search",
                "conversation_id": "rest-1",
                "turn_index": 3,
                "original_text": "Wrong domain",
                "candidate_category": "order_item",
                "turkish_adapted_user_message": "Sipariş vermek istiyorum.",
                "adaptation_status": "accepted_adapted",
                "adaptation_notes": "invalid",
                "include_for_future_grounded_generation": True,
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
    before_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in processed_paths
    }

    summary = build_canonical_preview(input_path=input_path, output_path=output_path)

    assert summary["input_records_read"] == 4
    assert summary["preview_records_written"] == 1
    assert summary["rejected_or_skipped_records"] == 3
    assert output_path.exists()
    assert output_path.name == "taskmaster_food_ordering_adaptation_pilot_canonical_preview.jsonl"

    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    preview = json.loads(lines[0])
    assert preview["source_domain"] == "food_ordering"
    assert preview["canonical_response_preview"].strip()
    assert preview["preview_status"] == "needs_review"
    assert preview["include_for_grounded_paraphrase_dataset"] is False
    assert "deterministic_status" in preview

    after_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in processed_paths
    }
    assert before_hashes == after_hashes


def test_main_prints_summary(capsys, tmp_path):
    input_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_accepted.jsonl"
    output_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_canonical_preview.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "food-1",
                "turn_index": 0,
                "original_text": "I'd like to order.",
                "candidate_category": "order_item",
                "turkish_adapted_user_message": "Sipariş vermek istiyorum.",
                "adaptation_status": "accepted_adapted",
                "adaptation_notes": "accepted",
                "include_for_future_grounded_generation": True,
            }
        ],
    )

    exit_code = main(["--input", str(input_path), "--output", str(output_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Taskmaster canonical preview build complete." in captured.out
    assert "Preview records written: 1" in captured.out
