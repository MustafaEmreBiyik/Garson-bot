from __future__ import annotations

import hashlib
import json
from pathlib import Path

from robot_waiter_ai.training.build_menu_grounded_user_message_seed import (
    build_menu_grounded_user_message_seed,
    main,
)


def test_build_menu_grounded_user_message_seed_writes_review_only_output(tmp_path):
    menu_path = tmp_path / "menu.yaml"
    restaurant_info_path = tmp_path / "restaurant_info.yaml"
    output_path = tmp_path / "menu_grounded_user_message_seed_review.jsonl"

    menu_path.write_text(
        """
menu:
  - id: s1
    name: Mercimek Çorbası
    category: Çorba
    price: 85
    description: Kırmızı mercimek ile hazırlanır.
    allergens: [gluten]
    availability: true
    tags: [vegetarian]
  - id: b1
    name: Ayran
    category: İçecek
    price: 45
    description: Yoğurt içeceği.
    allergens: [dairy]
    availability: true
    tags: [cold]
""".strip(),
        encoding="utf-8",
    )
    restaurant_info_path.write_text(
        """
restaurant:
  name: Test Bistro
""".strip(),
        encoding="utf-8",
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

    summary = build_menu_grounded_user_message_seed(
        menu_path=menu_path,
        restaurant_info_path=restaurant_info_path,
        output_path=output_path,
    )

    assert summary["records_written"] >= 12
    assert output_path.exists()
    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    rows = [json.loads(line) for line in lines]
    assert all(row["seed_status"] == "needs_review" for row in rows)
    assert all(row["include_for_canonical_preview"] is False for row in rows)
    assert any(row["menu_item_name"] == "Mercimek Çorbası" for row in rows)
    assert any(row["menu_item_name"] == "Ayran" for row in rows)
    assert any(row["intent_category"] == "unsupported_item_probe" for row in rows)
    assert any(
        row["intent_category"] == "unsupported_item_probe"
        and "Pizza" in row["turkish_user_message"]
        for row in rows
    )
    assert not any(
        row["intent_category"] == "order_item"
        and "Pizza" in row["turkish_user_message"]
        for row in rows
    )

    after_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in processed_paths
    }
    assert before_hashes == after_hashes


def test_main_prints_summary(capsys, tmp_path):
    menu_path = tmp_path / "menu.yaml"
    restaurant_info_path = tmp_path / "restaurant_info.yaml"
    output_path = tmp_path / "menu_grounded_user_message_seed_review.jsonl"

    menu_path.write_text(
        """
menu:
  - id: s1
    name: Mercimek Çorbası
    category: Çorba
    price: 85
    description: Kırmızı mercimek ile hazırlanır.
    allergens: [gluten]
    availability: true
    tags: [vegetarian]
""".strip(),
        encoding="utf-8",
    )
    restaurant_info_path.write_text("restaurant:\n  name: Test Bistro\n", encoding="utf-8")

    exit_code = main(
        [
            "--menu",
            str(menu_path),
            "--restaurant-info",
            str(restaurant_info_path),
            "--output",
            str(output_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Menu-grounded user-message seed build complete." in captured.out
    assert "Records written:" in captured.out
