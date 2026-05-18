from __future__ import annotations

import json

from robot_waiter_ai.training.build_taskmaster_food_ordering_adaptation_template import (
    build_adaptation_template,
    main,
)


def _write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_build_adaptation_template_uses_only_food_ordering_candidates(tmp_path):
    input_path = tmp_path / "taskmaster_food_ordering_candidates.jsonl"
    output_path = tmp_path / "taskmaster_food_ordering_adaptation_template.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "food-1",
                "turn_index": 0,
                "original_text": "I'd like a burger.",
                "candidate_category": "order_item",
                "keep_candidate": True,
                "rejection_reason": "",
                "adaptation_notes": "candidate note",
                "adaptation_eligible": True,
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "food-2",
                "turn_index": 1,
                "original_text": "Do you have vegetarian options?",
                "candidate_category": "ask_allergy",
                "keep_candidate": True,
                "rejection_reason": "",
                "adaptation_notes": "candidate note",
                "adaptation_eligible": False,
            },
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "restaurant_search",
                "conversation_id": "rest-1",
                "turn_index": 2,
                "original_text": "Find a vegetarian restaurant in Albany.",
                "candidate_category": "off_scope_restaurant_search",
                "keep_candidate": True,
                "rejection_reason": "",
                "adaptation_notes": "candidate note",
                "adaptation_eligible": False,
            },
        ],
    )

    summary = build_adaptation_template(input_path=input_path, output_path=output_path)

    assert summary["records_read"] == 3
    assert summary["records_written"] == 1

    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record == {
        "source_dataset": "taskmaster_2",
        "source_domain": "food_ordering",
        "conversation_id": "food-1",
        "turn_index": 0,
        "original_text": "I'd like a burger.",
        "candidate_category": "order_item",
        "turkish_adapted_user_message": "",
        "adaptation_status": "needs_manual_review",
        "adaptation_notes": "",
        "include_for_future_grounded_generation": False,
    }


def test_main_builds_template_and_prints_summary(capsys, tmp_path):
    input_path = tmp_path / "taskmaster_food_ordering_candidates.jsonl"
    output_path = tmp_path / "taskmaster_food_ordering_adaptation_template.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source_dataset": "taskmaster_2",
                "source_domain": "food_ordering",
                "conversation_id": "food-1",
                "turn_index": 0,
                "original_text": "I'd like a burger.",
                "candidate_category": "order_item",
                "keep_candidate": True,
                "rejection_reason": "",
                "adaptation_notes": "candidate note",
                "adaptation_eligible": True,
            }
        ],
    )

    exit_code = main(["--input", str(input_path), "--output", str(output_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Taskmaster food-ordering adaptation template build complete." in captured.out
    assert "Template records written: 1" in captured.out
