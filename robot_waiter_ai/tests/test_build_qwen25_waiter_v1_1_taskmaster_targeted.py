from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from robot_waiter_ai.training.build_qwen25_waiter_v1_1_taskmaster_targeted import (
    DEFAULT_ALL_OUTPUT_PATH,
    DEFAULT_AUDIT_OUTPUT_PATH,
    DEFAULT_FOOD_ORDERING_PATH,
    DEFAULT_TEST_OUTPUT_PATH,
    DEFAULT_TRAIN_OUTPUT_PATH,
    DEFAULT_VALID_OUTPUT_PATH,
    SPLIT_SIZES,
    SYSTEM_PROMPT,
    TARGET_COUNTS,
    UNCERTAIN_ITEM_NAMES,
    build_targeted_dataset,
)


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _read_audit(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _assistant(row: dict) -> str:
    return row["messages"][2]["content"]


def _assert_valid_messages(row: dict) -> None:
    assert set(row) == {"messages"}
    messages = row["messages"]
    assert isinstance(messages, list)
    assert [message["role"] for message in messages] == ["system", "user", "assistant"]
    assert messages[0]["content"] == SYSTEM_PROMPT
    assert messages[1]["content"].strip()
    assert messages[2]["content"].strip()


def test_default_targeted_outputs_exist_and_match_required_counts():
    all_rows = _read_jsonl(DEFAULT_ALL_OUTPUT_PATH)
    train_rows = _read_jsonl(DEFAULT_TRAIN_OUTPUT_PATH)
    valid_rows = _read_jsonl(DEFAULT_VALID_OUTPUT_PATH)
    test_rows = _read_jsonl(DEFAULT_TEST_OUTPUT_PATH)
    audit_rows = _read_audit(DEFAULT_AUDIT_OUTPUT_PATH)

    assert len(all_rows) == 500
    assert len(train_rows) == 400
    assert len(valid_rows) == 50
    assert len(test_rows) == 50
    assert train_rows + valid_rows + test_rows == all_rows
    assert len(audit_rows) == 500

    for row in all_rows:
        _assert_valid_messages(row)

    assert Counter(row["category"] for row in audit_rows) == TARGET_COUNTS
    assert Counter(row["split"] for row in audit_rows) == SPLIT_SIZES
    assert {
        "category",
        "source_conversation_id",
        "source_turn_index",
        "user",
        "assistant",
    }.issubset(audit_rows[0])

    for index, audit_row in enumerate(audit_rows):
        assert audit_row["user"] == all_rows[index]["messages"][1]["content"]
        assert audit_row["assistant"] == all_rows[index]["messages"][2]["content"]
        assert audit_row["source_conversation_id"]
        assert audit_row["source_turn_index"] != ""


def test_assistant_responses_follow_safety_constraints():
    all_rows = _read_jsonl(DEFAULT_ALL_OUTPUT_PATH)
    banned_substrings = [
        "20 dakika",
        "kişisel bilgiler",
        "pickup",
        "takeout",
        "teslimat",
        "hazır olacak",
    ]
    price_pattern = re.compile(r"(₺|\$|\btl\b|\blira\b|\bdolar\b|\d+\s*(tl|lira))", re.I)
    allergy_guarantee_pattern = re.compile(
        r"(alerj\w*.*(güvenli|garanti|kesin)|"
        r"(güvenli|garanti|kesin).*alerj\w*)",
        re.I,
    )

    for row in all_rows:
        assistant = _assistant(row)
        lowered = assistant.lower()
        assert assistant.strip()
        assert all(banned not in lowered for banned in banned_substrings)
        assert price_pattern.search(assistant) is None
        assert allergy_guarantee_pattern.search(assistant) is None
        assert "seçenek seçenekleri" not in assistant.lower()


def test_clear_remove_confirm_close_and_recommendation_responses_are_targeted():
    audit_rows = _read_audit(DEFAULT_AUDIT_OUTPUT_PATH)

    clear_rows = [row for row in audit_rows if row["category"] == "clear_order_item"]
    assert clear_rows
    assert all("hangi" not in row["assistant"].lower() for row in clear_rows)
    assert all("kaç" not in row["assistant"].lower() for row in clear_rows)
    assert all("istediğinizi anladım" in row["assistant"] for row in clear_rows)

    remove_rows = [row for row in audit_rows if row["category"] == "remove_or_change_order"]
    assert remove_rows
    assert all(
        (
            "siparişten çıkarmak istediğinizi anladım" in row["assistant"]
            or "ile değiştirmek istediğinizi anladım" in row["assistant"]
        )
        for row in remove_rows
    )

    confirm_close_rows = [
        row for row in audit_rows if row["category"] == "confirm_or_close_order"
    ]
    assert confirm_close_rows
    valid_confirm_close_responses = {
        "Tamam. Siparişi onaylamak istediğinizi anladım.",
        "Tamam. Başka bir isteğiniz olmadığını anladım.",
    }
    assert {row["assistant"] for row in confirm_close_rows} == valid_confirm_close_responses

    polite_rows = [row for row in audit_rows if row["category"] == "polite_thanks_closing"]
    assert polite_rows
    assert all(
        row["assistant"] == "Rica ederim. Başka bir isteğiniz olmadığını anladım."
        for row in polite_rows
    )

    recommendation_rows = [
        row
        for row in audit_rows
        if "öner" in row["user"].lower() or "ne iyi gider" in row["user"].lower()
    ]
    assert recommendation_rows
    assert all("alerj" not in row["assistant"].lower() for row in recommendation_rows)
    assert all("güncel menü" in row["assistant"].lower() for row in recommendation_rows)


def test_uncertain_items_use_availability_safe_wording():
    audit_rows = _read_audit(DEFAULT_AUDIT_OUTPUT_PATH)
    categories_that_add_items = {
        "clear_order_item",
        "add_more_quantity",
        "side_drink_extra_request",
    }
    uncertain_rows = []
    for row in audit_rows:
        if row["category"] not in categories_that_add_items:
            continue
        user_lower = row["user"].lower()
        if any(
            re.search(rf"(?<!\w){re.escape(item_name)}(?!\w)", user_lower)
            for item_name in UNCERTAIN_ITEM_NAMES
        ):
            uncertain_rows.append(row)

    assert uncertain_rows
    assert all(
        "güncel menüde varsa" in row["assistant"].lower()
        for row in uncertain_rows
    )


@pytest.mark.skipif(
    not DEFAULT_FOOD_ORDERING_PATH.exists(),
    reason="Raw taskmaster food-ordering.json dataset not present in this local environment."
)
def test_builder_uses_food_ordering_source_only(tmp_path):
    all_output = tmp_path / "targeted_500.jsonl"
    train_output = tmp_path / "targeted_train.jsonl"
    valid_output = tmp_path / "targeted_valid.jsonl"
    test_output = tmp_path / "targeted_test.jsonl"
    audit_output = tmp_path / "targeted_audit.csv"

    summary = build_targeted_dataset(
        food_ordering_path=DEFAULT_FOOD_ORDERING_PATH,
        all_output_path=all_output,
        train_output_path=train_output,
        valid_output_path=valid_output,
        test_output_path=test_output,
        audit_output_path=audit_output,
    )

    assert Path(summary["food_ordering_path"]).name == "food-ordering.json"
    assert "restaurant-search" not in summary["food_ordering_path"]
    assert summary["records_written"] == 500
    assert summary["category_counts"] == TARGET_COUNTS
    assert len(_read_jsonl(all_output)) == 500
    assert len(_read_jsonl(train_output)) == 400
    assert len(_read_jsonl(valid_output)) == 50
    assert len(_read_jsonl(test_output)) == 50
    assert len(_read_audit(audit_output)) == 500
