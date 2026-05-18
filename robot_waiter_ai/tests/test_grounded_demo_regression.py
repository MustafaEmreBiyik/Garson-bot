from __future__ import annotations

from pathlib import Path

import yaml

from robot_waiter_ai.inference.grounded_demo import run_grounded_demo


BASE_DIR = Path(__file__).resolve().parents[1]
REGRESSION_PATH = BASE_DIR / "inference" / "grounded_demo_regression_cases.yaml"


def _load_cases():
    data = yaml.safe_load(REGRESSION_PATH.read_text(encoding="utf-8"))
    return data["cases"]


def test_regression_fixture_file_exists():
    assert REGRESSION_PATH.exists()


def test_grounded_demo_regression_cases():
    cases = _load_cases()
    assert cases, "Regression cases should not be empty."

    for case in cases:
        payload = run_grounded_demo(
            case["user"],
            paraphrase_candidate=case.get("paraphrase"),
        )

        assert payload["detected_intent"] == case["expected_intent"], case["id"]

        if "expected_used_paraphrase" in case:
            assert payload["used_paraphrase"] is case["expected_used_paraphrase"], case["id"]

        for expected_text in case.get("expected_final_contains", []):
            assert expected_text in payload["final_response"], case["id"]

        for expected_reason in case.get("expected_rejection_contains", []):
            assert expected_reason in payload["rejection_reasons"], case["id"]
