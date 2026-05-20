from __future__ import annotations

import hashlib
import json
from pathlib import Path

from robot_waiter_ai.training.build_menu_grounded_paraphrase_manual_pilot_v2 import (
    build_menu_grounded_paraphrase_manual_pilot_v2,
    main,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_build_menu_grounded_paraphrase_manual_pilot_v2_excludes_first_pilot_ids(tmp_path):
    input_path = tmp_path / "menu_grounded_grounded_paraphrase_candidates.jsonl"
    used_pilot_path = tmp_path / "menu_grounded_paraphrase_manual_pilot_10.jsonl"
    output_path = tmp_path / "menu_grounded_paraphrase_manual_pilot_10_v2.jsonl"

    records = []
    for idx in range(3):
        records.append(
            {
                "id": f"used_{idx}",
                "source": "menu_grounded_seed",
                "intent_category": "order_item",
                "menu_item_name": f"Used {idx}",
                "user_message": f"Used {idx} sipariş etmek istiyorum.",
                "canonical_response": f"Ekledim: 1 x Used {idx}.",
                "candidate_type": "supported_menu_response",
                "canonical_review_status": "approved_canonical_preview",
                "canonical_review_notes": "ok",
                "must_preserve_terms": [f"Used {idx}"],
                "must_not_introduce": ["unsupported menu items"],
                "safe_paraphrase": "",
                "paraphrase_status": "needs_manual_review",
                "include_for_processed_dataset": False,
            }
        )

    remaining_specs = [
        ("ask_ingredient", "Domates Çorbası içinde ne var?"),
        ("ask_ingredient", "Mercimek Çorbası içinde ne var?"),
        ("ask_ingredient", "Izgara Tavuk Salata hangi malzemelerle hazırlanıyor?"),
        ("ask_allergy", "Ayran içinde süt ürünü var mı?"),
        ("ask_allergy", "Mercimek Çorbası fındık veya fıstık içeriyor mu?"),
        ("ask_menu", "Menüde neler var?"),
        ("remove_item", "Siparişimden Ayran'ı çıkarabilir misiniz?"),
        ("remove_item", "Siparişimden Limonata'yı çıkarabilir misiniz?"),
        ("unsupported_item_probe", "Pizza sipariş etmek istiyorum."),
        ("off_topic_rejection_probe", "Bana hava durumunu söyler misiniz?"),
        ("confirm_order", "Siparişimi onaylamak istiyorum."),
    ]
    for idx, (intent, user_message) in enumerate(remaining_specs):
        records.append(
            {
                "id": f"new_{idx}",
                "source": "menu_grounded_seed",
                "intent_category": intent,
                "menu_item_name": "Ayran" if intent not in {"ask_menu", "off_topic_rejection_probe", "unsupported_item_probe", "confirm_order"} else None,
                "user_message": user_message,
                "canonical_response": f"Yanıt {idx}.",
                "candidate_type": "rejection_probe_response"
                if "probe" in intent
                else "supported_menu_response",
                "canonical_review_status": "approved_rejection_probe"
                if "probe" in intent
                else "approved_canonical_preview",
                "canonical_review_notes": "ok",
                "must_preserve_terms": ["Ayran"] if intent not in {"ask_menu", "off_topic_rejection_probe", "unsupported_item_probe", "confirm_order"} else [],
                "must_not_introduce": ["unsupported menu items"],
                "safe_paraphrase": "",
                "paraphrase_status": "needs_manual_review",
                "include_for_processed_dataset": False,
            }
        )

    _write_jsonl(input_path, records)
    _write_jsonl(
        used_pilot_path,
        [{"id": f"used_{idx}"} for idx in range(3)],
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
    before_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in processed_paths}

    summary = build_menu_grounded_paraphrase_manual_pilot_v2(
        input_path=input_path,
        used_pilot_path=used_pilot_path,
        output_path=output_path,
    )

    assert summary["records_written"] == 10
    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 10
    assert all(not row["id"].startswith("used_") for row in rows)
    assert all(row["safe_paraphrase"] == "" for row in rows)
    assert all(row["paraphrase_status"] == "needs_manual_review" for row in rows)
    assert all(row["include_for_processed_dataset"] is False for row in rows)
    assert all(row["manual_pilot_version"] == "v2_10" for row in rows)
    assert any(row["candidate_type"] == "rejection_probe_response" for row in rows)

    after_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in processed_paths}
    assert before_hashes == after_hashes


def test_main_prints_summary(capsys, tmp_path):
    input_path = tmp_path / "menu_grounded_grounded_paraphrase_candidates.jsonl"
    used_pilot_path = tmp_path / "menu_grounded_paraphrase_manual_pilot_10.jsonl"
    output_path = tmp_path / "menu_grounded_paraphrase_manual_pilot_10_v2.jsonl"

    records = []
    for idx in range(10):
        records.append(
            {
                "id": f"mgp_{idx}",
                "source": "menu_grounded_seed",
                "intent_category": "ask_ingredient" if idx < 3 else "remove_item",
                "menu_item_name": "Ayran",
                "user_message": f"Mesaj {idx}",
                "canonical_response": f"Yanıt {idx}",
                "candidate_type": "rejection_probe_response" if idx == 9 else "supported_menu_response",
                "canonical_review_status": "approved_rejection_probe" if idx == 9 else "approved_canonical_preview",
                "canonical_review_notes": "ok",
                "must_preserve_terms": [],
                "must_not_introduce": [],
                "safe_paraphrase": "",
                "paraphrase_status": "needs_manual_review",
                "include_for_processed_dataset": False,
            }
        )

    _write_jsonl(input_path, records)
    _write_jsonl(used_pilot_path, [])
    exit_code = main(
        [
            "--input",
            str(input_path),
            "--used-pilot",
            str(used_pilot_path),
            "--output",
            str(output_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Menu-grounded paraphrase manual pilot v2 build complete." in captured.out
    assert "Pilot records written: 10" in captured.out
