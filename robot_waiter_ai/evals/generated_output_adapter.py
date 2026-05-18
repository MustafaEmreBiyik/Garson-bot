from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from robot_waiter_ai.evals.eval_runner import (
    _normalize_text,
    _parse_case,
    load_evaluation_cases,
)


@dataclass
class GeneratedOutputRecord:
    case_id: str
    response: str
    backend_name: str = "generated_output"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InvalidGeneratedOutputRecord:
    line_number: int
    reasons: List[str]
    raw_record: Any


@dataclass
class GeneratedOutputCaseResult:
    case_id: str
    status: str
    reasons: List[str]
    response: str = ""
    backend_name: str = ""
    notes: str | None = None


@dataclass
class GeneratedOutputEvaluationReport:
    total_cases: int
    matched_outputs: int
    missing_outputs: int
    passed: int
    failed: int
    invalid_output_records: int
    results: List[GeneratedOutputCaseResult]
    invalid_records: List[InvalidGeneratedOutputRecord]

    @property
    def pass_rate(self) -> float:
        if self.total_cases == 0:
            return 0.0
        return (self.passed / self.total_cases) * 100


def load_generated_output_records(outputs_path: Path | str) -> List[Dict[str, Any]]:
    path = Path(outputs_path)
    if not path.exists():
        raise FileNotFoundError(f"Generated outputs file not found: {path}")

    records: List[Dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
        records.append(record)
    return records


def _parse_generated_output_record(raw_record: Any, line_number: int) -> GeneratedOutputRecord:
    if not isinstance(raw_record, dict):
        raise ValueError("Each generated output record must be a JSON object.")

    case_id = raw_record.get("case_id")
    response = raw_record.get("response")
    backend_name = raw_record.get("backend_name", "generated_output")
    metadata = raw_record.get("metadata", {})

    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("Missing or invalid 'case_id'.")
    if not isinstance(response, str) or not response.strip():
        raise ValueError("Missing or invalid 'response'.")
    if not isinstance(backend_name, str) or not backend_name.strip():
        raise ValueError("Missing or invalid 'backend_name'.")
    if not isinstance(metadata, dict):
        raise ValueError("'metadata' must be a JSON object when present.")

    return GeneratedOutputRecord(
        case_id=case_id,
        response=response,
        backend_name=backend_name,
        metadata=metadata,
    )


def _collect_generated_output_records(
    outputs_path: Path | str,
) -> tuple[Dict[str, GeneratedOutputRecord], List[InvalidGeneratedOutputRecord]]:
    raw_records = load_generated_output_records(outputs_path)
    valid_records: Dict[str, GeneratedOutputRecord] = {}
    invalid_records: List[InvalidGeneratedOutputRecord] = []

    for line_number, raw_record in enumerate(raw_records, start=1):
        try:
            record = _parse_generated_output_record(raw_record, line_number)
            if record.case_id in valid_records:
                raise ValueError(f"Duplicate generated output for case_id '{record.case_id}'.")
        except ValueError as exc:
            invalid_records.append(
                InvalidGeneratedOutputRecord(
                    line_number=line_number,
                    reasons=[str(exc)],
                    raw_record=raw_record,
                )
            )
            continue

        valid_records[record.case_id] = record

    return valid_records, invalid_records


def _score_generated_response(case: Any, record: GeneratedOutputRecord) -> GeneratedOutputCaseResult:
    normalized_response = _normalize_text(record.response)
    reasons: List[str] = []

    for expected in case.expected_contains:
        if _normalize_text(expected) not in normalized_response:
            reasons.append(f"Missing expected text: {expected}")

    for forbidden in case.expected_not_contains:
        if _normalize_text(forbidden) in normalized_response:
            reasons.append(f"Found forbidden text: {forbidden}")

    status = "passed" if not reasons else "failed"
    return GeneratedOutputCaseResult(
        case_id=case.id,
        status=status,
        reasons=reasons,
        response=record.response,
        backend_name=record.backend_name,
        notes=case.notes,
    )


def evaluate_generated_outputs(
    outputs_path: Path | str,
    eval_path: Path | str | None = None,
) -> GeneratedOutputEvaluationReport:
    valid_records, invalid_records = _collect_generated_output_records(outputs_path)
    raw_cases = load_evaluation_cases(eval_path)

    results: List[GeneratedOutputCaseResult] = []
    matched_outputs = 0
    missing_outputs = 0

    for raw_case in raw_cases:
        case = _parse_case(raw_case)
        record = valid_records.get(case.id)
        if record is None:
            missing_outputs += 1
            results.append(
                GeneratedOutputCaseResult(
                    case_id=case.id,
                    status="missing",
                    reasons=["Missing generated output for evaluation case."],
                    notes=case.notes,
                )
            )
            continue

        matched_outputs += 1
        results.append(_score_generated_response(case, record))

    passed = sum(1 for result in results if result.status == "passed")
    failed = sum(1 for result in results if result.status == "failed")

    return GeneratedOutputEvaluationReport(
        total_cases=len(results),
        matched_outputs=matched_outputs,
        missing_outputs=missing_outputs,
        passed=passed,
        failed=failed,
        invalid_output_records=len(invalid_records),
        results=results,
        invalid_records=invalid_records,
    )


def format_generated_output_report(report: GeneratedOutputEvaluationReport) -> str:
    lines = [
        "Generated Output Evaluation Report",
        "=" * 34,
        f"Total cases           : {report.total_cases}",
        f"Matched outputs       : {report.matched_outputs}",
        f"Missing outputs       : {report.missing_outputs}",
        f"Passed                : {report.passed}",
        f"Failed                : {report.failed}",
        f"Invalid output records: {report.invalid_output_records}",
        f"Pass rate             : {report.pass_rate:.2f}%",
    ]

    problem_results = [result for result in report.results if result.status in {"failed", "missing"}]
    if problem_results:
        lines.append("")
        lines.append("Failed or Missing Cases:")
        for result in problem_results:
            joined_reasons = "; ".join(result.reasons) if result.reasons else "Unknown issue."
            lines.append(f"- {result.case_id}: {joined_reasons}")

    if report.invalid_records:
        lines.append("")
        lines.append("Invalid Output Records:")
        for invalid_record in report.invalid_records:
            joined_reasons = "; ".join(invalid_record.reasons)
            lines.append(f"- line {invalid_record.line_number}: {joined_reasons}")

    if not problem_results and not report.invalid_records:
        lines.append("")
        lines.append("All matched generated outputs passed.")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate generated model outputs saved in JSONL format."
    )
    parser.add_argument(
        "--outputs",
        required=True,
        help="Path to the generated-output JSONL file.",
    )
    parser.add_argument(
        "--eval-path",
        default=None,
        help="Optional path to evaluation_cases.yaml.",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = evaluate_generated_outputs(args.outputs, eval_path=args.eval_path)
    print(format_generated_output_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
