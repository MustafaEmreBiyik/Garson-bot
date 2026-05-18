from pathlib import Path

from robot_waiter_ai.evals.eval_runner import run_evaluations
from robot_waiter_ai.inference import (
    DeterministicDialogueBackend,
    InferenceRequest,
    InferenceResponse,
)


BASE_DIR = Path(__file__).resolve().parents[1]
EVAL_PATH = BASE_DIR / "evals" / "evaluation_cases.yaml"


def _build_backend() -> DeterministicDialogueBackend:
    return DeterministicDialogueBackend(
        BASE_DIR / "data" / "menu.yaml",
        BASE_DIR / "data" / "restaurant_info.yaml",
    )


def test_deterministic_adapter_returns_inference_response():
    backend = _build_backend()
    response = backend.generate(InferenceRequest(user_message="Merhaba"))

    assert isinstance(response, InferenceResponse)


def test_deterministic_adapter_sets_backend_name():
    backend = _build_backend()
    response = backend.generate(InferenceRequest(user_message="Merhaba"))

    assert response.backend_name == "deterministic_baseline"


def test_deterministic_adapter_returns_non_empty_text():
    backend = _build_backend()
    response = backend.generate(InferenceRequest(user_message="Merhaba"))

    assert response.text.strip()


def test_eval_runner_can_use_deterministic_adapter():
    backend = _build_backend()
    report = run_evaluations(eval_path=EVAL_PATH, backend=backend)

    assert report.total_cases >= 1
    assert report.failed == 0
    assert report.invalid == 0
