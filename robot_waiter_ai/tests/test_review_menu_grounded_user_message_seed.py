from __future__ import annotations

import hashlib
import json
from pathlib import Path

from robot_waiter_ai.training.review_menu_grounded_user_message_seed import (
    main,
    review_menu_grounded_user_message_seed,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_review_menu_grounded_user_message_seed_marks_supported_and_probe_rows(tmp_path):
    input_path = tmp_path / "menu_grounded_user_message_seed_review_refined.jsonl"
    output_path = tmp_path / "menu_grounded_user_message_seed_reviewed.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source": "menu_grounded_seed",
                "intent_category": "order_item",
                "menu_item_name": "Ayran",
                "turkish_user_message": "Ayran sipariş etmek istiyorum.",
                "seed_status": "needs_review",
                "seed_notes": "",
                "include_for_canonical_preview": False,
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "ask_menu",
                "menu_item_name": None,
                "turkish_user_message": "Menüde hangi içecekler var?",
                "seed_status": "needs_review",
                "seed_notes": "",
                "include_for_canonical_preview": False,
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "confirm_order",
                "menu_item_name": None,
                "turkish_user_message": "Bu kadar, siparişi onaylayabiliriz.",
                "seed_status": "needs_review",
                "seed_notes": "",
                "include_for_canonical_preview": False,
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "unsupported_item_probe",
                "menu_item_name": None,
                "turkish_user_message": "Pizza sipariş etmek istiyorum.",
                "seed_status": "needs_review",
                "seed_notes": "",
                "include_for_canonical_preview": False,
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "off_topic_rejection_probe",
                "menu_item_name": None,
                "turkish_user_message": "Bana hava durumunu söyler misiniz?",
                "seed_status": "needs_review",
                "seed_notes": "",
                "include_for_canonical_preview": False,
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

    summary = review_menu_grounded_user_message_seed(
        input_path=input_path,
        output_path=output_path,
    )

    assert output_path.exists()
    assert summary["records_written"] == 5

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows[0]["seed_status"] == "approved_seed"
    assert rows[0]["include_for_canonical_preview"] is True
    assert rows[1]["seed_status"] == "approved_seed"
    assert rows[1]["include_for_canonical_preview"] is True
    assert rows[2]["seed_status"] == "approved_seed"
    assert rows[2]["include_for_canonical_preview"] is True
    assert rows[3]["seed_status"] == "approved_probe"
    assert rows[3]["include_for_canonical_preview"] is True
    assert rows[4]["seed_status"] == "approved_probe"
    assert rows[4]["include_for_canonical_preview"] is True

    after_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in processed_paths
    }
    assert before_hashes == after_hashes


def test_review_menu_grounded_user_message_seed_rejects_malformed_rows(tmp_path):
    input_path = tmp_path / "menu_grounded_user_message_seed_review_refined.jsonl"
    output_path = tmp_path / "menu_grounded_user_message_seed_reviewed.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source": "menu_grounded_seed",
                "intent_category": "ask_price",
                "menu_item_name": None,
                "turkish_user_message": "Ayran ne kadar?",
                "seed_status": "needs_review",
                "seed_notes": "",
                "include_for_canonical_preview": False,
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "order_item",
                "menu_item_name": "Ayran",
                "turkish_user_message": "",
                "seed_status": "needs_review",
                "seed_notes": "",
                "include_for_canonical_preview": False,
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "",
                "menu_item_name": "Ayran",
                "turkish_user_message": "Ayran sipariş etmek istiyorum.",
                "seed_status": "needs_review",
                "seed_notes": "",
                "include_for_canonical_preview": False,
            },
        ],
    )

    summary = review_menu_grounded_user_message_seed(
        input_path=input_path,
        output_path=output_path,
    )
    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert summary["status_counts"]["rejected_seed"] == 3
    assert all(row["seed_status"] == "rejected_seed" for row in rows)
    assert all(row["include_for_canonical_preview"] is False for row in rows)


def test_main_prints_summary(capsys, tmp_path):
    input_path = tmp_path / "menu_grounded_user_message_seed_review_refined.jsonl"
    output_path = tmp_path / "menu_grounded_user_message_seed_reviewed.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source": "menu_grounded_seed",
                "intent_category": "off_topic_rejection_probe",
                "menu_item_name": None,
                "turkish_user_message": "Bana hava durumunu söyler misiniz?",
                "seed_status": "needs_review",
                "seed_notes": "",
                "include_for_canonical_preview": False,
            }
        ],
    )

    exit_code = main(["--input", str(input_path), "--output", str(output_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Menu-grounded user-message seed review complete." in captured.out
    assert "Seed status counts:" in captured.out
