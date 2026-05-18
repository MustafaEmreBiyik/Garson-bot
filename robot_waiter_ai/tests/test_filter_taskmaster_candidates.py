from __future__ import annotations

import hashlib
import json
from pathlib import Path

from robot_waiter_ai.training.filter_taskmaster_candidates import (
    classify_record,
    filter_candidates,
    main,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_classify_record_keeps_food_ordering_examples():
    record = {
        "source_dataset": "taskmaster_2",
        "source_domain": "food_ordering",
        "conversation_id": "conv-1",
        "turn_index": 2,
        "original_text": "Can I get a burger with no onions?",
    }

    classified = classify_record(record)

    assert classified["source_dataset"] == "taskmaster_2"
    assert classified["source_domain"] == "food_ordering"
    assert classified["conversation_id"] == "conv-1"
    assert classified["turn_index"] == 2
    assert classified["candidate_category"] in {"order_item", "modify_order", "remove_item"}
    assert classified["keep_candidate"] is True
    assert classified["rejection_reason"] == ""
    assert classified["adaptation_notes"]
    assert classified["adaptation_eligible"] is True


def test_classify_record_keeps_food_ordering_dietary_question():
    classified = classify_record(
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "food_ordering",
            "conversation_id": "conv-food-dietary",
            "turn_index": 3,
            "original_text": "Do you have any gluten-free or vegetarian options?",
        }
    )

    assert classified["candidate_category"] in {"ask_allergy", "ask_menu"}
    assert classified["keep_candidate"] is True
    assert classified["rejection_reason"] == ""
    assert classified["adaptation_eligible"] is True


def test_classify_record_marks_restaurant_search_as_off_scope():
    reservation = classify_record(
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "restaurant_search",
            "conversation_id": "conv-2",
            "turn_index": 1,
            "original_text": "Can you book a table for four tonight?",
        }
    )
    address = classify_record(
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "restaurant_search",
            "conversation_id": "conv-3",
            "turn_index": 1,
            "original_text": "What is the address and is it near me?",
        }
    )
    payment = classify_record(
        {
            "source_dataset": "taskmaster_2",
            "source_domain": "restaurant_search",
            "conversation_id": "conv-4",
            "turn_index": 1,
            "original_text": "Can I pay with cash or Visa?",
        }
    )

    assert reservation["candidate_category"] == "off_scope_reservation"
    assert reservation["keep_candidate"] is False
    assert reservation["adaptation_eligible"] is False
    assert address["candidate_category"] == "off_scope_delivery_address"
    assert address["keep_candidate"] is False
    assert address["adaptation_eligible"] is False
    assert payment["candidate_category"] == "off_scope_payment"
    assert payment["keep_candidate"] is False
    assert payment["adaptation_eligible"] is False


def test_classify_record_marks_restaurant_search_dietary_discovery_as_off_scope():
    examples = [
        "I need a restaurant in Arcadia with vegetarian dishes.",
        "I'm finding a vegetarian restaurant in Albany.",
        "Do they have gluten-free options and outdoor seating?",
        "Find a restaurant with a formal atmosphere and vegetarian dishes.",
    ]

    for index, text in enumerate(examples):
        classified = classify_record(
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "restaurant_search",
                "conversation_id": f"rest-dietary-{index}",
                "turn_index": index,
                "original_text": text,
            }
        )

        assert classified["candidate_category"] == "off_scope_restaurant_search"
        assert classified["keep_candidate"] is False
        assert classified["adaptation_eligible"] is False
        assert (
            classified["rejection_reason"]
            == "restaurant_discovery_or_filtering_out_of_scope"
        )


def test_filter_candidates_writes_schema_and_preserves_processed_datasets(tmp_path, capsys):
    input_path = tmp_path / "taskmaster_user_utterances_raw.jsonl"
    food_output_path = tmp_path / "taskmaster_food_ordering_candidates.jsonl"
    restaurant_output_path = tmp_path / "taskmaster_restaurant_search_candidates.jsonl"

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

    _write_jsonl(
        input_path,
        [
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "food-1",
                "turn_index": 0,
                "original_text": "I'd like to order a pizza.",
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "food-1",
                "turn_index": 1,
                "original_text": "What sides do you have?",
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "restaurant_search",
                "conversation_id": "rest-1",
                "turn_index": 0,
                "original_text": "I'm looking for a restaurant near me.",
            },
        ],
    )

    summary = filter_candidates(
        input_path=input_path,
        food_output_path=food_output_path,
        restaurant_output_path=restaurant_output_path,
        max_food_ordering_candidates=10,
        max_restaurant_search_candidates=10,
    )

    assert summary["raw_records_read"] == 3
    assert summary["food_ordering_records_reviewed"] == 2
    assert summary["food_ordering_candidates_kept"] == 2
    assert summary["restaurant_search_records_reviewed"] == 1
    assert summary["restaurant_search_candidates_kept"] == 0
    assert food_output_path.exists()
    assert restaurant_output_path.exists()

    food_records = [
        json.loads(line)
        for line in food_output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    restaurant_records = [
        json.loads(line)
        for line in restaurant_output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert food_records
    assert restaurant_records

    for record in food_records + restaurant_records:
        assert set(record) == {
            "source_dataset",
            "source_domain",
            "conversation_id",
            "turn_index",
            "original_text",
            "candidate_category",
            "keep_candidate",
            "rejection_reason",
            "adaptation_notes",
            "adaptation_eligible",
        }

    after_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in processed_paths
    }
    assert before_hashes == after_hashes

    exit_code = main(
        [
            "--input",
            str(input_path),
            "--food-output",
            str(food_output_path),
            "--restaurant-output",
            str(restaurant_output_path),
            "--max-food-ordering-candidates",
            "10",
            "--max-restaurant-search-candidates",
            "10",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Taskmaster candidate filtering complete." in captured.out
    assert "Counts per candidate_category:" in captured.out
