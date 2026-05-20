from __future__ import annotations

import hashlib
import json
from pathlib import Path

from robot_waiter_ai.training.build_taskmaster_food_ordering_adaptation_pilot_v3 import (
    build_adaptation_pilot_v3,
    main,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_build_adaptation_pilot_v3_excludes_prior_noise_unsupported_and_dedupes(tmp_path):
    input_path = tmp_path / "taskmaster_user_utterances_raw.jsonl"
    pilot_v1_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_30.jsonl"
    pilot_v2_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_50_v2.jsonl"
    output_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_50_v3.jsonl"

    raw_records = [
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "food_ordering",
            "conversation_id": "prev-v1",
            "turn_index": 0,
            "original_text": "What drinks do you have?",
        },
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "food_ordering",
            "conversation_id": "prev-v2",
            "turn_index": 1,
            "original_text": "How much does soup cost?",
        },
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "food_ordering",
            "conversation_id": "noise-1",
            "turn_index": 2,
            "original_text": "What was I doing again?",
        },
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "food_ordering",
            "conversation_id": "noise-2",
            "turn_index": 3,
            "original_text": "I would like to reorder the same thing I ordered last week.",
        },
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "food_ordering",
            "conversation_id": "unsupported-1",
            "turn_index": 4,
            "original_text": "I want pizza for dinner.",
        },
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "food_ordering",
            "conversation_id": "unsupported-2",
            "turn_index": 5,
            "original_text": "Hello, I'd like to order some gyro.",
        },
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "restaurant_search",
            "conversation_id": "rest-1",
            "turn_index": 6,
            "original_text": "Find me a place to eat.",
        },
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "food_ordering",
            "conversation_id": "generic-1",
            "turn_index": 7,
            "original_text": "I want to order takeout.",
        },
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "food_ordering",
            "conversation_id": "generic-2",
            "turn_index": 8,
            "original_text": "I would like to order takeout.",
        },
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "food_ordering",
            "conversation_id": "generic-3",
            "turn_index": 9,
            "original_text": "I'd like to order takeout, please.",
        },
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "food_ordering",
            "conversation_id": "menu-1",
            "turn_index": 10,
            "original_text": "What do you have on the menu?",
        },
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "food_ordering",
            "conversation_id": "price-1",
            "turn_index": 11,
            "original_text": "How much does it cost?",
        },
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "food_ordering",
            "conversation_id": "ingredient-1",
            "turn_index": 12,
            "original_text": "What is in this and what comes with it?",
        },
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "food_ordering",
            "conversation_id": "allergy-1",
            "turn_index": 13,
            "original_text": "I am allergic to peanuts.",
        },
    ]
    _write_jsonl(input_path, raw_records)
    _write_jsonl(
        pilot_v1_path,
        [{"conversation_id": "prev-v1", "turn_index": 0}],
    )
    _write_jsonl(
        pilot_v2_path,
        [{"conversation_id": "prev-v2", "turn_index": 1}],
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

    summary = build_adaptation_pilot_v3(
        input_path=input_path,
        pilot_v1_path=pilot_v1_path,
        pilot_v2_path=pilot_v2_path,
        output_path=output_path,
        max_records=50,
    )

    assert summary["excluded_prior_pilots"] == 2
    assert summary["duplicates_removed"] >= 2
    assert summary["generic_order_start_included"] <= 5
    assert output_path.exists()
    assert output_path.name == "taskmaster_food_ordering_adaptation_pilot_50_v3.jsonl"

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert all(row["source_domain"] == "food_ordering" for row in rows)
    assert all(row["adaptation_status"] == "needs_manual_review" for row in rows)
    assert all(row["turkish_adapted_user_message"] == "" for row in rows)
    assert all(row["include_for_future_grounded_generation"] is False for row in rows)
    assert all(row["pilot_version"] == "v3_targeted_deduped" for row in rows)
    conversation_ids = {row["conversation_id"] for row in rows}
    assert "prev-v1" not in conversation_ids
    assert "prev-v2" not in conversation_ids
    assert "noise-1" not in conversation_ids
    assert "noise-2" not in conversation_ids
    assert "unsupported-1" not in conversation_ids
    assert "unsupported-2" not in conversation_ids
    assert "rest-1" not in conversation_ids

    generic_rows = [
        row
        for row in rows
        if row["candidate_category"] == "generic_order_start"
    ]
    assert len(generic_rows) <= 5

    after_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in processed_paths
    }
    assert before_hashes == after_hashes


def test_main_prints_summary(capsys, tmp_path):
    input_path = tmp_path / "taskmaster_user_utterances_raw.jsonl"
    pilot_v1_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_30.jsonl"
    pilot_v2_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_50_v2.jsonl"
    output_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_50_v3.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "menu-1",
                "turn_index": 0,
                "original_text": "What do you have on the menu?",
            }
        ],
    )
    _write_jsonl(pilot_v1_path, [])
    _write_jsonl(pilot_v2_path, [])

    exit_code = main(
        [
            "--input",
            str(input_path),
            "--pilot-v1",
            str(pilot_v1_path),
            "--pilot-v2",
            str(pilot_v2_path),
            "--output",
            str(output_path),
            "--max-records",
            "50",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Taskmaster food-ordering adaptation pilot v3 build complete." in captured.out
    assert "Records written: 1" in captured.out
