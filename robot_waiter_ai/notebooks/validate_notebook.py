from __future__ import annotations

import json
import sys
from pathlib import Path


NOTEBOOK_HEADING_PROFILES = {
    "colab_qwen3_0_6b_lora_smoke_test.ipynb": [
        "## A. Title And Warning",
        "## B. Runtime Check",
        "## C. Project Setup",
        "## D. Install Dependencies",
        "## E. Dataset Path Configuration",
        "## F. Model Configuration",
        "## G. Tokenization / Formatting",
        "## H. LoRA/QLoRA Configuration",
        "## I. Training Cell",
        "## J. Simple Post-Training Generation",
        "## K. Download / Export Section",
    ],
    "colab_hey_garson_wakeword_training.ipynb": [
        "## A. Title And Warning",
        "## B. Runtime Check",
        "## C. Project Setup",
        "## D. Install Dependencies",
        "## E. Wake Word Configuration",
        "## F. Generate Positive Samples",
        "## G. Download Negative Data",
        "## H. Verify Training Data",
        "## I. Training Cell",
        "## J. Evaluate & Test",
        "## K. Export & Download",
    ],
    "colab_grounded_paraphraser_qwen3_0_6b_smoke_test.ipynb": [
        "## A. Title And Warning",
        "## B. Runtime Check",
        "## C. Project Setup",
        "## D. Dependency Install",
        "## E. Dataset Path Configuration",
        "## F. Model Configuration",
        "## G. Formatting Function",
        "## H. LoRA/QLoRA Config",
        "## I. Training Cell",
        "## J. Held-Out Validation Generation",
        "## K. Export / Download Section",
    ],
}

DEFAULT_REQUIRED_HEADINGS = NOTEBOOK_HEADING_PROFILES["colab_qwen3_0_6b_lora_smoke_test.ipynb"]


def load_notebook(path: Path | str) -> dict:
    notebook_path = Path(path)
    return json.loads(notebook_path.read_text(encoding="utf-8"))


def collect_markdown_text(notebook: dict) -> str:
    parts: list[str] = []
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") != "markdown":
            continue
        source = cell.get("source", [])
        if isinstance(source, list):
            parts.append("".join(source))
        elif isinstance(source, str):
            parts.append(source)
    return "\n".join(parts)


def get_required_headings(path: Path | str) -> list[str]:
    notebook_path = Path(path)
    return NOTEBOOK_HEADING_PROFILES.get(notebook_path.name, DEFAULT_REQUIRED_HEADINGS)


def validate_notebook(path: Path | str) -> tuple[bool, list[str]]:
    notebook_path = Path(path)
    notebook = load_notebook(path)

    if notebook.get("nbformat") != 4:
        return False, ["Notebook nbformat must be 4."]

    cells = notebook.get("cells")
    if not isinstance(cells, list) or not cells:
        return False, ["Notebook must contain at least one cell."]

    markdown_text = collect_markdown_text(notebook)
    required_headings = get_required_headings(notebook_path)
    missing = [heading for heading in required_headings if heading not in markdown_text]
    if missing:
        return False, [
            f"{notebook_path.name}: missing required heading {index}/{len(required_headings)}: {heading}"
            for index, heading in enumerate(missing, start=1)
        ]

    return True, []


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("Usage: python robot_waiter_ai/notebooks/validate_notebook.py <notebook.ipynb>")
        return 2

    notebook_path = Path(args[0])
    if not notebook_path.exists():
        print(f"Notebook not found: {notebook_path}")
        return 1

    ok, errors = validate_notebook(notebook_path)
    if not ok:
        print("Notebook validation failed.")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Notebook validation passed.")
    print(f"Notebook: {notebook_path}")
    required_headings = get_required_headings(notebook_path)
    print(f"Required headings found: {len(required_headings)} / {len(required_headings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
