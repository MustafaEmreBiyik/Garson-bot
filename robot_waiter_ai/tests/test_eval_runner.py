from __future__ import annotations

from pathlib import Path

import yaml

from robot_waiter_ai.evals.eval_runner import load_evaluation_cases, run_evaluations
from robot_waiter_ai.inference import DeterministicDialogueBackend


BASE_DIR = Path(__file__).resolve().parents[1]
EVAL_PATH = BASE_DIR / "evals" / "evaluation_cases.yaml"


def _write_eval_file(tmp_path: Path, cases: list[dict]) -> Path:
    eval_path = tmp_path / "evaluation_cases.yaml"
    payload = {"evaluation_cases": cases}
    eval_path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return eval_path


def test_eval_runner_loads_cases():
    cases = load_evaluation_cases(EVAL_PATH)
    assert len(cases) >= 1
    assert cases[0]["id"] == "eval_001"


def test_eval_runner_returns_report(tmp_path):
    eval_path = _write_eval_file(
        tmp_path,
        [
            {
                "id": "eval_ok",
                "user": "Merhaba",
                "expected_intent": "greeting",
                "expected_contains": ["Merhaba"],
                "expected_not_contains": [],
            }
        ],
    )

    report = run_evaluations(eval_path=eval_path)

    assert report.total_cases == 1
    assert report.passed == 1
    assert report.failed == 0
    assert report.invalid == 0


def test_eval_runner_detects_expected_contains(tmp_path):
    eval_path = _write_eval_file(
        tmp_path,
        [
            {
                "id": "eval_missing_text",
                "user": "Merhaba",
                "expected_contains": ["Bulunmayan ifade"],
            }
        ],
    )

    report = run_evaluations(eval_path=eval_path)

    assert report.failed == 1
    assert "Missing expected text: Bulunmayan ifade" in report.results[0].reasons


def test_eval_runner_detects_expected_not_contains(tmp_path):
    eval_path = _write_eval_file(
        tmp_path,
        [
            {
                "id": "eval_forbidden_text",
                "user": "Merhaba",
                "expected_not_contains": ["Merhaba"],
            }
        ],
    )

    report = run_evaluations(eval_path=eval_path)

    assert report.failed == 1
    assert "Found forbidden text: Merhaba" in report.results[0].reasons


def test_eval_runner_handles_invalid_case(tmp_path):
    eval_path = _write_eval_file(
        tmp_path,
        [
            {
                "id": "eval_invalid",
                "expected_contains": ["Merhaba"],
            }
        ],
    )

    report = run_evaluations(eval_path=eval_path)

    assert report.total_cases == 1
    assert report.invalid == 1
    assert report.results[0].status == "invalid"
    assert "Missing or invalid 'user'." in report.results[0].reasons


def test_eval_runner_passes_turkish_character_case(tmp_path):
    eval_path = _write_eval_file(
        tmp_path,
        [
            {
                "id": "eval_turkish_case",
                "user": "Ne önerirsiniz?",
                "expected_intent": "recommendation",
                "expected_contains": ["öneri"],
                "expected_not_contains": [],
            }
        ],
    )

    report = run_evaluations(eval_path=eval_path)

    assert report.passed == 1


def test_eval_runner_detects_confirm_order_intent(tmp_path):
    eval_path = _write_eval_file(
        tmp_path,
        [
            {
                "id": "eval_add_item",
                "user": "2 Ayran istiyorum",
                "expected_intent": "add_item",
                "expected_contains": ["Ayran"],
                "expected_not_contains": [],
            },
            {
                "id": "eval_confirm_order",
                "user": "Evet, onaylıyorum",
                "expected_intent": "confirm_order",
                "expected_contains": ["MVP/demo", "Toplam"],
                "expected_not_contains": [],
            },
        ],
    )

    report = run_evaluations(eval_path=eval_path)

    assert report.failed == 0


def test_eval_runner_uses_backend_abstraction(tmp_path):
    eval_path = _write_eval_file(
        tmp_path,
        [
            {
                "id": "eval_backend_ok",
                "user": "Merhaba",
                "expected_intent": "greeting",
                "expected_contains": ["Merhaba"],
                "expected_not_contains": [],
            }
        ],
    )
    base_dir = Path(__file__).resolve().parents[1]
    backend = DeterministicDialogueBackend(
        base_dir / "data" / "menu.yaml",
        base_dir / "data" / "restaurant_info.yaml",
    )

    report = run_evaluations(eval_path=eval_path, backend=backend)

    assert report.passed == 1
