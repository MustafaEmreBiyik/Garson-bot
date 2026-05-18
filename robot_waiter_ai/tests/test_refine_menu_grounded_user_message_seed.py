from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from robot_waiter_ai.training.refine_menu_grounded_user_message_seed import (
    refine_menu_grounded_user_message_seed,
    main,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_refine_menu_grounded_user_message_seed_keeps_review_only_and_balanced(tmp_path):
    input_path = tmp_path / "menu_grounded_user_message_seed_review.jsonl"
    output_path = tmp_path / "menu_grounded_user_message_seed_review_refined.jsonl"

    records = []
    for index in range(12):
        records.append(
            {
                "source": "menu_grounded_seed",
                "intent_category": "order_item",
                "menu_item_name": f"Item {index}",
                "turkish_user_message": f"Item {index} sipariş etmek istiyorum.",
                "seed_status": "needs_review",
                "seed_notes": "",
                "include_for_canonical_preview": False,
            }
        )
    for index in range(12):
        records.append(
            {
                "source": "menu_grounded_seed",
                "intent_category": "ask_price",
                "menu_item_name": f"Item {index}",
                "turkish_user_message": f"Item {index} fiyatı nedir?",
                "seed_status": "needs_review",
                "seed_notes": "",
                "include_for_canonical_preview": False,
            }
        )
    for category, count in [
        ("ask_ingredient", 8),
        ("ask_allergy", 8),
        ("ask_menu", 4),
        ("modify_order", 4),
        ("remove_item", 4),
        ("confirm_order", 3),
        ("unsupported_item_probe", 4),
        ("off_topic_rejection_probe", 2),
    ]:
        for index in range(count):
            records.append(
                {
                    "source": "menu_grounded_seed",
                    "intent_category": category,
                    "menu_item_name": None,
                    "turkish_user_message": f"{category} örnek {index}",
                    "seed_status": "needs_review",
                    "seed_notes": "",
                    "include_for_canonical_preview": False,
                }
            )

    _write_jsonl(input_path, records)

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

    summary = refine_menu_grounded_user_message_seed(
        input_path=input_path,
        output_path=output_path,
    )

    assert output_path.exists()
    assert 40 <= summary["records_written"] <= 50

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert all(row["seed_status"] == "needs_review" for row in rows)
    assert all(row["include_for_canonical_preview"] is False for row in rows)
    assert any(row["intent_category"] == "unsupported_item_probe" for row in rows)
    assert any(row["intent_category"] == "off_topic_rejection_probe" for row in rows)

    counts = Counter(row["intent_category"] for row in rows)
    assert max(counts.values()) <= 10

    after_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in processed_paths
    }
    assert before_hashes == after_hashes


def test_main_prints_summary(capsys, tmp_path):
    input_path = tmp_path / "menu_grounded_user_message_seed_review.jsonl"
    output_path = tmp_path / "menu_grounded_user_message_seed_review_refined.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source": "menu_grounded_seed",
                "intent_category": "ask_menu",
                "menu_item_name": None,
                "turkish_user_message": "Menüde neler var?",
                "seed_status": "needs_review",
                "seed_notes": "",
                "include_for_canonical_preview": False,
            }
        ],
    )

    exit_code = main(["--input", str(input_path), "--output", str(output_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Menu-grounded user-message seed refinement complete." in captured.out
    assert "Records written:" in captured.out
