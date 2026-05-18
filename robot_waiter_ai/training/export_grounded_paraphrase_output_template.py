from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


_BASE = Path(__file__).resolve().parents[1]
REFERENCE_PATH = _BASE / "evals" / "grounded_paraphrase_valid_reference.jsonl"
OUTPUT_PATH = _BASE / "evals" / "grounded_paraphrase_valid_output_template.jsonl"

BACKEND_PLACEHOLDER = "TODO_BACKEND_NAME"
SOURCE_REFERENCE = "grounded_paraphrase_valid_reference"
FILL_INSTRUCTIONS = (
    "generated_paraphrase alanını gelecekteki model çıktısı veya manuel deney sonucu ile doldurun."
)


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"JSONL file not found: {path}")

    records: List[Dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number} in {path}: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"Expected JSON object on line {line_number} in {path}.")
        records.append(record)
    return records


def export_output_template(
    reference_path: Path = REFERENCE_PATH,
    output_path: Path = OUTPUT_PATH,
) -> int:
    reference_records = _load_jsonl(reference_path)

    template_records: List[Dict[str, Any]] = []
    for idx, reference in enumerate(reference_records, start=1):
        record_id = reference.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError(f"Reference record {idx} is missing a valid id.")

        template_records.append(
            {
                "id": record_id,
                "generated_paraphrase": "",
                "backend_name": BACKEND_PLACEHOLDER,
                "metadata": {
                    "intent": reference["intent"],
                    "source_reference": SOURCE_REFERENCE,
                    "fill_instructions": FILL_INSTRUCTIONS,
                    "canonical_response": reference["canonical_response"],
                    "must_preserve_terms": reference["must_preserve_terms"],
                    "must_not_introduce": reference["must_not_introduce"],
                },
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in template_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(template_records)} records -> {output_path}")
    return len(template_records)


def main() -> None:
    count = export_output_template()
    print(f"Grounded paraphrase output template export complete. Total template records: {count}")


if __name__ == "__main__":
    main()
