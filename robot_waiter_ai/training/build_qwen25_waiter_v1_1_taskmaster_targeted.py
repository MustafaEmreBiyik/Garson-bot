"""
Build a targeted Turkish v1.1 waiter SFT dataset from Taskmaster food-ordering.

The builder reads only Taskmaster's food-ordering.json. Source USER turns are
used as pattern/source-id inspiration; assistant responses are newly authored
according to the safe Turkish waiter policy.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

_BASE = Path(__file__).resolve().parents[1]
TASKMASTER_DIR = _BASE / "datasets" / "external" / "taskmaster" / "TM-2-2020"
DEFAULT_FOOD_ORDERING_PATH = TASKMASTER_DIR / "food-ordering.json"
INTERMEDIATE_DIR = _BASE / "datasets" / "intermediate"

DEFAULT_ALL_OUTPUT_PATH = (
    INTERMEDIATE_DIR / "qwen25_waiter_v1_1_taskmaster_targeted_500.jsonl"
)
DEFAULT_TRAIN_OUTPUT_PATH = (
    INTERMEDIATE_DIR / "qwen25_waiter_v1_1_taskmaster_targeted_train_400.jsonl"
)
DEFAULT_VALID_OUTPUT_PATH = (
    INTERMEDIATE_DIR / "qwen25_waiter_v1_1_taskmaster_targeted_valid_50.jsonl"
)
DEFAULT_TEST_OUTPUT_PATH = (
    INTERMEDIATE_DIR / "qwen25_waiter_v1_1_taskmaster_targeted_test_50.jsonl"
)
DEFAULT_AUDIT_OUTPUT_PATH = (
    INTERMEDIATE_DIR / "qwen25_waiter_v1_1_taskmaster_targeted_audit.csv"
)

SYSTEM_PROMPT = (
    "Sen Türkçe konuşan kibar bir restoran garson asistanısın. "
    "Müşteriyle doğal, kısa ve net konuş. Menü, fiyat, stok, kampanya, "
    "teslimat veya alerjen bilgisi uydurma. Kesin bilgi gerekiyorsa güncel "
    "menüye, personele veya mutfağa yönlendir. Restoran dışı konularda sohbeti "
    "nazikçe menü veya sipariş konusuna geri getir."
)

TARGET_COUNTS = {
    "clear_order_item": 120,
    "add_more_quantity": 80,
    "order_clarification": 70,
    "remove_or_change_order": 70,
    "confirm_or_close_order": 80,
    "side_drink_extra_request": 50,
    "polite_thanks_closing": 30,
}

SPLIT_SIZES = {
    "train": 400,
    "valid": 50,
    "test": 50,
}

SHUFFLE_SEED = 20260516

FORBIDDEN_SOURCE_KEYWORDS = {
    "pickup",
    "pick up",
    "delivery",
    "deliver",
    "takeout",
    "take out",
    "to go",
    "address",
    "phone",
    "credit card",
    "on file",
    "restaurant name",
    "restaurant",
    "location",
    "price",
    "cost",
    "dollar",
    "dollars",
    "$",
}

UNHELPFUL_SOURCE_FOODS = {
    "pizza",
    "burger",
    "hamburger",
    "burrito",
    "hot dog",
    "sandwich",
    "sandwiches",
    "blt",
    "taco",
    "tacos",
    "sushi",
    "ribs",
    "barbecue",
    "bbq",
    "gyro",
    "gyros",
}

FORBIDDEN_SOURCE_ANNOTATIONS = {
    "food_order.name.restaurant",
    "food_order.location.restaurant",
    "food_order.time.pickup",
    "food_order.price_range",
    "food_order.rating.restaurant",
}

ITEMS = [
    {"name": "ayran", "cap": "Ayran", "acc": "Ayranı", "kind": "drink"},
    {"name": "limonata", "cap": "Limonata", "acc": "Limonatayı", "kind": "drink"},
    {"name": "su", "cap": "Su", "acc": "Suyu", "kind": "drink"},
    {"name": "çay", "cap": "Çay", "acc": "Çayı", "kind": "drink"},
    {"name": "kahve", "cap": "Kahve", "acc": "Kahveyi", "kind": "drink"},
    {"name": "soda", "cap": "Soda", "acc": "Sodayı", "kind": "drink"},
    {"name": "mercimek çorbası", "cap": "Mercimek çorbası", "acc": "Mercimek çorbasını", "kind": "food"},
    {"name": "ezogelin çorbası", "cap": "Ezogelin çorbası", "acc": "Ezogelin çorbasını", "kind": "food"},
    {"name": "salata", "cap": "Salata", "acc": "Salatayı", "kind": "side"},
    {"name": "pilav", "cap": "Pilav", "acc": "Pilavı", "kind": "side"},
    {"name": "makarna", "cap": "Makarna", "acc": "Makarnayı", "kind": "food"},
    {"name": "tavuk şiş", "cap": "Tavuk şiş", "acc": "Tavuk şişi", "kind": "food"},
    {"name": "köfte", "cap": "Köfte", "acc": "Köfteyi", "kind": "food"},
    {"name": "kebap", "cap": "Kebap", "acc": "Kebabı", "kind": "food"},
    {"name": "patates kızartması", "cap": "Patates kızartması", "acc": "Patates kızartmasını", "kind": "side"},
    {"name": "baklava", "cap": "Baklava", "acc": "Baklavayı", "kind": "dessert"},
    {"name": "sütlaç", "cap": "Sütlaç", "acc": "Sütlacı", "kind": "dessert"},
    {"name": "künefe", "cap": "Künefe", "acc": "Künefeyi", "kind": "dessert"},
]

DRINKS = [item for item in ITEMS if item["kind"] == "drink"]
SIDES = [item for item in ITEMS if item["kind"] == "side"]
DESSERTS = [item for item in ITEMS if item["kind"] == "dessert"]
FOODS = [item for item in ITEMS if item["kind"] == "food"]
DEMO_SAFE_ITEM_NAMES = {
    "ayran",
    "limonata",
    "mercimek çorbası",
    "sütlaç",
}
UNCERTAIN_ITEM_NAMES = {
    item["name"]
    for item in ITEMS
    if item["name"] not in DEMO_SAFE_ITEM_NAMES
}

QUANTITIES = [
    {"number": 1, "word": "bir", "word_cap": "Bir"},
    {"number": 2, "word": "iki", "word_cap": "İki"},
    {"number": 3, "word": "üç", "word_cap": "Üç"},
    {"number": 4, "word": "dört", "word_cap": "Dört"},
]


@dataclass(frozen=True)
class SourceTurn:
    conversation_id: str
    turn_index: Any
    text: str
    annotations: tuple[str, ...]


@dataclass(frozen=True)
class TargetExample:
    category: str
    user: str
    assistant: str
    source_conversation_id: str
    source_turn_index: Any


def _normalize_text(text: str) -> str:
    normalized = text.lower().replace("\xa0", " ")
    normalized = re.sub(r"[^a-z0-9ğüşöçıİĞÜŞÖÇ$'\s-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _is_user_speaker(turn: Dict[str, Any]) -> bool:
    speaker = str(turn.get("speaker") or turn.get("role") or "").strip().upper()
    return speaker.startswith("USER") or speaker.startswith("CUSTOMER")


def _extract_annotations(turn: Dict[str, Any]) -> tuple[str, ...]:
    annotations: list[str] = []
    for segment in turn.get("segments") or []:
        if not isinstance(segment, dict):
            continue
        for annotation in segment.get("annotations") or []:
            if isinstance(annotation, dict) and isinstance(annotation.get("name"), str):
                annotations.append(annotation["name"])
    return tuple(annotations)


def _is_forbidden_source(text: str, annotations: Sequence[str]) -> bool:
    normalized = _normalize_text(text)
    if len(normalized) > 180:
        return True
    if not normalized or not any(char.isalnum() for char in normalized):
        return True
    if any(keyword in normalized for keyword in FORBIDDEN_SOURCE_KEYWORDS):
        return True
    if any(food in normalized for food in UNHELPFUL_SOURCE_FOODS):
        return True
    return any(annotation in FORBIDDEN_SOURCE_ANNOTATIONS for annotation in annotations)


def _load_source_turns(food_ordering_path: Path) -> list[SourceTurn]:
    data = json.loads(food_ordering_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {food_ordering_path}")

    source_turns: list[SourceTurn] = []
    for conversation_idx, conversation in enumerate(data):
        if not isinstance(conversation, dict):
            continue
        conversation_id = (
            conversation.get("conversation_id")
            or conversation.get("id")
            or conversation.get("dialogue_id")
            or f"food_ordering_{conversation_idx}"
        )
        utterances = conversation.get("utterances")
        if not isinstance(utterances, list):
            continue

        for turn_idx, turn in enumerate(utterances):
            if not isinstance(turn, dict) or not _is_user_speaker(turn):
                continue
            text = turn.get("text") or turn.get("utterance") or turn.get("content")
            if not isinstance(text, str):
                continue
            text = text.strip()
            annotations = _extract_annotations(turn)
            if _is_forbidden_source(text, annotations):
                continue
            source_turns.append(
                SourceTurn(
                    conversation_id=str(conversation_id),
                    turn_index=turn.get("index", turn_idx),
                    text=text,
                    annotations=annotations,
                )
            )
    if not source_turns:
        raise ValueError(f"No usable USER source turns found in {food_ordering_path}")
    return source_turns


def _has_item_annotation(turn: SourceTurn) -> bool:
    return "food_order.name.item" in turn.annotations


def _matches(pattern: str, text: str) -> bool:
    return re.search(pattern, text) is not None


def _build_source_buckets(source_turns: Sequence[SourceTurn]) -> dict[str, list[SourceTurn]]:
    buckets: dict[str, list[SourceTurn]] = defaultdict(list)
    for turn in source_turns:
        text = _normalize_text(turn.text)

        if _has_item_annotation(turn) and _matches(
            r"\b(i'?d like|i would like|i want|i need|can i get|let me have|order|get)\b",
            text,
        ):
            buckets["clear_order_item"].append(turn)

        if _matches(r"\b(add|also|too|another|extra|more|couple|side)\b", text):
            buckets["add_more_quantity"].append(turn)

        if _matches(r"\b(without|no|hold|instead|change|remove|cancel|don'?t want)\b", text):
            buckets["remove_or_change_order"].append(turn)

        if _matches(
            r"\b(what kind|options|recommend|suggest|do you have|menu|what are my|what can i)\b",
            text,
        ):
            buckets["order_clarification"].append(turn)

        if _matches(
            r"\b(yes|correct|confirm|that'?s it|that is it|all right|nothing else|no thanks|no thank you)\b",
            text,
        ):
            buckets["confirm_or_close_order"].append(turn)

        if _matches(r"\b(thank|thanks|all right|that'?s it|that is it|nothing else)\b", text):
            buckets["polite_thanks_closing"].append(turn)

        if _matches(
            r"\b(drink|soda|coke|tea|water|lemonade|fries|salad|side|sauce|dessert|extra)\b",
            text,
        ):
            buckets["side_drink_extra_request"].append(turn)

    buckets["all"] = list(source_turns)
    return dict(buckets)


def _source_for(
    category: str,
    buckets: dict[str, list[SourceTurn]],
    index: int,
) -> SourceTurn:
    bucket = buckets.get(category) or buckets["all"]
    return bucket[index % len(bucket)]


def _with_source(
    *,
    category: str,
    user: str,
    assistant: str,
    source: SourceTurn,
) -> TargetExample:
    return TargetExample(
        category=category,
        user=user,
        assistant=assistant,
        source_conversation_id=source.conversation_id,
        source_turn_index=source.turn_index,
    )


def _format_ack(quantity: int, item_name: str) -> str:
    if item_name in UNCERTAIN_ITEM_NAMES:
        return (
            f"{quantity} adet {item_name} istediğinizi anladım. "
            "Güncel menüde varsa siparişe eklenebilir. Başka bir isteğiniz var mı?"
        )
    return (
        f"Tabii. {quantity} adet {item_name} istediğinizi anladım. "
        "Başka bir isteğiniz var mı?"
    )


def _format_add_more_ack(quantity: int, item_name: str) -> str:
    if item_name in UNCERTAIN_ITEM_NAMES:
        return (
            f"{quantity} adet {item_name} daha istediğinizi anladım. "
            "Güncel menüde varsa siparişe eklenebilir. Başka bir isteğiniz var mı?"
        )
    return (
        f"Tabii. {quantity} adet {item_name} daha eklemek istediğinizi anladım. "
        "Başka bir isteğiniz var mı?"
    )


def _format_extra_ack(requested: str, item_name: str) -> str:
    if item_name in UNCERTAIN_ITEM_NAMES:
        return (
            f"{requested} istediğinizi anladım. Güncel menüde varsa siparişe "
            "eklenebilir. Başka bir isteğiniz var mı?"
        )
    return f"Tabii. {requested} istediğinizi anladım. Başka bir isteğiniz var mı?"


def _build_clear_order_examples(
    count: int,
    buckets: dict[str, list[SourceTurn]],
) -> list[TargetExample]:
    patterns = [
        "{qty_num} {item} istiyorum.",
        "{qty_word_cap} {item} alabilir miyim?",
        "{qty_word_cap} tane {item} rica ederim.",
        "Bana {qty_num} {item} verir misiniz?",
        "{qty_word_cap} adet {item} olsun.",
        "{qty_num} {item} alayım.",
        "Lütfen {qty_word} {item} istiyorum.",
        "{qty_word_cap} {item} sipariş etmek istiyorum.",
    ]
    examples: list[TargetExample] = []
    seen: set[str] = set()
    cursor = 0
    for pattern in patterns:
        for quantity in QUANTITIES:
            for item in ITEMS:
                user = pattern.format(
                    qty_num=quantity["number"],
                    qty_word=quantity["word"],
                    qty_word_cap=quantity["word_cap"],
                    item=item["name"],
                )
                if user in seen:
                    continue
                seen.add(user)
                source = _source_for("clear_order_item", buckets, cursor)
                examples.append(
                    _with_source(
                        category="clear_order_item",
                        user=user,
                        assistant=_format_ack(quantity["number"], item["name"]),
                        source=source,
                    )
                )
                cursor += 1
                if len(examples) == count:
                    return examples
    raise ValueError("Not enough clear_order_item templates to satisfy target count")


def _build_add_more_examples(
    count: int,
    buckets: dict[str, list[SourceTurn]],
) -> list[TargetExample]:
    patterns = [
        "{qty_num} {item} daha.",
        "{qty_word_cap} {item} daha alabilir miyim?",
        "Bir de {qty_num} {item} ekleyelim.",
        "{qty_word_cap} tane {item} daha istiyorum.",
        "Siparişe {qty_num} {item} daha ekler misiniz?",
        "{qty_word_cap} adet {item} daha olsun.",
    ]
    examples: list[TargetExample] = []
    seen: set[str] = set()
    cursor = 0
    for pattern in patterns:
        for quantity in QUANTITIES:
            for item in ITEMS:
                user = pattern.format(
                    qty_num=quantity["number"],
                    qty_word_cap=quantity["word_cap"],
                    item=item["name"],
                )
                if user in seen:
                    continue
                seen.add(user)
                source = _source_for("add_more_quantity", buckets, cursor)
                assistant = _format_add_more_ack(quantity["number"], item["name"])
                examples.append(
                    _with_source(
                        category="add_more_quantity",
                        user=user,
                        assistant=assistant,
                        source=source,
                    )
                )
                cursor += 1
                if len(examples) == count:
                    return examples
    raise ValueError("Not enough add_more_quantity templates to satisfy target count")


def _build_order_clarification_examples(
    count: int,
    buckets: dict[str, list[SourceTurn]],
) -> list[TargetExample]:
    generic_pairs = [
        (
            "Bir içecek alayım.",
            "Hangi içeceği istediğinizi belirtir misiniz? Güncel seçenekler için menüye bakabiliriz.",
        ),
        (
            "Bana bir tatlı verir misin?",
            "Hangi tatlıyı istediğinizi söyleyebilir misiniz? Güncel tatlı seçenekleri için menüye bakmak en doğrusu olur.",
        ),
        (
            "Yanına bir şey ekleyelim.",
            "Ne eklemek istediğinizi belirtir misiniz? Güncel yan ürün seçenekleri için menüye bakabiliriz.",
        ),
        (
            "Bir çorba olsun.",
            "Hangi çorbayı istediğinizi söyleyebilir misiniz? Güncel menüye bakmak en doğrusu olur.",
        ),
        (
            "Bir ana yemek alacağım.",
            "Hangi ana yemeği istediğinizi belirtir misiniz? Güncel menüden birlikte netleştirebiliriz.",
        ),
        (
            "Menüde hafif ne var?",
            "Güncel menüye bakmak en doğrusu olur. Hafif bir ana yemek mi, salata gibi bir seçenek mi istersiniz?",
        ),
        (
            "Tatlı olarak ne önerirsin?",
            "Tatlı tercihiniz için güncel menüye bakmak en doğrusu olur. Hafif mi daha yoğun bir tatlı mı istersiniz?",
        ),
        (
            "İçecek olarak ne önerirsiniz?",
            "İçecek tercihiniz için güncel menüye bakmak en doğrusu olur. Soğuk mu sıcak mı bir içecek istersiniz?",
        ),
        (
            "Yemeğin yanına ne iyi gider?",
            "Yan ürün tercihi için güncel menüye bakmak en doğrusu olur. Hafif mi daha doyurucu bir seçenek mi istersiniz?",
        ),
        (
            "Sos seçenekleri neler?",
            "Sos seçenekleri için güncel menüye veya personele bakmak en doğrusu olur. Siparişinize sos eklemek ister misiniz?",
        ),
    ]
    category_words = [
        "içecek",
        "tatlı",
        "yan ürün",
        "çorba",
        "salata",
        "ana yemek",
        "sos",
        "soğuk içecek",
        "sıcak içecek",
        "hafif bir seçenek",
    ]
    patterns = [
        "Bir {category} istiyorum.",
        "{category_cap} alabilir miyim?",
        "{category_cap} için seçenek söyler misiniz?",
        "{category_cap} olarak ne önerirsiniz?",
        "Siparişe bir {category} eklemek istiyorum.",
        "Yanına {category} olsun.",
    ]

    examples: list[TargetExample] = []
    cursor = 0
    for user, assistant in generic_pairs:
        source = _source_for("order_clarification", buckets, cursor)
        examples.append(
            _with_source(
                category="order_clarification",
                user=user,
                assistant=assistant,
                source=source,
            )
        )
        cursor += 1
        if len(examples) == count:
            return examples

    for pattern in patterns:
        for category_word in category_words:
            category_cap = category_word[0].upper() + category_word[1:]
            user = pattern.format(category=category_word, category_cap=category_cap)
            if "öner" in user:
                assistant = (
                    f"{category_cap} tercihiniz için güncel menüye bakmak en doğrusu olur. "
                    "Nasıl bir seçenek istediğinizi biraz açar mısınız?"
                )
            elif "seçenek" in user:
                if category_word == "hafif bir seçenek":
                    assistant = (
                        "Hafif seçenekler için güncel menüye bakmak en doğrusu olur. "
                        "Aklınızda belirli bir tercih var mı?"
                    )
                else:
                    assistant = (
                        f"{category_cap} seçenekleri için güncel menüye bakmak en doğrusu olur. "
                        "Aklınızda belirli bir tercih var mı?"
                    )
            else:
                assistant = (
                    f"Hangi {category_word} istediğinizi belirtir misiniz? "
                    "Güncel menüye bakarak netleştirebiliriz."
                )
            source = _source_for("order_clarification", buckets, cursor)
            examples.append(
                _with_source(
                    category="order_clarification",
                    user=user,
                    assistant=assistant,
                    source=source,
                )
            )
            cursor += 1
            if len(examples) == count:
                return examples
    raise ValueError("Not enough order_clarification templates to satisfy target count")


def _build_remove_or_change_examples(
    count: int,
    buckets: dict[str, list[SourceTurn]],
) -> list[TargetExample]:
    remove_patterns = [
        "{acc_lower} çıkarır mısın?",
        "{acc_lower} siparişten çıkarabilir misiniz?",
        "{acc_lower} istemiyorum, çıkaralım.",
        "Lütfen {acc_lower} iptal edelim.",
        "{acc_lower} listeden çıkaralım.",
    ]
    change_patterns = [
        "{old_acc_lower} {new_name} ile değiştirir misiniz?",
        "{old_name} yerine {new_name} alabilir miyim?",
        "Siparişte {old_name} yerine {new_name} olsun.",
    ]
    examples: list[TargetExample] = []
    seen: set[str] = set()
    cursor = 0

    for pattern in remove_patterns:
        for item in ITEMS:
            user = pattern.format(acc_lower=item["acc"].lower())
            if user in seen:
                continue
            seen.add(user)
            assistant = (
                f"Tabii. {item['acc']} siparişten çıkarmak istediğinizi anladım. "
                "Başka bir değişiklik var mı?"
            )
            source = _source_for("remove_or_change_order", buckets, cursor)
            examples.append(
                _with_source(
                    category="remove_or_change_order",
                    user=user,
                    assistant=assistant,
                    source=source,
                )
            )
            cursor += 1
            if len(examples) == count:
                return examples

    for pattern in change_patterns:
        for index, old_item in enumerate(ITEMS):
            new_item = ITEMS[(index + 5) % len(ITEMS)]
            user = pattern.format(
                old_acc_lower=old_item["acc"].lower(),
                old_name=old_item["name"],
                new_name=new_item["name"],
            )
            if user in seen:
                continue
            seen.add(user)
            assistant = (
                f"Tabii. {old_item['acc']} {new_item['name']} ile değiştirmek "
                "istediğinizi anladım. Başka bir değişiklik var mı?"
            )
            source = _source_for("remove_or_change_order", buckets, cursor)
            examples.append(
                _with_source(
                    category="remove_or_change_order",
                    user=user,
                    assistant=assistant,
                    source=source,
                )
            )
            cursor += 1
            if len(examples) == count:
                return examples
    raise ValueError("Not enough remove_or_change_order templates to satisfy target count")


def _build_confirm_or_close_examples(
    count: int,
    buckets: dict[str, list[SourceTurn]],
) -> list[TargetExample]:
    confirm_users = [
        "Siparişi onaylıyorum.",
        "Tamam, siparişi onaylıyorum.",
        "Onaylıyorum.",
        "Evet, onaylıyorum.",
        "Sipariş doğru, onaylayalım.",
        "Bu şekilde onaylıyorum.",
        "Tamamdır, sipariş onay.",
        "Evet, siparişim bu.",
        "Siparişimi bu şekilde onaylıyorum.",
        "Her şey doğru, onaylıyorum.",
        "Tamam, böyle olsun.",
        "Evet, bu siparişi onaylıyorum.",
        "Siparişi kesinleştirebiliriz.",
        "Böyle onaylayalım.",
        "Tamam, sipariş tamam.",
        "Evet, doğru.",
        "Doğru, onaylıyorum.",
        "Siparişim doğru.",
        "Bu sipariş tamam.",
        "Aynen, onaylıyorum.",
        "Evet, bu şekilde.",
        "Tamam, doğru anladınız.",
        "Siparişi bu haliyle onaylıyorum.",
        "Evet, sipariş böyle kalsın.",
        "Onaylayabilirsiniz.",
        "Tamam, onaylayabilirsiniz.",
        "Evet, siparişi geçelim.",
        "Bunları onaylıyorum.",
        "Siparişim net, onaylıyorum.",
        "Bu hali uygun, onaylıyorum.",
        "Tamamdır, onay veriyorum.",
        "Sipariş bu, onaylıyorum.",
        "Evet, başka değişiklik yok, onaylıyorum.",
        "Bu listeyi onaylıyorum.",
        "Evet, sipariş doğru görünüyor.",
        "Tamam, sipariş bu olsun.",
        "Böylece onaylıyorum.",
        "Tamam, onayım var.",
        "Evet, bu sipariş benim.",
        "Siparişi bu şekilde kabul ediyorum.",
    ]
    close_users = [
        "Bu kadar.",
        "Şimdilik bu kadar.",
        "Başka bir şey istemiyorum.",
        "Benden bu kadar.",
        "Hepsi bu.",
        "Başka yok.",
        "Bu sipariş yeterli.",
        "Eklemek istediğim başka bir şey yok.",
        "Şu an başka isteğim yok.",
        "Tamam, bu kadar olsun.",
        "Başka bir şey almayacağım.",
        "Siparişim bu kadar.",
        "Yeterli, başka istemiyorum.",
        "Başka ürün eklemeyelim.",
        "Bu kadar yeter.",
        "Tamamdır, başka yok.",
        "Ekstra bir şey istemiyorum.",
        "Böyle kalsın.",
        "Daha fazla istemiyorum.",
        "Son olarak bu kadar.",
        "Başka talebim yok.",
        "Bu siparişle bitirelim.",
        "Şimdilik başka yok.",
        "Benim için bu kadar.",
        "Siparişi böyle bırakalım.",
        "Başka ekleme yapmayalım.",
        "Evet, bu kadar yeter.",
        "Bu kadar alacağım.",
        "Tamam, devamı yok.",
        "Başka sipariş vermeyeceğim.",
        "Ek olarak bir şey yok.",
        "Bu kadarı tamam.",
        "Sipariş burada bitsin.",
        "Daha başka yok.",
        "Bunlar dışında istemiyorum.",
        "Bu kadar olsun lütfen.",
        "Başka bir isteğim kalmadı.",
        "Şimdilik sipariş bu.",
        "Tamam, kapatalım.",
        "Liste bu kadar.",
    ]

    examples: list[TargetExample] = []
    cursor = 0
    for user in confirm_users:
        source = _source_for("confirm_or_close_order", buckets, cursor)
        examples.append(
            _with_source(
                category="confirm_or_close_order",
                user=user,
                assistant="Tamam. Siparişi onaylamak istediğinizi anladım.",
                source=source,
            )
        )
        cursor += 1
        if len(examples) == count:
            return examples
    for user in close_users:
        source = _source_for("confirm_or_close_order", buckets, cursor)
        examples.append(
            _with_source(
                category="confirm_or_close_order",
                user=user,
                assistant="Tamam. Başka bir isteğiniz olmadığını anladım.",
                source=source,
            )
        )
        cursor += 1
        if len(examples) == count:
            return examples
    raise ValueError("Not enough confirm_or_close_order templates to satisfy target count")


def _build_side_drink_extra_examples(
    count: int,
    buckets: dict[str, list[SourceTurn]],
) -> list[TargetExample]:
    examples: list[TargetExample] = []
    cursor = 0
    request_specs: list[tuple[str, str, str]] = []

    for quantity in QUANTITIES[:3]:
        for drink in DRINKS:
            request_specs.append(
                (
                    f"Yemeğin yanına {quantity['number']} {drink['name']} alabilir miyim?",
                    f"{quantity['number']} adet {drink['name']}",
                    drink["name"],
                )
            )
            request_specs.append(
                (
                    f"Bir de {quantity['number']} {drink['name']} olsun.",
                    f"{quantity['number']} adet {drink['name']}",
                    drink["name"],
                )
            )
    for side in SIDES:
        request_specs.extend(
            [
                (f"Yanına {side['name']} ekleyebilir miyiz?", side["name"], side["name"]),
                (f"Bir de {side['name']} alabilir miyim?", side["name"], side["name"]),
                (f"{side['cap']} yanında olsun.", side["name"], side["name"]),
            ]
        )
    for dessert in DESSERTS:
        request_specs.extend(
            [
                (f"Son olarak {dessert['name']} ekleyelim.", dessert["name"], dessert["name"]),
                (f"Tatlı olarak {dessert['name']} alabilir miyim?", dessert["name"], dessert["name"]),
            ]
        )
    for food in FOODS[:4]:
        request_specs.extend(
            [
                (
                    f"{food['cap']} yanında ekstra sos istiyorum.",
                    f"{food['name']} yanında ekstra sos",
                    food["name"],
                ),
                (
                    f"{food['cap']} için ekstra ekmek alabilir miyim?",
                    f"{food['name']} için ekstra ekmek",
                    food["name"],
                ),
            ]
        )

    seen: set[str] = set()
    for user, requested, item_name in request_specs:
        if user in seen:
            continue
        seen.add(user)
        source = _source_for("side_drink_extra_request", buckets, cursor)
        assistant = _format_extra_ack(requested, item_name)
        examples.append(
            _with_source(
                category="side_drink_extra_request",
                user=user,
                assistant=assistant,
                source=source,
            )
        )
        cursor += 1
        if len(examples) == count:
            return examples
    raise ValueError("Not enough side_drink_extra_request templates to satisfy target count")


def _build_polite_thanks_closing_examples(
    count: int,
    buckets: dict[str, list[SourceTurn]],
) -> list[TargetExample]:
    users = [
        "Teşekkür ederim, bu kadar.",
        "Sağ olun, başka bir şey yok.",
        "Teşekkürler, siparişim bu kadar.",
        "Çok teşekkürler, başka istemiyorum.",
        "Tamamdır, teşekkür ederim.",
        "Teşekkürler, hepsi bu.",
        "Sağ olun, bu kadar yeter.",
        "Teşekkür ederim, başka talebim yok.",
        "Teşekkürler, şimdilik bu kadar.",
        "Sağ olun, sipariş bu.",
        "Tamam, teşekkürler.",
        "Çok sağ olun, başka yok.",
        "Teşekkür ederim, ekleme yapmayacağım.",
        "Teşekkürler, bu şekilde kalsın.",
        "Sağ olun, başka sipariş vermeyeceğim.",
        "Teşekkürler, liste bu kadar.",
        "Çok teşekkür ederim, hepsi bu.",
        "Sağ olun, benim için bu kadar.",
        "Teşekkürler, başka bir isteğim kalmadı.",
        "Tamamdır, sağ olun.",
        "Teşekkür ederim, siparişi böyle bırakalım.",
        "Teşekkürler, devamı yok.",
        "Sağ olun, yeterli.",
        "Teşekkür ederim, son olarak bu kadar.",
        "Teşekkürler, başka ürün eklemeyelim.",
        "Sağ olun, şimdilik başka yok.",
        "Tamam, sağ olun.",
        "Teşekkür ederim, sipariş tamam.",
        "Çok sağ olun, bu kadar olsun.",
        "Teşekkürler, kapatabiliriz.",
    ]
    examples: list[TargetExample] = []
    for cursor, user in enumerate(users[:count]):
        source = _source_for("polite_thanks_closing", buckets, cursor)
        examples.append(
            _with_source(
                category="polite_thanks_closing",
                user=user,
                assistant="Rica ederim. Başka bir isteğiniz olmadığını anladım.",
                source=source,
            )
        )
    if len(examples) != count:
        raise ValueError("Not enough polite_thanks_closing templates to satisfy target count")
    return examples


def _build_target_examples(buckets: dict[str, list[SourceTurn]]) -> list[TargetExample]:
    examples = [
        *_build_clear_order_examples(TARGET_COUNTS["clear_order_item"], buckets),
        *_build_add_more_examples(TARGET_COUNTS["add_more_quantity"], buckets),
        *_build_order_clarification_examples(TARGET_COUNTS["order_clarification"], buckets),
        *_build_remove_or_change_examples(TARGET_COUNTS["remove_or_change_order"], buckets),
        *_build_confirm_or_close_examples(TARGET_COUNTS["confirm_or_close_order"], buckets),
        *_build_side_drink_extra_examples(TARGET_COUNTS["side_drink_extra_request"], buckets),
        *_build_polite_thanks_closing_examples(TARGET_COUNTS["polite_thanks_closing"], buckets),
    ]
    random.Random(SHUFFLE_SEED).shuffle(examples)
    return examples


def _to_chat_record(example: TargetExample) -> dict[str, list[dict[str, str]]]:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": example.user},
            {"role": "assistant", "content": example.assistant},
        ]
    }


def _write_jsonl(records: Sequence[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _split_name(index: int) -> str:
    if index < SPLIT_SIZES["train"]:
        return "train"
    if index < SPLIT_SIZES["train"] + SPLIT_SIZES["valid"]:
        return "valid"
    return "test"


def _write_audit(examples: Sequence[TargetExample], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "row_index",
        "split",
        "category",
        "source_conversation_id",
        "source_turn_index",
        "user",
        "assistant",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for index, example in enumerate(examples):
            writer.writerow(
                {
                    "row_index": index,
                    "split": _split_name(index),
                    "category": example.category,
                    "source_conversation_id": example.source_conversation_id,
                    "source_turn_index": example.source_turn_index,
                    "user": example.user,
                    "assistant": example.assistant,
                }
            )


def build_targeted_dataset(
    *,
    food_ordering_path: Path = DEFAULT_FOOD_ORDERING_PATH,
    all_output_path: Path = DEFAULT_ALL_OUTPUT_PATH,
    train_output_path: Path = DEFAULT_TRAIN_OUTPUT_PATH,
    valid_output_path: Path = DEFAULT_VALID_OUTPUT_PATH,
    test_output_path: Path = DEFAULT_TEST_OUTPUT_PATH,
    audit_output_path: Path = DEFAULT_AUDIT_OUTPUT_PATH,
) -> dict[str, Any]:
    source_turns = _load_source_turns(food_ordering_path)
    buckets = _build_source_buckets(source_turns)
    examples = _build_target_examples(buckets)

    expected_total = sum(TARGET_COUNTS.values())
    if len(examples) != expected_total:
        raise ValueError(f"Expected {expected_total} examples, generated {len(examples)}")

    records = [_to_chat_record(example) for example in examples]
    train_end = SPLIT_SIZES["train"]
    valid_end = train_end + SPLIT_SIZES["valid"]

    _write_jsonl(records, all_output_path)
    _write_jsonl(records[:train_end], train_output_path)
    _write_jsonl(records[train_end:valid_end], valid_output_path)
    _write_jsonl(records[valid_end:], test_output_path)
    _write_audit(examples, audit_output_path)

    return {
        "food_ordering_path": str(food_ordering_path),
        "source_turns_read": len(source_turns),
        "bucket_counts": {category: len(turns) for category, turns in buckets.items()},
        "records_written": len(records),
        "category_counts": dict(Counter(example.category for example in examples)),
        "all_output_path": str(all_output_path),
        "train_output_path": str(train_output_path),
        "valid_output_path": str(valid_output_path),
        "test_output_path": str(test_output_path),
        "audit_output_path": str(audit_output_path),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a targeted Turkish Qwen2.5 waiter v1.1 dataset from food-ordering.json only."
    )
    parser.add_argument(
        "--food-ordering",
        type=Path,
        default=DEFAULT_FOOD_ORDERING_PATH,
        help=f"Taskmaster food-ordering.json path (default: {DEFAULT_FOOD_ORDERING_PATH})",
    )
    parser.add_argument("--all-output", type=Path, default=DEFAULT_ALL_OUTPUT_PATH)
    parser.add_argument("--train-output", type=Path, default=DEFAULT_TRAIN_OUTPUT_PATH)
    parser.add_argument("--valid-output", type=Path, default=DEFAULT_VALID_OUTPUT_PATH)
    parser.add_argument("--test-output", type=Path, default=DEFAULT_TEST_OUTPUT_PATH)
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT_OUTPUT_PATH)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not Path(args.food_ordering).exists():
        print("Targeted Taskmaster build failed. Missing food-ordering input:", file=sys.stderr)
        print(f"- {Path(args.food_ordering)}", file=sys.stderr)
        return 1

    try:
        summary = build_targeted_dataset(
            food_ordering_path=Path(args.food_ordering),
            all_output_path=Path(args.all_output),
            train_output_path=Path(args.train_output),
            valid_output_path=Path(args.valid_output),
            test_output_path=Path(args.test_output),
            audit_output_path=Path(args.audit_output),
        )
    except Exception as exc:
        print(f"Targeted Taskmaster build failed: {exc}", file=sys.stderr)
        return 1

    print("Qwen2.5 waiter v1.1 targeted Taskmaster build complete.")
    print(f"Input food-ordering path: {summary['food_ordering_path']}")
    print(f"Source USER turns read: {summary['source_turns_read']}")
    print(f"Records written: {summary['records_written']}")
    print(f"Category counts: {summary['category_counts']}")
    print(f"All output path: {summary['all_output_path']}")
    print(f"Train output path: {summary['train_output_path']}")
    print(f"Valid output path: {summary['valid_output_path']}")
    print(f"Test output path: {summary['test_output_path']}")
    print(f"Audit output path: {summary['audit_output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
