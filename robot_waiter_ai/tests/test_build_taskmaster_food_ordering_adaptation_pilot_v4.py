from __future__ import annotations

import hashlib
import json
from pathlib import Path

from robot_waiter_ai.training.build_taskmaster_food_ordering_adaptation_pilot_v4 import (
    build_adaptation_pilot_v4,
    main,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_build_adaptation_pilot_v4_tightens_filters(tmp_path):
    input_path = tmp_path / "taskmaster_user_utterances_raw.jsonl"
    pilot_v1_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_30.jsonl"
    pilot_v2_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_50_v2.jsonl"
    pilot_v3_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_50_v3.jsonl"
    output_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_50_v4.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "prev-v1",
                "turn_index": 0,
                "original_text": "What do you have on the menu?",
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "prev-v2",
                "turn_index": 1,
                "original_text": "How much does that cost?",
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "prev-v3",
                "turn_index": 2,
                "original_text": "Without onions.",
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "frag-1",
                "turn_index": 3,
                "original_text": "No, thanks.",
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "frag-2",
                "turn_index": 4,
                "original_text": "No, it's okay.",
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "noise-1",
                "turn_index": 5,
                "original_text": "What was I doing again?",
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "unsupported-1",
                "turn_index": 6,
                "original_text": "I want pizza for dinner.",
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "bad-allergy",
                "turn_index": 7,
                "original_text": "Chicken with cashew nuts.",
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "bad-price",
                "turn_index": 8,
                "original_text": "The price rating should be moderate. I don't want to spend a ton of money on takeout.",
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "good-price",
                "turn_index": 9,
                "original_text": "How much does that cost?",
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "good-ingredient",
                "turn_index": 10,
                "original_text": "What comes with it?",
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "good-modify",
                "turn_index": 11,
                "original_text": "No pickles.",
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "restaurant_search",
                "conversation_id": "rest-1",
                "turn_index": 12,
                "original_text": "Find me a place to eat.",
            },
        ],
    )
    _write_jsonl(pilot_v1_path, [{"conversation_id": "prev-v1", "turn_index": 0}])
    _write_jsonl(pilot_v2_path, [{"conversation_id": "prev-v2", "turn_index": 1}])
    _write_jsonl(pilot_v3_path, [{"conversation_id": "prev-v3", "turn_index": 2}])

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

    summary = build_adaptation_pilot_v4(
        input_path=input_path,
        pilot_v1_path=pilot_v1_path,
        pilot_v2_path=pilot_v2_path,
        pilot_v3_path=pilot_v3_path,
        output_path=output_path,
        max_records=50,
    )

    assert summary["excluded_prior_pilots"] == 3
    assert output_path.exists()
    assert output_path.name == "taskmaster_food_ordering_adaptation_pilot_50_v4.jsonl"

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    conversation_ids = {row["conversation_id"] for row in rows}
    assert "prev-v1" not in conversation_ids
    assert "prev-v2" not in conversation_ids
    assert "prev-v3" not in conversation_ids
    assert "frag-1" not in conversation_ids
    assert "frag-2" not in conversation_ids
    assert "noise-1" not in conversation_ids
    assert "unsupported-1" not in conversation_ids
    assert "bad-allergy" not in conversation_ids
    assert "bad-price" not in conversation_ids
    assert "rest-1" not in conversation_ids
    assert "good-price" in conversation_ids
    assert "good-ingredient" in conversation_ids
    assert "good-modify" in conversation_ids

    by_id = {row["conversation_id"]: row for row in rows}
    assert by_id["good-price"]["candidate_category"] == "ask_price"
    assert by_id["good-ingredient"]["candidate_category"] == "ask_ingredient"
    assert by_id["good-modify"]["candidate_category"] == "modify_order"
    assert all(row["source_domain"] == "food_ordering" for row in rows)
    assert all(row["adaptation_status"] == "needs_manual_review" for row in rows)
    assert all(row["turkish_adapted_user_message"] == "" for row in rows)
    assert all(row["include_for_future_grounded_generation"] is False for row in rows)
    assert all(row["pilot_version"] == "v4_tightened_high_precision" for row in rows)

    after_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in processed_paths
    }
    assert before_hashes == after_hashes


def test_main_prints_summary(capsys, tmp_path):
    input_path = tmp_path / "taskmaster_user_utterances_raw.jsonl"
    pilot_v1_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_30.jsonl"
    pilot_v2_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_50_v2.jsonl"
    pilot_v3_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_50_v3.jsonl"
    output_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_50_v4.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "good-price",
                "turn_index": 0,
                "original_text": "How much does that cost?",
            }
        ],
    )
    _write_jsonl(pilot_v1_path, [])
    _write_jsonl(pilot_v2_path, [])
    _write_jsonl(pilot_v3_path, [])

    exit_code = main(
        [
            "--input",
            str(input_path),
            "--pilot-v1",
            str(pilot_v1_path),
            "--pilot-v2",
            str(pilot_v2_path),
            "--pilot-v3",
            str(pilot_v3_path),
            "--output",
            str(output_path),
            "--max-records",
            "50",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Taskmaster food-ordering adaptation pilot v4 build complete." in captured.out
    assert "Records written: 1" in captured.out
