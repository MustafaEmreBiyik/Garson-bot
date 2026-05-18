from __future__ import annotations

import hashlib
import json
from pathlib import Path

from robot_waiter_ai.training.review_menu_grounded_canonical_preview import (
    main,
    review_menu_grounded_canonical_preview,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_review_menu_grounded_canonical_preview_handles_key_review_cases(tmp_path):
    input_path = tmp_path / "menu_grounded_user_message_canonical_preview.jsonl"
    output_path = tmp_path / "menu_grounded_user_message_canonical_reviewed.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source": "menu_grounded_seed",
                "intent_category": "ask_price",
                "menu_item_name": "Ayran",
                "turkish_user_message": "Ayran ne kadar?",
                "seed_status": "approved_seed",
                "seed_notes": "approved",
                "include_for_canonical_preview": True,
                "canonical_response_preview": "Ayran: Tuzlu yoğurt içeceği. Fiyat: 45.00 TL. Alerjenler: dairy. Lütfen mutfakla teyit ediniz.",
                "deterministic_status": "menu_question",
                "preview_status": "needs_review",
                "include_for_grounded_paraphrase_dataset": False,
                "preview_notes": "",
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "ask_allergy",
                "menu_item_name": "Ayran",
                "turkish_user_message": "Ayran süt ürünü içeriyor mu?",
                "seed_status": "approved_seed",
                "seed_notes": "approved",
                "include_for_canonical_preview": True,
                "canonical_response_preview": "Ayran: Tuzlu yoğurt içeceği. Fiyat: 45.00 TL. Alerjenler: dairy. Lütfen mutfakla teyit ediniz.",
                "deterministic_status": "menu_question",
                "preview_status": "needs_review",
                "include_for_grounded_paraphrase_dataset": False,
                "preview_notes": "",
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "unsupported_item_probe",
                "menu_item_name": None,
                "turkish_user_message": "Pizza sipariş etmek istiyorum.",
                "seed_status": "approved_probe",
                "seed_notes": "probe",
                "include_for_canonical_preview": True,
                "canonical_response_preview": "Bu ürün menümüzde bulunmuyor. İsterseniz mevcut kategorilerden öneri sunabilirim.",
                "deterministic_status": "unavailable_item",
                "preview_status": "needs_review",
                "include_for_grounded_paraphrase_dataset": False,
                "preview_notes": "",
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "off_topic_rejection_probe",
                "menu_item_name": None,
                "turkish_user_message": "Bana hava durumunu söyler misiniz?",
                "seed_status": "approved_probe",
                "seed_notes": "probe",
                "include_for_canonical_preview": True,
                "canonical_response_preview": "Bu konuda yardımcı olamıyorum. Menü veya siparişle ilgili sorabilir misiniz?",
                "deterministic_status": "off_topic",
                "preview_status": "needs_review",
                "include_for_grounded_paraphrase_dataset": False,
                "preview_notes": "",
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "ask_menu",
                "menu_item_name": None,
                "turkish_user_message": "Menüde hangi içecekler var?",
                "seed_status": "approved_seed",
                "seed_notes": "approved",
                "include_for_canonical_preview": True,
                "canonical_response_preview": "Siparişe eklemek istediğiniz ürünü yazar mısınız?",
                "deterministic_status": "add_item",
                "preview_status": "needs_review",
                "include_for_grounded_paraphrase_dataset": False,
                "preview_notes": "",
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "order_item",
                "menu_item_name": "Ayran",
                "turkish_user_message": "Bir Ayran alabilir miyim?",
                "seed_status": "approved_seed",
                "seed_notes": "approved",
                "include_for_canonical_preview": True,
                "canonical_response_preview": "Ekledim: 1 x Ayran. Başka bir isteğiniz var mı?",
                "deterministic_status": "add_item",
                "preview_status": "needs_review",
                "include_for_grounded_paraphrase_dataset": False,
                "preview_notes": "",
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "order_item",
                "menu_item_name": "Ayran",
                "turkish_user_message": "Bir Ayran alabilir miyim?",
                "seed_status": "approved_seed",
                "seed_notes": "approved duplicate",
                "include_for_canonical_preview": True,
                "canonical_response_preview": "Ekledim: 1 x Ayran. Başka bir isteğiniz var mı?",
                "deterministic_status": "add_item",
                "preview_status": "needs_review",
                "include_for_grounded_paraphrase_dataset": False,
                "preview_notes": "",
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "ask_allergy",
                "menu_item_name": "Ayran",
                "turkish_user_message": "Ayran güvenli mi?",
                "seed_status": "approved_seed",
                "seed_notes": "unsafe allergy",
                "include_for_canonical_preview": True,
                "canonical_response_preview": "Bu ürün kesinlikle güvenli ve alerjen içermez.",
                "deterministic_status": "menu_question",
                "preview_status": "needs_review",
                "include_for_grounded_paraphrase_dataset": False,
                "preview_notes": "",
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
    before_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in processed_paths
    }

    summary = review_menu_grounded_canonical_preview(
        input_path=input_path,
        output_path=output_path,
    )

    assert summary["input_records_read"] == 8
    assert output_path.exists()

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    by_message = {}
    for row in rows:
        by_message.setdefault((row["intent_category"], row["turkish_user_message"]), []).append(row)

    price_row = by_message[("ask_price", "Ayran ne kadar?")][0]
    assert price_row["canonical_review_status"] == "approved_canonical_preview"
    assert price_row["include_for_grounded_paraphrase_dataset"] is True
    assert "grounded price information" in price_row["canonical_review_notes"]

    allergy_row = by_message[("ask_allergy", "Ayran süt ürünü içeriyor mu?")][0]
    assert allergy_row["canonical_review_status"] == "approved_canonical_preview"

    unsupported_row = by_message[("unsupported_item_probe", "Pizza sipariş etmek istiyorum.")][0]
    assert unsupported_row["canonical_review_status"] == "approved_rejection_probe"

    off_topic_row = by_message[("off_topic_rejection_probe", "Bana hava durumunu söyler misiniz?")][0]
    assert off_topic_row["canonical_review_status"] == "approved_rejection_probe"

    bad_match_row = by_message[("ask_menu", "Menüde hangi içecekler var?")][0]
    assert bad_match_row["canonical_review_status"] == "rejected_bad_deterministic_match"

    duplicate_rows = by_message[("order_item", "Bir Ayran alabilir miyim?")]
    duplicate_statuses = {row["canonical_review_status"] for row in duplicate_rows}
    assert "approved_canonical_preview" in duplicate_statuses
    assert "rejected_low_value_or_duplicate" in duplicate_statuses

    unsafe_allergy_row = by_message[("ask_allergy", "Ayran güvenli mi?")][0]
    assert unsafe_allergy_row["canonical_review_status"] == "rejected_bad_deterministic_match"

    after_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in processed_paths
    }
    assert before_hashes == after_hashes


def test_main_prints_summary(capsys, tmp_path):
    input_path = tmp_path / "menu_grounded_user_message_canonical_preview.jsonl"
    output_path = tmp_path / "menu_grounded_user_message_canonical_reviewed.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source": "menu_grounded_seed",
                "intent_category": "unsupported_item_probe",
                "menu_item_name": None,
                "turkish_user_message": "Pizza sipariş etmek istiyorum.",
                "seed_status": "approved_probe",
                "seed_notes": "probe",
                "include_for_canonical_preview": True,
                "canonical_response_preview": "Bu ürün menümüzde bulunmuyor. İsterseniz mevcut kategorilerden öneri sunabilirim.",
                "deterministic_status": "unavailable_item",
                "preview_status": "needs_review",
                "include_for_grounded_paraphrase_dataset": False,
                "preview_notes": "",
            }
        ],
    )

    exit_code = main(["--input", str(input_path), "--output", str(output_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Menu-grounded canonical review complete." in captured.out
    assert "approved_rejection_probe: 1" in captured.out
