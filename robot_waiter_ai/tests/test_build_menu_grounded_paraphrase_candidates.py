from __future__ import annotations

import hashlib
import json
from pathlib import Path

from robot_waiter_ai.training.build_menu_grounded_paraphrase_candidates import (
    build_menu_grounded_paraphrase_candidates,
    main,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_build_menu_grounded_paraphrase_candidates_exports_only_approved_rows(tmp_path):
    input_path = tmp_path / "menu_grounded_user_message_canonical_reviewed.jsonl"
    output_path = tmp_path / "menu_grounded_grounded_paraphrase_candidates.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source": "menu_grounded_seed",
                "intent_category": "ask_price",
                "menu_item_name": "Ayran",
                "turkish_user_message": "Ayran ne kadar?",
                "canonical_response_preview": "Ayran: Tuzlu yoğurt içeceği. Fiyat: 45.00 TL. Alerjenler: dairy. Lütfen mutfakla teyit ediniz.",
                "canonical_review_status": "approved_canonical_preview",
                "canonical_review_notes": "approved",
                "include_for_grounded_paraphrase_dataset": True,
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "unsupported_item_probe",
                "menu_item_name": None,
                "turkish_user_message": "Pizza sipariş etmek istiyorum.",
                "canonical_response_preview": "Bu ürün menümüzde bulunmuyor. İsterseniz mevcut kategorilerden öneri sunabilirim.",
                "canonical_review_status": "approved_rejection_probe",
                "canonical_review_notes": "probe",
                "include_for_grounded_paraphrase_dataset": True,
            },
            {
                "source": "menu_grounded_seed",
                "intent_category": "ask_menu",
                "menu_item_name": None,
                "turkish_user_message": "Menüde hangi içecekler var?",
                "canonical_response_preview": "Siparişe eklemek istediğiniz ürünü yazar mısınız?",
                "canonical_review_status": "rejected_bad_deterministic_match",
                "canonical_review_notes": "reject",
                "include_for_grounded_paraphrase_dataset": False,
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

    summary = build_menu_grounded_paraphrase_candidates(
        input_path=input_path,
        output_path=output_path,
    )

    assert summary["input_records_read"] == 3
    assert summary["candidate_records_written"] == 2
    assert summary["skipped_records"] == 1
    assert output_path.exists()
    assert output_path.name == "menu_grounded_grounded_paraphrase_candidates.jsonl"

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 2
    assert rows[0]["safe_paraphrase"] == ""
    assert rows[0]["paraphrase_status"] == "needs_manual_review"
    assert rows[0]["include_for_processed_dataset"] is False
    assert "Ayran" in rows[0]["must_preserve_terms"]
    assert "45.00 TL" in rows[0]["must_preserve_terms"]
    assert "Lütfen mutfakla teyit ediniz." in rows[0]["must_preserve_terms"]
    assert "unsupported menu items" in rows[0]["must_not_introduce"]
    assert "allergy safety guarantees" in rows[0]["must_not_introduce"]
    assert rows[0]["candidate_type"] == "supported_menu_response"

    assert rows[1]["candidate_type"] == "rejection_probe_response"
    assert "menümüzde bulunmuyor" in rows[1]["must_preserve_terms"]

    after_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in processed_paths
    }
    assert before_hashes == after_hashes


def test_main_prints_summary(capsys, tmp_path):
    input_path = tmp_path / "menu_grounded_user_message_canonical_reviewed.jsonl"
    output_path = tmp_path / "menu_grounded_grounded_paraphrase_candidates.jsonl"

    _write_jsonl(
        input_path,
        [
            {
                "source": "menu_grounded_seed",
                "intent_category": "order_item",
                "menu_item_name": "Ayran",
                "turkish_user_message": "Bir Ayran alabilir miyim?",
                "canonical_response_preview": "Ekledim: 1 x Ayran. Başka bir isteğiniz var mı?",
                "canonical_review_status": "approved_canonical_preview",
                "canonical_review_notes": "approved",
                "include_for_grounded_paraphrase_dataset": True,
            }
        ],
    )

    exit_code = main(["--input", str(input_path), "--output", str(output_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Menu-grounded grounded paraphrase candidate build complete." in captured.out
    assert "Candidate records written: 1" in captured.out
