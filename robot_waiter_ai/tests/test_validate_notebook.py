from __future__ import annotations

import json
from pathlib import Path

from robot_waiter_ai.notebooks.validate_notebook import (
    DEFAULT_REQUIRED_HEADINGS,
    get_required_headings,
    validate_notebook,
)


def test_colab_notebook_validates_successfully():
    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "colab_qwen3_0_6b_lora_smoke_test.ipynb"
    )

    ok, errors = validate_notebook(notebook_path)

    assert notebook_path.exists()
    assert ok, "\n".join(errors)
    assert len(DEFAULT_REQUIRED_HEADINGS) >= 10


def test_grounded_paraphraser_notebook_validates_successfully():
    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "colab_grounded_paraphraser_qwen3_0_6b_smoke_test.ipynb"
    )

    ok, errors = validate_notebook(notebook_path)

    assert notebook_path.exists()
    assert ok, "\n".join(errors)
    assert len(get_required_headings(notebook_path)) >= 10


def test_missing_heading_error_includes_notebook_name():
    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "colab_grounded_paraphraser_qwen3_0_6b_smoke_test.ipynb"
    )

    notebook = {
        "nbformat": 4,
        "cells": [
            {
                "cell_type": "markdown",
                "source": ["# Temporary notebook\n", "## A. Title And Warning\n"],
            }
        ],
    }

    temp_path = notebook_path.with_name("tmp_missing_heading_test.ipynb")
    temp_path.write_text(json.dumps(notebook), encoding="utf-8")
    try:
        ok, errors = validate_notebook(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)

    assert not ok
    assert errors
    assert "tmp_missing_heading_test.ipynb" in errors[0]
    assert "missing required heading" in errors[0]
