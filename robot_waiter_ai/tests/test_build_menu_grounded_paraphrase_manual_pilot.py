from __future__ import annotations

import hashlib
import json
from pathlib import Path

from robot_waiter_ai.training.build_menu_grounded_paraphrase_manual_pilot import (
    build_menu_grounded_paraphrase_manual_pilot,
    main,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_build_menu_grounded_paraphrase_manual_pilot_writes_exactly_ten_records(tmp_path):
    input_path = tmp_path / "menu_grounded_grounded_paraphrase_candidates.jsonl"
    output_path = tmp_path / "menu_grounded_paraphrase_manual_pilot_10.jsonl"

    records = []
    for idx in range(3):
        records.append(
            {
                "id": f"mgp_order_{idx}",
                "source": "menu_grounded_seed",
                "intent_category": "order_item",
                "menu_item_name": f"Item {idx}",
                "user_message": f"Item {idx} sipariş etmek istiyorum.",
                "canonical_response": f"Ekledim: 1 x Item {idx}.",
                "candidate_type": "supported_menu_response",
                "canonical_review_status": "approved_canonical_preview",
                "canonical_review_notes": "ok",
                "must_preserve_terms": [f"Item {idx}"],
                "must_not_introduce": ["unsupported menu items"],
                "safe_paraphrase": "",
                "paraphrase_status": "needs_manual_review",
                "include_for_processed_dataset": False,
            }
        )
    for idx in range(3):
        records.append(
            {
                "id": f"mgp_info_{idx}",
                "source": "menu_grounded_seed",
                "intent_category": ["ask_price", "ask_menu", "ask_ingredient"][idx],
                "menu_item_name": f"Info {idx}" if idx != 1 else None,
                "user_message": f"Info {idx} soru",
                "canonical_response": f"Bilgi yanıtı {idx}. Fiyat: {idx + 10}.00 TL. Lütfen mutfakla teyit ediniz.",
                "candidate_type": "supported_menu_response",
                "canonical_review_status": "approved_canonical_preview",
                "canonical_review_notes": "ok",
                "must_preserve_terms": [f"{idx + 10}.00 TL"],
                "must_not_introduce": ["unsupported menu items"],
                "safe_paraphrase": "",
                "paraphrase_status": "needs_manual_review",
                "include_for_processed_dataset": False,
            }
        )
    for idx in range(3):
        records.append(
            {
                "id": f"mgp_allergy_{idx}",
                "source": "menu_grounded_seed",
                "intent_category": "ask_allergy",
                "menu_item_name": f"Allergy {idx}",
                "user_message": f"Allergy {idx} içeriyor mu?",
                "canonical_response": "Alerjenler: dairy. Lütfen mutfakla teyit ediniz.",
                "candidate_type": "supported_menu_response",
                "canonical_review_status": "approved_canonical_preview",
                "canonical_review_notes": "ok",
                "must_preserve_terms": ["Lütfen mutfakla teyit ediniz."],
                "must_not_introduce": ["allergy safety guarantees"],
                "safe_paraphrase": "",
                "paraphrase_status": "needs_manual_review",
                "include_for_processed_dataset": False,
            }
        )
    records.append(
        {
            "id": "mgp_probe_1",
            "source": "menu_grounded_seed",
            "intent_category": "unsupported_item_probe",
            "menu_item_name": None,
            "user_message": "Pizza var mı?",
            "canonical_response": "Bu ürün menümüzde bulunmuyor.",
            "candidate_type": "rejection_probe_response",
            "canonical_review_status": "approved_rejection_probe",
            "canonical_review_notes": "probe",
            "must_preserve_terms": ["menümüzde bulunmuyor"],
            "must_not_introduce": ["unsupported menu items"],
            "safe_paraphrase": "",
            "paraphrase_status": "needs_manual_review",
            "include_for_processed_dataset": False,
        }
    )
    records.append(
        {
            "id": "mgp_remove_1",
            "source": "menu_grounded_seed",
            "intent_category": "remove_item",
            "menu_item_name": "Ayran",
            "user_message": "Ayranı çıkarır mısınız?",
            "canonical_response": "Çıkardım: Ayran.",
            "candidate_type": "supported_menu_response",
            "canonical_review_status": "approved_canonical_preview",
            "canonical_review_notes": "ok",
            "must_preserve_terms": ["Ayran"],
            "must_not_introduce": ["unsupported menu items"],
            "safe_paraphrase": "",
            "paraphrase_status": "needs_manual_review",
            "include_for_processed_dataset": False,
        }
    )
    records.append(
        {
            "id": "mgp_confirm_1",
            "source": "menu_grounded_seed",
            "intent_category": "confirm_order",
            "menu_item_name": None,
            "user_message": "Siparişi onaylıyorum.",
            "canonical_response": "Siparişinizi onaylıyorum. Toplam: 100.00 TL",
            "candidate_type": "supported_menu_response",
            "canonical_review_status": "approved_canonical_preview",
            "canonical_review_notes": "ok",
            "must_preserve_terms": ["100.00 TL"],
            "must_not_introduce": ["new prices"],
            "safe_paraphrase": "",
            "paraphrase_status": "needs_manual_review",
            "include_for_processed_dataset": False,
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
    before_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in processed_paths}

    summary = build_menu_grounded_paraphrase_manual_pilot(
        input_path=input_path,
        output_path=output_path,
    )

    assert summary["records_written"] == 10
    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 10
    assert all(row["safe_paraphrase"] == "" for row in rows)
    assert all(row["paraphrase_status"] == "needs_manual_review" for row in rows)
    assert all(row["include_for_processed_dataset"] is False for row in rows)
    assert all(row["manual_pilot_version"] == "v1_10" for row in rows)
    assert any(row["candidate_type"] == "rejection_probe_response" for row in rows)

    after_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in processed_paths}
    assert before_hashes == after_hashes


def test_main_prints_summary(capsys, tmp_path):
    input_path = tmp_path / "menu_grounded_grounded_paraphrase_candidates.jsonl"
    output_path = tmp_path / "menu_grounded_paraphrase_manual_pilot_10.jsonl"

    records = []
    for idx in range(10):
        records.append(
            {
                "id": f"mgp_{idx}",
                "source": "menu_grounded_seed",
                "intent_category": "order_item" if idx < 2 else "ask_allergy",
                "menu_item_name": f"Item {idx}",
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
    exit_code = main(["--input", str(input_path), "--output", str(output_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Menu-grounded paraphrase manual pilot build complete." in captured.out
    assert "Pilot records written: 10" in captured.out
