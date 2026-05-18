from __future__ import annotations

import hashlib
import json
from pathlib import Path

from robot_waiter_ai.training.build_taskmaster_food_ordering_adaptation_pilot import (
    build_adaptation_pilot,
    main,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_build_adaptation_pilot_reads_food_template_and_limits_output(tmp_path):
    input_path = tmp_path / "taskmaster_food_ordering_adaptation_template.jsonl"
    output_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_30.jsonl"

    template_records = []
    categories = [
        "order_item",
        "ask_menu",
        "ask_price",
        "modify_order",
        "remove_item",
        "confirm_order",
        "ask_ingredient",
        "ask_allergy",
        "ask_recommendation",
    ]
    for index in range(35):
        template_records.append(
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering" if index < 34 else "restaurant_search",
                "conversation_id": f"conv-{index}",
                "turn_index": index,
                "original_text": f"example {index}",
                "candidate_category": categories[index % len(categories)],
                "turkish_adapted_user_message": "should be cleared",
                "adaptation_status": "accepted_adapted",
                "adaptation_notes": "template note",
                "include_for_future_grounded_generation": True,
            }
        )

    _write_jsonl(input_path, template_records)

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

    summary = build_adaptation_pilot(
        input_path=input_path,
        output_path=output_path,
        max_records=30,
    )

    assert summary["records_read"] == 34
    assert summary["records_written"] == 30
    assert output_path.exists()

    records = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 30
    assert all(record["source_domain"] == "food_ordering" for record in records)
    assert all(record["turkish_adapted_user_message"] == "" for record in records)
    assert all(record["adaptation_status"] == "needs_manual_review" for record in records)
    assert all(record["include_for_future_grounded_generation"] is False for record in records)

    after_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in processed_paths
    }
    assert before_hashes == after_hashes


def test_main_writes_only_pilot_output(capsys, tmp_path):
    input_path = tmp_path / "taskmaster_food_ordering_adaptation_template.jsonl"
    output_path = tmp_path / "taskmaster_food_ordering_adaptation_pilot_30.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "food-1",
                "turn_index": 0,
                "original_text": "I'd like soup.",
                "candidate_category": "order_item",
                "turkish_adapted_user_message": "",
                "adaptation_status": "needs_manual_review",
                "adaptation_notes": "",
                "include_for_future_grounded_generation": False,
            }
        ],
    )

    exit_code = main(["--input", str(input_path), "--output", str(output_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Taskmaster food-ordering adaptation pilot build complete." in captured.out
    assert "Pilot records written: 1" in captured.out
    assert output_path.exists()
