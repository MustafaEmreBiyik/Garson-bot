from __future__ import annotations

import json
from pathlib import Path

import yaml

from robot_waiter_ai.evals.generated_output_adapter import (
    evaluate_generated_outputs,
    format_generated_output_report,
    load_generated_output_records,
    main,
)


def _write_jsonl(tmp_path: Path, records: list[dict]) -> Path:
    output_path = tmp_path / "outputs.jsonl"
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return output_path


def _write_eval_file(tmp_path: Path, cases: list[dict]) -> Path:
    eval_path = tmp_path / "evaluation_cases.yaml"
    payload = {"evaluation_cases": cases}
    eval_path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return eval_path


def test_loads_valid_generated_output_records(tmp_path):
    output_path = _write_jsonl(
        tmp_path,
        [{"case_id": "eval_001", "response": "Merhaba", "backend_name": "demo_backend"}],
    )

    records = load_generated_output_records(output_path)

    assert len(records) == 1
    assert records[0]["case_id"] == "eval_001"


def test_invalid_record_detection(tmp_path):
    eval_path = _write_eval_file(
        tmp_path,
        [{"id": "eval_001", "user": "Merhaba", "expected_contains": ["Merhaba"]}],
    )
    output_path = _write_jsonl(tmp_path, [{"case_id": "eval_001"}])

    report = evaluate_generated_outputs(output_path, eval_path=eval_path)

    assert report.invalid_output_records == 1


def test_missing_case_output_detection(tmp_path):
    eval_path = _write_eval_file(
        tmp_path,
        [{"id": "eval_001", "user": "Merhaba", "expected_contains": ["Merhaba"]}],
    )
    output_path = _write_jsonl(tmp_path, [])

    report = evaluate_generated_outputs(output_path, eval_path=eval_path)

    assert report.missing_outputs == 1
    assert report.results[0].status == "missing"


def test_expected_contains_scoring(tmp_path):
    eval_path = _write_eval_file(
        tmp_path,
        [{"id": "eval_001", "user": "Merhaba", "expected_contains": ["Hoş geldiniz"]}],
    )
    output_path = _write_jsonl(
        tmp_path,
        [{"case_id": "eval_001", "response": "Merhaba, hoş geldiniz."}],
    )

    report = evaluate_generated_outputs(output_path, eval_path=eval_path)

    assert report.passed == 1
    assert report.failed == 0


def test_expected_not_contains_scoring(tmp_path):
    eval_path = _write_eval_file(
        tmp_path,
        [{"id": "eval_001", "user": "Pizza var mı?", "expected_not_contains": ["Pizza: "]}],
    )
    output_path = _write_jsonl(
        tmp_path,
        [{"case_id": "eval_001", "response": "Pizza: 99 TL"}],
    )

    report = evaluate_generated_outputs(output_path, eval_path=eval_path)

    assert report.failed == 1
    assert "Found forbidden text: Pizza: " in report.results[0].reasons


def test_cli_report_function_returns_structured_result(tmp_path):
    eval_path = _write_eval_file(
        tmp_path,
        [{"id": "eval_001", "user": "Merhaba", "expected_contains": ["Merhaba"]}],
    )
    output_path = _write_jsonl(
        tmp_path,
        [{"case_id": "eval_001", "response": "Merhaba, hoş geldiniz."}],
    )

    report = evaluate_generated_outputs(output_path, eval_path=eval_path)
    rendered = format_generated_output_report(report)
    exit_code = main(["--outputs", str(output_path), "--eval-path", str(eval_path)])

    assert report.total_cases == 1
    assert "Generated Output Evaluation Report" in rendered
    assert exit_code == 0
