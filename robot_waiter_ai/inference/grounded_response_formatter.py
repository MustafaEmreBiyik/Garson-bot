from __future__ import annotations

from typing import List, Optional

from .structured_result import GroundedResult, check_paraphrase_safety


def format_grounded_response(
    result: GroundedResult,
    paraphrase_candidate: str | None = None,
) -> str:
    if paraphrase_candidate is None:
        return result.canonical_response

    rejection_reasons = explain_paraphrase_rejection(result, paraphrase_candidate)
    if rejection_reasons:
        return result.canonical_response

    return paraphrase_candidate


def explain_paraphrase_rejection(
    result: GroundedResult,
    paraphrase_candidate: str | None,
) -> List[str]:
    if paraphrase_candidate is None:
        return []

    raw_reasons = check_paraphrase_safety(result, paraphrase_candidate)
    if not raw_reasons:
        return []

    simplified: List[str] = []
    for reason in raw_reasons:
        lowered = reason.casefold()
        if "forbidden term present" in lowered:
            if result.menu.unavailable_items:
                simplified.append("introduced unsupported item")
            elif result.safety.safety_type == "allergy":
                simplified.append("contains forbidden term")
            else:
                simplified.append("contains forbidden term")
            continue

        if "missing required term" in lowered:
            if result.action.intent == "price_question":
                simplified.append("missing price")
            elif result.action.intent == "allergen_question":
                simplified.append("missing allergy confirmation wording")
            else:
                simplified.append("missing required term")
            continue

        simplified.append(reason)

    ordered: List[str] = []
    for reason in simplified:
        if reason not in ordered:
            ordered.append(reason)
    return ordered
