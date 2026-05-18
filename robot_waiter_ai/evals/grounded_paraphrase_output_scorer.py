from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml

from robot_waiter_ai.training.grounded_paraphrase_validator import normalize_text


DEFAULT_REFERENCE_PATH = (
    Path(__file__).resolve().parents[1] / "datasets" / "raw" / "grounded_paraphrase_seed.yaml"
)


@dataclass
class GroundedParaphraseReference:
    id: str
    intent: str
    canonical_response: str
    must_preserve_terms: List[str]
    must_not_introduce: List[str]
    notes: str


@dataclass
class GroundedParaphraseOutputRecord:
    id: str
    generated_paraphrase: str
    backend_name: str = "grounded_paraphrase_output"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InvalidGroundedParaphraseOutputRecord:
    line_number: int
    reasons: List[str]
    raw_record: Any


@dataclass
class GroundedParaphraseCaseResult:
    id: str
    status: str
    reasons: List[str]
    intent: str = ""
    generated_paraphrase: str = ""
    backend_name: str = ""
    notes: str = ""


@dataclass
class GroundedParaphraseEvaluationReport:
    total_reference_examples: int
    matched_outputs: int
    missing_outputs: int
    passed: int
    failed: int
    invalid_output_records: int
    results: List[GroundedParaphraseCaseResult]
    invalid_records: List[InvalidGroundedParaphraseOutputRecord]

    @property
    def pass_rate(self) -> float:
        if self.total_reference_examples == 0:
            return 0.0
        return (self.passed / self.total_reference_examples) * 100


def load_grounded_paraphrase_references(reference_path: Path | str = DEFAULT_REFERENCE_PATH) -> List[dict]:
    path = Path(reference_path)
    if not path.exists():
        raise FileNotFoundError(f"Grounded paraphrase reference file not found: {path}")

    if path.suffix.lower() == ".jsonl":
        return load_grounded_paraphrase_output_records(path)

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    examples = payload.get("examples", [])
    if not isinstance(examples, list):
        raise ValueError("Expected 'examples' to be a list in grounded paraphrase seed YAML.")
    return examples


def load_grounded_paraphrase_output_records(outputs_path: Path | str) -> List[Dict[str, Any]]:
    path = Path(outputs_path)
    if not path.exists():
        raise FileNotFoundError(f"Grounded paraphrase outputs file not found: {path}")

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


def _parse_reference(raw_reference: Any) -> GroundedParaphraseReference:
    if not isinstance(raw_reference, dict):
        raise ValueError("Each grounded paraphrase reference must be a mapping.")

    return GroundedParaphraseReference(
        id=str(raw_reference["id"]),
        intent=str(raw_reference["intent"]),
        canonical_response=str(raw_reference["canonical_response"]),
        must_preserve_terms=list(raw_reference.get("must_preserve_terms", [])),
        must_not_introduce=list(raw_reference.get("must_not_introduce", [])),
        notes=str(raw_reference.get("notes", "")),
    )


def _parse_output_record(raw_record: Any, line_number: int) -> GroundedParaphraseOutputRecord:
    if not isinstance(raw_record, dict):
        raise ValueError("Each grounded paraphrase output record must be a JSON object.")

    record_id = raw_record.get("id")
    generated_paraphrase = raw_record.get("generated_paraphrase")
    backend_name = raw_record.get("backend_name", "grounded_paraphrase_output")
    metadata = raw_record.get("metadata", {})

    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError("Missing or invalid 'id'.")
    if not isinstance(generated_paraphrase, str):
        raise ValueError("Missing or invalid 'generated_paraphrase'.")
    if not isinstance(backend_name, str) or not backend_name.strip():
        raise ValueError("Missing or invalid 'backend_name'.")
    if not isinstance(metadata, dict):
        raise ValueError("'metadata' must be a JSON object when present.")

    return GroundedParaphraseOutputRecord(
        id=record_id,
        generated_paraphrase=generated_paraphrase,
        backend_name=backend_name,
        metadata=metadata,
    )


def _collect_output_records(
    outputs_path: Path | str,
) -> tuple[Dict[str, GroundedParaphraseOutputRecord], List[InvalidGroundedParaphraseOutputRecord]]:
    raw_records = load_grounded_paraphrase_output_records(outputs_path)
    valid_records: Dict[str, GroundedParaphraseOutputRecord] = {}
    invalid_records: List[InvalidGroundedParaphraseOutputRecord] = []

    for line_number, raw_record in enumerate(raw_records, start=1):
        try:
            record = _parse_output_record(raw_record, line_number)
            if record.id in valid_records:
                raise ValueError(f"Duplicate grounded paraphrase output for id '{record.id}'.")
        except ValueError as exc:
            invalid_records.append(
                InvalidGroundedParaphraseOutputRecord(
                    line_number=line_number,
                    reasons=[str(exc)],
                    raw_record=raw_record,
                )
            )
            continue

        valid_records[record.id] = record

    return valid_records, invalid_records


def _score_output(
    reference: GroundedParaphraseReference,
    record: GroundedParaphraseOutputRecord,
) -> GroundedParaphraseCaseResult:
    generated = record.generated_paraphrase.strip()
    normalized_generated = normalize_text(generated)
    reasons: List[str] = []

    if not generated:
        reasons.append("Generated paraphrase is empty.")

    for term in reference.must_preserve_terms:
        if normalize_text(term) not in normalized_generated:
            reasons.append(f"Missing preserve term: {term}")

    for forbidden in reference.must_not_introduce:
        if normalize_text(forbidden) in normalized_generated:
            reasons.append(f"Contains forbidden term: {forbidden}")

    status = "passed" if not reasons else "failed"
    return GroundedParaphraseCaseResult(
        id=reference.id,
        status=status,
        reasons=reasons,
        intent=reference.intent,
        generated_paraphrase=record.generated_paraphrase,
        backend_name=record.backend_name,
        notes=reference.notes,
    )


def score_grounded_paraphrase_outputs(
    outputs_path: Path | str,
    reference_path: Path | str = DEFAULT_REFERENCE_PATH,
) -> GroundedParaphraseEvaluationReport:
    valid_records, invalid_records = _collect_output_records(outputs_path)
    raw_references = load_grounded_paraphrase_references(reference_path)
    references = [_parse_reference(raw_reference) for raw_reference in raw_references]

    results: List[GroundedParaphraseCaseResult] = []
    matched_outputs = 0
    missing_outputs = 0

    for reference in references:
        record = valid_records.get(reference.id)
        if record is None:
            missing_outputs += 1
            results.append(
                GroundedParaphraseCaseResult(
                    id=reference.id,
                    status="missing",
                    reasons=["Missing generated paraphrase output for reference example."],
                    intent=reference.intent,
                    notes=reference.notes,
                )
            )
            continue

        matched_outputs += 1
        results.append(_score_output(reference, record))

    passed = sum(1 for result in results if result.status == "passed")
    failed = sum(1 for result in results if result.status == "failed")

    return GroundedParaphraseEvaluationReport(
        total_reference_examples=len(references),
        matched_outputs=matched_outputs,
        missing_outputs=missing_outputs,
        passed=passed,
        failed=failed,
        invalid_output_records=len(invalid_records),
        results=results,
        invalid_records=invalid_records,
    )


def format_grounded_paraphrase_report(report: GroundedParaphraseEvaluationReport) -> str:
    lines = [
        "Grounded Paraphrase Output Evaluation Report",
        "=" * 43,
        f"Total reference examples : {report.total_reference_examples}",
        f"Matched outputs          : {report.matched_outputs}",
        f"Missing outputs          : {report.missing_outputs}",
        f"Passed                   : {report.passed}",
        f"Failed                   : {report.failed}",
        f"Invalid output records   : {report.invalid_output_records}",
        f"Pass rate                : {report.pass_rate:.2f}%",
    ]

    problem_results = [result for result in report.results if result.status in {"failed", "missing"}]
    if problem_results:
        lines.append("")
        lines.append("Failed or Missing IDs:")
        for result in problem_results:
            joined_reasons = "; ".join(result.reasons) if result.reasons else "Unknown issue."
            lines.append(f"- {result.id}: {joined_reasons}")

    if report.invalid_records:
        lines.append("")
        lines.append("Invalid Output Records:")
        for invalid_record in report.invalid_records:
            joined_reasons = "; ".join(invalid_record.reasons)
            lines.append(f"- line {invalid_record.line_number}: {joined_reasons}")

    if not problem_results and not report.invalid_records:
        lines.append("")
        lines.append("All matched grounded paraphrase outputs passed.")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate saved grounded paraphrase outputs against preserve and forbidden-term constraints."
    )
    parser.add_argument(
        "--outputs",
        required=True,
        help="Path to the grounded paraphrase output JSONL file.",
    )
    parser.add_argument(
        "--reference",
        default=str(DEFAULT_REFERENCE_PATH),
        help="Optional path to grounded paraphrase reference data (.yaml or .jsonl).",
    )
    parser.add_argument(
        "--reference-path",
        dest="reference",
        help="Deprecated alias for --reference.",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = score_grounded_paraphrase_outputs(
        outputs_path=args.outputs,
        reference_path=args.reference,
    )
    print(format_grounded_paraphrase_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
