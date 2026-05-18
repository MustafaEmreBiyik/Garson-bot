from __future__ import annotations

import json
from pathlib import Path

import yaml

from robot_waiter_ai.assistant.menu_knowledge import normalize_text
from robot_waiter_ai.inference.structured_result import SUPPORTED_GROUNDED_INTENTS
from robot_waiter_ai.training.grounded_paraphrase_builder import SYSTEM_PROMPT
from robot_waiter_ai.training.grounded_paraphrase_validator import REQUIRED_FIELDS


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_PATH = BASE_DIR / "datasets" / "raw" / "grounded_paraphrase_seed.yaml"
TRAIN_PATH = BASE_DIR / "datasets" / "processed" / "grounded_paraphrase_train.jsonl"
VALID_PATH = BASE_DIR / "datasets" / "processed" / "grounded_paraphrase_valid.jsonl"


def _load_seed_examples() -> list[dict]:
    data = yaml.safe_load(RAW_PATH.read_text(encoding="utf-8")) or {}
    return data.get("examples", [])


def _load_jsonl_records(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_raw_seed_examples_match_required_field_contract():
    examples = _load_seed_examples()
    assert examples, "Grounded paraphrase seed examples should not be empty."

    for ex in examples:
        assert REQUIRED_FIELDS.issubset(ex.keys()), ex["id"]
        assert ex["canonical_response"].strip(), ex["id"]
        assert ex["safe_paraphrase"].strip(), ex["id"]
        assert isinstance(ex["must_preserve_terms"], list), ex["id"]
        assert isinstance(ex["must_not_introduce"], list), ex["id"]


def test_raw_seed_ids_are_unique_and_intents_allowed():
    examples = _load_seed_examples()
    ids = [ex["id"] for ex in examples]
    assert len(ids) == len(set(ids))

    intents = {ex["intent"] for ex in examples}
    assert intents.issubset(SUPPORTED_GROUNDED_INTENTS)


def test_raw_seed_paraphrases_preserve_and_avoid_terms():
    examples = _load_seed_examples()
    for ex in examples:
        paraphrase = ex["safe_paraphrase"]
        for term in ex["must_preserve_terms"]:
            assert term in paraphrase, f"{ex['id']} missing preserve term: {term}"
        for term in ex["must_not_introduce"]:
            assert term not in paraphrase, f"{ex['id']} contains forbidden term: {term}"


def test_built_grounded_jsonl_files_exist():
    assert TRAIN_PATH.exists()
    assert VALID_PATH.exists()


def test_built_grounded_jsonl_records_follow_message_contract():
    seed_examples = {ex["id"]: ex for ex in _load_seed_examples()}
    records = _load_jsonl_records(TRAIN_PATH) + _load_jsonl_records(VALID_PATH)
    assert records, "Grounded paraphrase JSONL records should not be empty."

    for rec in records:
        assert "messages" in rec
        assert "metadata" in rec
        messages = rec["messages"]
        assert len(messages) == 3
        assert [msg["role"] for msg in messages] == ["system", "user", "assistant"]

        system_message = messages[0]["content"]
        user_message = messages[1]["content"]
        assistant_message = messages[2]["content"]
        metadata = rec["metadata"]

        assert system_message == SYSTEM_PROMPT
        assert "Kullanıcı mesajı:" in user_message
        assert "Canonical cevap:" in user_message
        assert "Korunacak terimler:" in user_message
        assert "Eklenmemesi gereken terimler:" in user_message

        ex = seed_examples[metadata["id"]]
        assert ex["user_message"] in user_message
        assert ex["canonical_response"] in user_message
        for term in ex["must_preserve_terms"]:
            assert term in user_message

        if ex["must_not_introduce"]:
            for term in ex["must_not_introduce"]:
                assert term in user_message
        else:
            assert "Eklenmemesi gereken terimler: -" in user_message

        assert assistant_message == ex["safe_paraphrase"]
        assert metadata["intent"] == ex["intent"]
        assert metadata["notes"] == ex["notes"]


def test_sample_intent_coverage_exists_in_raw_seed():
    examples = _load_seed_examples()
    counts = {}
    for ex in examples:
        counts[ex["intent"]] = counts.get(ex["intent"], 0) + 1

    for intent in [
        "greeting",
        "price_question",
        "allergen_question",
        "unavailable_item",
        "off_topic",
        "confirm_order",
    ]:
        assert counts.get(intent, 0) >= 1, intent


def test_critical_safety_patterns_exist_in_raw_seed():
    examples = _load_seed_examples()

    allergy_examples = [ex for ex in examples if ex["intent"] == "allergen_question"]
    assert allergy_examples
    for ex in allergy_examples:
        assert normalize_text("Alerji") in normalize_text(ex["safe_paraphrase"])
        assert normalize_text("teyit") in normalize_text(ex["safe_paraphrase"])

    price_examples = [ex for ex in examples if ex["intent"] == "price_question"]
    assert price_examples
    for ex in price_examples:
        assert normalize_text("TL") in normalize_text(ex["safe_paraphrase"])

    unavailable_examples = [ex for ex in examples if ex["intent"] == "unavailable_item"]
    assert unavailable_examples
    for ex in unavailable_examples:
        assert normalize_text("bulunmuyor") in normalize_text(ex["safe_paraphrase"])

    off_topic_examples = [ex for ex in examples if ex["intent"] == "off_topic"]
    assert off_topic_examples
    for ex in off_topic_examples:
        assert ex["must_preserve_terms"], ex["id"]
        for term in ex["must_preserve_terms"]:
            assert normalize_text(term) in normalize_text(ex["safe_paraphrase"]), ex["id"]

    confirm_examples = [ex for ex in examples if ex["intent"] == "confirm_order"]
    assert confirm_examples
    for ex in confirm_examples:
        assert normalize_text("MVP/demo") in normalize_text(ex["safe_paraphrase"])
