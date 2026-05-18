from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import unicodedata
from typing import Any, Dict, List, Optional

import yaml

from robot_waiter_ai.app.config import default_config
from robot_waiter_ai.assistant.dialogue_manager import DialogueManager
from robot_waiter_ai.inference import (
    BaseInferenceBackend,
    DeterministicDialogueBackend,
    InferenceRequest,
)


@dataclass
class EvaluationCase:
    id: str
    user: str
    expected_intent: Optional[str] = None
    expected_contains: List[str] = field(default_factory=list)
    expected_not_contains: List[str] = field(default_factory=list)
    notes: Optional[str] = None


@dataclass
class CaseResult:
    case_id: str
    status: str
    reasons: List[str]
    response: str = ""
    expected_intent: Optional[str] = None
    actual_intent: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class EvaluationReport:
    total_cases: int
    passed: int
    failed: int
    invalid: int
    results: List[CaseResult]

    @property
    def pass_rate(self) -> float:
        if self.total_cases == 0:
            return 0.0
        return (self.passed / self.total_cases) * 100


def _default_eval_path() -> Path:
    return Path(__file__).resolve().parent / "evaluation_cases.yaml"


def load_evaluation_cases(eval_path: Path | str | None = None) -> List[Dict[str, Any]]:
    path = Path(eval_path) if eval_path else _default_eval_path()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cases = data.get("evaluation_cases")
    if not isinstance(cases, list):
        raise ValueError("evaluation_cases.yaml must define an 'evaluation_cases' list.")
    return cases


def _validate_string_list(value: Any, field_name: str) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"'{field_name}' must be a list of strings.")
    return value


def _parse_case(raw_case: Dict[str, Any]) -> EvaluationCase:
    if not isinstance(raw_case, dict):
        raise ValueError("Each evaluation case must be a mapping.")

    case_id = raw_case.get("id")
    user = raw_case.get("user")

    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("Missing or invalid 'id'.")
    if not isinstance(user, str) or not user.strip():
        raise ValueError("Missing or invalid 'user'.")

    expected_intent = raw_case.get("expected_intent")
    if expected_intent is not None and not isinstance(expected_intent, str):
        raise ValueError("'expected_intent' must be a string when present.")

    notes = raw_case.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise ValueError("'notes' must be a string when present.")

    return EvaluationCase(
        id=case_id,
        user=user,
        expected_intent=expected_intent,
        expected_contains=_validate_string_list(raw_case.get("expected_contains"), "expected_contains"),
        expected_not_contains=_validate_string_list(raw_case.get("expected_not_contains"), "expected_not_contains"),
        notes=notes,
    )


def _normalize_text(text: str) -> str:
    repaired = _repair_text(text)
    repaired = (
        repaired.replace("ı", "i")
        .replace("İ", "I")
        .replace("ş", "s")
        .replace("Ş", "S")
        .replace("ğ", "g")
        .replace("Ğ", "G")
        .replace("ç", "c")
        .replace("Ç", "C")
        .replace("ö", "o")
        .replace("Ö", "O")
        .replace("ü", "u")
        .replace("Ü", "U")
    )
    decomposed = unicodedata.normalize("NFKD", repaired.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _repair_text(text: str) -> str:
    try:
        return text.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def detect_intent(manager: DialogueManager, text: str) -> str:
    lower = _normalize_text(text.strip())
    if not lower:
        return "empty"
    if manager._is_greeting(lower):
        return "greeting"
    if manager._is_thanks(lower):
        return "thanks"
    if manager._is_ask_hours(lower):
        return "hours_question"
    if manager._is_ask_categories(lower):
        return "menu_question"
    if manager._is_recommendation(lower):
        return "recommendation"
    if manager._is_allergy(lower) or "glutensiz" in lower:
        return "allergen_question"
    if manager._is_confirm_order(lower):
        return "confirm_order"
    if manager._is_summary(lower):
        return "summarize_order"
    if manager._is_clear_order(lower):
        return "clear_order"
    if manager._is_remove_order(lower):
        return "remove_item"
    if manager._is_update_order(lower):
        return "update_item"
    if "glutensiz" in lower:
        return "allergen_question"
    if "menu" in lower and ("var" in lower or "neler" in lower):
        return "menu_question"
    if "var mi" in lower:
        return "menu_question"
    if "oner" in lower or "tavsiye" in lower:
        return "recommendation"
    if manager._is_add_order(lower):
        return "add_item"
    if _mentions_known_item(manager, lower):
        if "fiyat" in lower or "kac" in lower:
            return "price_question"
        return "menu_question"
    if manager._is_menu_question(lower):
        if "fiyat" in lower:
            return "price_question"
        return "menu_question"
    return "off_topic"


def _mentions_known_item(manager: DialogueManager, normalized_text: str) -> bool:
    for item in manager.menu.items:
        if _normalize_text(item.name) in normalized_text:
            return True
    return False


def evaluate_case(
    case: EvaluationCase,
    backend: BaseInferenceBackend,
    intent_probe: DialogueManager,
) -> CaseResult:
    actual_intent = detect_intent(intent_probe, case.user)
    response = backend.generate(InferenceRequest(user_message=case.user))
    reasons: List[str] = []
    normalized_response = _normalize_text(response.text)

    if case.expected_intent and actual_intent != case.expected_intent:
        reasons.append(
            f"Expected intent '{case.expected_intent}' but detected '{actual_intent}'."
        )

    for expected in case.expected_contains:
        if _normalize_text(expected) not in normalized_response:
            reasons.append(f"Missing expected text: {expected}")

    for forbidden in case.expected_not_contains:
        if _normalize_text(forbidden) in normalized_response:
            reasons.append(f"Found forbidden text: {forbidden}")

    status = "passed" if not reasons else "failed"
    return CaseResult(
        case_id=case.id,
        status=status,
        reasons=reasons,
        response=response.text,
        expected_intent=case.expected_intent,
        actual_intent=actual_intent,
        notes=case.notes,
    )


def run_evaluations(
    eval_path: Path | str | None = None,
    menu_path: Path | str | None = None,
    restaurant_info_path: Path | str | None = None,
    backend: BaseInferenceBackend | None = None,
) -> EvaluationReport:
    config = default_config()
    resolved_menu_path = Path(menu_path) if menu_path else config.menu_path
    resolved_restaurant_info_path = (
        Path(restaurant_info_path) if restaurant_info_path else config.restaurant_info_path
    )
    inference_backend = backend or DeterministicDialogueBackend(
        resolved_menu_path,
        resolved_restaurant_info_path,
    )
    intent_probe = DialogueManager(
        resolved_menu_path,
        resolved_restaurant_info_path,
    )

    results: List[CaseResult] = []
    raw_cases = load_evaluation_cases(eval_path)

    for index, raw_case in enumerate(raw_cases, start=1):
        try:
            case = _parse_case(raw_case)
        except ValueError as exc:
            case_id = raw_case.get("id") if isinstance(raw_case, dict) else f"case_{index}"
            results.append(
                CaseResult(
                    case_id=str(case_id),
                    status="invalid",
                    reasons=[str(exc)],
                    notes=raw_case.get("notes") if isinstance(raw_case, dict) else None,
                )
            )
            continue

        results.append(evaluate_case(case, inference_backend, intent_probe))

    passed = sum(1 for result in results if result.status == "passed")
    failed = sum(1 for result in results if result.status == "failed")
    invalid = sum(1 for result in results if result.status == "invalid")

    return EvaluationReport(
        total_cases=len(results),
        passed=passed,
        failed=failed,
        invalid=invalid,
        results=results,
    )


def format_report(report: EvaluationReport) -> str:
    lines = [
        "Robot Waiter AI Evaluation Report",
        "=" * 34,
        f"Total cases : {report.total_cases}",
        f"Passed      : {report.passed}",
        f"Failed      : {report.failed}",
        f"Invalid     : {report.invalid}",
        f"Pass rate   : {report.pass_rate:.2f}%",
    ]

    failures = [result for result in report.results if result.status in {"failed", "invalid"}]
    if failures:
        lines.append("")
        lines.append("Failed or Invalid Cases:")
        for result in failures:
            joined_reasons = "; ".join(result.reasons) if result.reasons else "Unknown failure."
            lines.append(f"- {result.case_id}: {joined_reasons}")
    else:
        lines.append("")
        lines.append("All evaluation cases passed.")

    return "\n".join(lines)


def main() -> int:
    report = run_evaluations()
    print(format_report(report))
    return 0 if report.failed == 0 and report.invalid == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
