from __future__ import annotations

import hashlib
import json
from pathlib import Path

from robot_waiter_ai.training.build_taskmaster_food_ordering_adaptation_pilot_v2 import (
    build_adaptation_pilot_v2,
    main,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_build_adaptation_pilot_v2_filters_and_excludes_previous_rows(tmp_path):
    input_path = tmp_path / "taskmaster_food_ordering_candidates.jsonl"
    previous_pilot_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_30.jsonl"
    output_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_50_v2.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "prev-1",
                "turn_index": 0,
                "original_text": "What drinks do you have?",
                "candidate_category": "ask_menu",
                "keep_candidate": True,
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "keep-1",
                "turn_index": 1,
                "original_text": "What drinks do you have?",
                "candidate_category": "ask_menu",
                "keep_candidate": True,
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "restaurant_search",
                "conversation_id": "rest-1",
                "turn_index": 2,
                "original_text": "Find me a restaurant.",
                "candidate_category": "ask_menu",
                "keep_candidate": True,
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "skip-keep-false",
                "turn_index": 3,
                "original_text": "Price of soup?",
                "candidate_category": "ask_price",
                "keep_candidate": False,
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "keep-2",
                "turn_index": 4,
                "original_text": "I want to order takeout.",
                "candidate_category": "order_item",
                "keep_candidate": True,
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "downrank-1",
                "turn_index": 5,
                "original_text": "I want pizza for dinner.",
                "candidate_category": "order_item",
                "keep_candidate": True,
            },
        ],
    )
    _write_jsonl(
        previous_pilot_path,
        [
            {
                "conversation_id": "prev-1",
                "turn_index": 0,
            }
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

    summary = build_adaptation_pilot_v2(
        input_path=input_path,
        previous_pilot_path=previous_pilot_path,
        output_path=output_path,
        max_records=2,
    )

    assert summary["records_written"] == 2
    assert summary["excluded_previous_pilot"] == 1
    assert output_path.exists()

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 2
    assert all(row["source_domain"] == "food_ordering" for row in rows)
    assert all(row["adaptation_status"] == "needs_manual_review" for row in rows)
    assert all(row["turkish_adapted_user_message"] == "" for row in rows)
    assert all(row["include_for_future_grounded_generation"] is False for row in rows)
    assert all(row["pilot_version"] == "v2_menu_aware" for row in rows)
    assert {row["conversation_id"] for row in rows} == {"keep-1", "keep-2"}

    after_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in processed_paths
    }
    assert before_hashes == after_hashes


def test_main_prints_summary(capsys, tmp_path):
    input_path = tmp_path / "taskmaster_food_ordering_candidates.jsonl"
    previous_pilot_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_30.jsonl"
    output_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_50_v2.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "keep-1",
                "turn_index": 1,
                "original_text": "What drinks do you have?",
                "candidate_category": "ask_menu",
                "keep_candidate": True,
            }
        ],
    )
    _write_jsonl(previous_pilot_path, [])

    exit_code = main(
        [
            "--input",
            str(input_path),
            "--previous-pilot",
            str(previous_pilot_path),
            "--output",
            str(output_path),
            "--max-records",
            "50",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Taskmaster food-ordering adaptation pilot v2 build complete." in captured.out
    assert "Records written: 1" in captured.out
