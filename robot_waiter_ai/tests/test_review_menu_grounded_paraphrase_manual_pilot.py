from __future__ import annotations

import hashlib
import json
from pathlib import Path

from robot_waiter_ai.training.review_menu_grounded_paraphrase_manual_pilot import (
    main,
    review_menu_grounded_paraphrase_manual_pilot,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_review_menu_grounded_paraphrase_manual_pilot_applies_semantic_gate(tmp_path):
    input_path = tmp_path / "menu_grounded_paraphrase_manual_pilot_10.jsonl"
    output_path = tmp_path / "menu_grounded_paraphrase_manual_pilot_10_reviewed.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "id": "ok_price",
                "intent_category": "ask_price",
                "candidate_type": "supported_menu_response",
                "canonical_response": "Ayran: Tuzlu yoğurt içeceği. Fiyat: 45.00 TL. Lütfen mutfakla teyit ediniz.",
                "must_preserve_terms": ["Ayran", "45.00 TL", "Lütfen mutfakla teyit ediniz."],
                "must_not_introduce": ["new prices", "allergy safety guarantees"],
                "safe_paraphrase": "Ayran tuzlu yoğurt içeceğidir. Fiyatı 45.00 TL. Lütfen mutfakla teyit ediniz.",
                "paraphrase_status": "accepted_manual_paraphrase",
                "include_for_processed_dataset": False,
            },
            {
                "id": "missing_term",
                "intent_category": "ask_price",
                "candidate_type": "supported_menu_response",
                "canonical_response": "Ayran: Fiyat: 45.00 TL.",
                "must_preserve_terms": ["Ayran", "45.00 TL"],
                "must_not_introduce": ["new prices"],
                "safe_paraphrase": "Fiyatı 45.00 TL.",
                "paraphrase_status": "accepted_manual_paraphrase",
                "include_for_processed_dataset": False,
            },
            {
                "id": "forbidden_fact",
                "intent_category": "ask_price",
                "candidate_type": "supported_menu_response",
                "canonical_response": "Ayran: Fiyat: 45.00 TL.",
                "must_preserve_terms": ["Ayran", "45.00 TL"],
                "must_not_introduce": ["discounts"],
                "safe_paraphrase": "Ayran 45.00 TL ama bugün indirim var.",
                "paraphrase_status": "accepted_manual_paraphrase",
                "include_for_processed_dataset": False,
            },
            {
                "id": "weak_caution",
                "intent_category": "ask_allergy",
                "candidate_type": "supported_menu_response",
                "canonical_response": "Alerjenler: dairy. Lütfen mutfakla teyit ediniz.",
                "must_preserve_terms": ["Lütfen mutfakla teyit ediniz."],
                "must_not_introduce": ["allergy safety guarantees"],
                "safe_paraphrase": "Alerjenler: dairy.",
                "paraphrase_status": "accepted_manual_paraphrase",
                "include_for_processed_dataset": False,
            },
            {
                "id": "probe_missing_reject",
                "intent_category": "unsupported_item_probe",
                "candidate_type": "rejection_probe_response",
                "canonical_response": "Bu ürün menümüzde bulunmuyor.",
                "must_preserve_terms": ["menümüzde bulunmuyor"],
                "must_not_introduce": ["unsupported menu items"],
                "safe_paraphrase": "Şu anda yardımcı olamıyorum.",
                "paraphrase_status": "accepted_manual_paraphrase",
                "include_for_processed_dataset": False,
            },
            {
                "id": "confirm_changed_state",
                "intent_category": "confirm_order",
                "candidate_type": "supported_menu_response",
                "canonical_response": "Siparişinizi onaylıyorum.\n3 x Ayran = 135.00 TL\nToplam: 135.00 TL\nNot: Bu yalnızca MVP/demo onayıdır; gerçek restoran gönderimi yapılmaz.",
                "must_preserve_terms": ["135.00 TL", "3 x Ayran = 135"],
                "must_not_introduce": ["order state changes not present in canonical_response"],
                "safe_paraphrase": "Siparişiniz onaylandı. 3 x Ayran = 135.00 TL. Toplam: 135.00 TL. Not: Bu yalnızca MVP/demo onayıdır; gerçek restoran gönderimi yapılmaz.",
                "paraphrase_status": "accepted_manual_paraphrase",
                "include_for_processed_dataset": False,
            },
            {
                "id": "duplicate_1",
                "intent_category": "order_item",
                "candidate_type": "supported_menu_response",
                "canonical_response": "Ekledim: 1 x Ayran.",
                "must_preserve_terms": ["1 x Ayran"],
                "must_not_introduce": [],
                "safe_paraphrase": "1 x Ayran eklendi.",
                "paraphrase_status": "accepted_manual_paraphrase",
                "include_for_processed_dataset": False,
            },
            {
                "id": "duplicate_2",
                "intent_category": "ask_allergy",
                "candidate_type": "supported_menu_response",
                "canonical_response": "Ekledim: 1 x Ayran.",
                "must_preserve_terms": ["1 x Ayran"],
                "must_not_introduce": [],
                "safe_paraphrase": "1 x Ayran eklendi.",
                "paraphrase_status": "accepted_manual_paraphrase",
                "include_for_processed_dataset": False,
            },
        ],
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
    before_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in processed_paths}

    summary = review_menu_grounded_paraphrase_manual_pilot(
        input_path=input_path,
        output_path=output_path,
    )

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_id = {row["id"]: row for row in rows}

    assert summary["input_records_read"] == 8
    assert by_id["ok_price"]["semantic_review_status"] == "approved_semantic_review"
    assert by_id["ok_price"]["approved_for_processed_candidate"] is True
    assert by_id["missing_term"]["semantic_review_status"] == "rejected_missing_preserve_term"
    assert by_id["forbidden_fact"]["semantic_review_status"] == "rejected_introduces_forbidden_fact"
    assert by_id["weak_caution"]["semantic_review_status"] == "rejected_missing_preserve_term"
    assert by_id["probe_missing_reject"]["semantic_review_status"] == "rejected_missing_preserve_term"
    assert by_id["confirm_changed_state"]["semantic_review_status"] == "rejected_changes_order_state"
    assert by_id["duplicate_1"]["semantic_review_status"] == "approved_semantic_review"
    assert by_id["duplicate_2"]["semantic_review_status"] == "rejected_low_value_duplicate"
    assert all(row["include_for_processed_dataset"] is False for row in rows)

    after_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in processed_paths}
    assert before_hashes == after_hashes


def test_main_prints_summary(capsys, tmp_path):
    input_path = tmp_path / "menu_grounded_paraphrase_manual_pilot_10.jsonl"
    output_path = tmp_path / "menu_grounded_paraphrase_manual_pilot_10_reviewed.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "id": "ok",
                "intent_category": "order_item",
                "candidate_type": "supported_menu_response",
                "canonical_response": "Ekledim: 1 x Ayran.",
                "must_preserve_terms": ["1 x Ayran"],
                "must_not_introduce": [],
                "safe_paraphrase": "1 x Ayran eklendi.",
                "paraphrase_status": "accepted_manual_paraphrase",
                "include_for_processed_dataset": False,
            }
        ],
    )

    exit_code = main(["--input", str(input_path), "--output", str(output_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Menu-grounded paraphrase semantic review complete." in captured.out
    assert "approved_semantic_review: 1" in captured.out
