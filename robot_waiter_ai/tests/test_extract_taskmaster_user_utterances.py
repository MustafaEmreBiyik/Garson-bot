from __future__ import annotations

import json
from pathlib import Path

from robot_waiter_ai.training.extract_taskmaster_user_utterances import (
    build_intermediate_dataset,
    extract_records_from_conversations,
    main,
)


def test_extract_records_only_keeps_user_customer_turns():
    conversations = [
        {
            "conversation_id": "conv-1",
            "utterances": [
                {"index": 0, "speaker": "USER", "text": "I want a burger."},
                {"index": 1, "speaker": "ASSISTANT", "text": "Sure."},
                {"index": 2, "speaker": "customer", "text": "And fries too."},
                {"index": 3, "speaker": "agent", "text": "Anything else?"},
            ],
        }
    ]

    records, skipped = extract_records_from_conversations(
        conversations,
        source_domain="food_ordering",
    )

    assert skipped == 0
    assert [record["original_text"] for record in records] == [
        "I want a burger.",
        "And fries too.",
    ]
    assert all(record["source_dataset"] == "taskmaster_2" for record in records)
    assert all(record["source_domain"] == "food_ordering" for record in records)
    assert all(record["conversation_id"] == "conv-1" for record in records)
    assert [record["turn_index"] for record in records] == [0, 2]


def test_extract_records_skips_empty_and_invalid_user_utterances():
    conversations = [
        {
            "conversation_id": "conv-2",
            "utterances": [
                {"index": 0, "speaker": "USER", "text": "   "},
                {"index": 1, "speaker": "USER", "text": "."},
                {"index": 2, "speaker": "USER", "text": None},
                {"index": 3, "speaker": "USER", "text": "table for two"},
                {"index": 4, "speaker": "ASSISTANT", "text": "Not included"},
            ],
        }
    ]

    records, skipped = extract_records_from_conversations(
        conversations,
        source_domain="restaurant_search",
    )

    assert skipped == 3
    assert len(records) == 1
    assert records[0]["original_text"] == "table for two"
    assert records[0]["status"] == "raw_extracted"
    assert records[0]["candidate_intent"] is None
    assert records[0]["keep_candidate"] is None
    assert records[0]["notes"] == ""


def test_build_intermediate_dataset_writes_expected_jsonl(tmp_path):
    food_path = tmp_path / "food-ordering.json"
    restaurant_path = tmp_path / "restaurant-search.json"
    output_path = tmp_path / "taskmaster_user_utterances_raw.jsonl"

    food_path.write_text(
        json.dumps(
            [
                {
                    "conversation_id": "food-1",
                    "utterances": [
                        {"index": 0, "speaker": "USER", "text": "Need a pizza."},
                        {"index": 1, "speaker": "ASSISTANT", "text": "Okay."},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    restaurant_path.write_text(
        json.dumps(
            [
                {
                    "conversation_id": "rest-1",
                    "utterances": [
                        {"index": 0, "speaker": "customer", "text": "Find sushi nearby."},
                        {"index": 1, "speaker": "agent", "text": "Sure."},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    summary = build_intermediate_dataset(
        food_ordering_path=food_path,
        restaurant_search_path=restaurant_path,
        output_path=output_path,
    )

    assert summary["conversations_read"] == 2
    assert summary["food_ordering_user_utterances"] == 1
    assert summary["restaurant_search_user_utterances"] == 1
    assert summary["skipped"] == 0
    assert output_path.exists()

    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    records = [json.loads(line) for line in lines]
    assert set(records[0]) == {
        "source_dataset",
        "source_domain",
        "conversation_id",
        "turn_index",
        "original_text",
        "status",
        "candidate_intent",
        "keep_candidate",
        "notes",
    }


def test_main_returns_nonzero_and_prints_missing_paths(capsys, tmp_path):
    food_path = tmp_path / "food-ordering.json"
    restaurant_path = tmp_path / "restaurant-search.json"

    exit_code = main(
        [
            "--food-ordering",
            str(food_path),
            "--restaurant-search",
            str(restaurant_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Missing input files" in captured.err
    assert str(food_path) in captured.err
    assert str(restaurant_path) in captured.err


def test_main_prints_summary_and_creates_output(capsys, tmp_path):
    food_path = tmp_path / "food-ordering.json"
    restaurant_path = tmp_path / "restaurant-search.json"
    output_path = tmp_path / "taskmaster_user_utterances_raw.jsonl"

    food_path.write_text(
        json.dumps(
            [
                {
                    "conversation_id": "food-1",
                    "utterances": [
                        {"index": 0, "speaker": "USER", "text": "Need a pizza."},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    restaurant_path.write_text(
        json.dumps(
            [
                {
                    "conversation_id": "rest-1",
                    "utterances": [
                        {"index": 0, "speaker": "customer", "text": "Find sushi nearby."},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--food-ordering",
            str(food_path),
            "--restaurant-search",
            str(restaurant_path),
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Taskmaster extraction complete." in captured.out
    assert f"Input food-ordering path: {food_path}" in captured.out
    assert f"Input restaurant-search path: {restaurant_path}" in captured.out
    assert "Food-ordering conversations read: 1" in captured.out
    assert "Restaurant-search conversations read: 1" in captured.out
    assert "Records written: 2" in captured.out
    assert f"Output path: {output_path}" in captured.out
    assert Path(output_path).exists()
