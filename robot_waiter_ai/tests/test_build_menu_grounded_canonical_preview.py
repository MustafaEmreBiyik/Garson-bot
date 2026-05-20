from __future__ import annotations

import hashlib
import json
from pathlib import Path

from robot_waiter_ai.training.build_menu_grounded_canonical_preview import (
    build_menu_grounded_canonical_preview,
    main,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_build_menu_grounded_canonical_preview_exports_only_approved_rows(tmp_path):
    input_path = tmp_path / "menu_grounded_user_message_seed_reviewed.jsonl"
    output_path = tmp_path / "menu_grounded_user_message_canonical_preview.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source": "menu_grounded_seed",
                "intent_category": "order_item",
                "menu_item_name": "Ayran",
                "turkish_user_message": "Ayran sipariş etmek istiyorum.",
                "seed_status": "approved_seed",
                "seed_notes": "approved",
                "include_for_canonical_preview": True,
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "unsupported_item_probe",
                "menu_item_name": None,
                "turkish_user_message": "Pizza sipariş etmek istiyorum.",
                "seed_status": "approved_probe",
                "seed_notes": "probe",
                "include_for_canonical_preview": True,
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "ask_price",
                "menu_item_name": "Ayran",
                "turkish_user_message": "Ayran ne kadar?",
                "seed_status": "rejected_seed",
                "seed_notes": "rejected",
                "include_for_canonical_preview": False,
            },
            {
                "source": "other_source",
                "intent_category": "order_item",
                "menu_item_name": "Ayran",
                "turkish_user_message": "Ayran sipariş etmek istiyorum.",
                "seed_status": "approved_seed",
                "seed_notes": "wrong source",
                "include_for_canonical_preview": True,
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

    summary = build_menu_grounded_canonical_preview(
        input_path=input_path,
        output_path=output_path,
    )

    assert summary["input_records_read"] == 4
    assert summary["preview_records_written"] == 2
    assert summary["rejected_or_skipped_records"] == 2
    assert output_path.exists()
    assert output_path.name == "menu_grounded_user_message_canonical_preview.jsonl"

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 2
    assert all(row["preview_status"] == "needs_review" for row in rows)
    assert all(row["include_for_grounded_paraphrase_dataset"] is False for row in rows)
    assert all("canonical_response_preview" in row for row in rows)
    assert all("deterministic_status" in row for row in rows)
    assert {row["seed_status"] for row in rows} == {"approved_seed", "approved_probe"}

    after_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in processed_paths
    }
    assert before_hashes == after_hashes


def test_main_prints_summary(capsys, tmp_path):
    input_path = tmp_path / "menu_grounded_user_message_seed_reviewed.jsonl"
    output_path = tmp_path / "menu_grounded_user_message_canonical_preview.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source": "menu_grounded_seed",
                "intent_category": "ask_menu",
                "menu_item_name": None,
                "turkish_user_message": "Menüde hangi içecekler var?",
                "seed_status": "approved_seed",
                "seed_notes": "approved",
                "include_for_canonical_preview": True,
            }
        ],
    )

    exit_code = main(["--input", str(input_path), "--output", str(output_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Menu-grounded canonical preview build complete." in captured.out
    assert "Preview records written: 1" in captured.out
