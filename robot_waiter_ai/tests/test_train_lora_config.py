from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from robot_waiter_ai.training.train_lora import (
    TrainingConfigError,
    load_config,
    main,
    run_dry_run,
    validate_config,
)


BASE_DIR = Path(__file__).resolve().parents[1]
EXAMPLE_CONFIG = BASE_DIR / "training" / "training_config.example.yaml"


def _write_config(tmp_path: Path, config: dict) -> Path:
    config_path = tmp_path / "training_config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return config_path


def _base_config() -> dict:
    return {
        "base_model_name_or_path": "placeholder-model",
        "output_dir": "artifacts/fine_tuning/test_run",
        "train_file": str(BASE_DIR / "datasets" / "processed" / "waiter_sft_train.jsonl"),
        "valid_file": str(BASE_DIR / "datasets" / "processed" / "waiter_sft_valid.jsonl"),
        "method": "qlora",
        "epochs": 3,
        "learning_rate": 0.0002,
        "batch_size": 2,
        "gradient_accumulation_steps": 8,
        "max_seq_length": 1024,
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        "eval_steps": 25,
        "save_steps": 50,
        "seed": 42,
    }


def test_config_loads_successfully():
    config = load_config(EXAMPLE_CONFIG)

    assert config["method"] in {"lora", "qlora"}
    assert "train_file" in config


def test_missing_required_field_raises_validation_error():
    config = _base_config()
    config.pop("method")

    with pytest.raises(TrainingConfigError, match="Missing required config field"):
        validate_config(config)


def test_invalid_method_raises_validation_error():
    config = _base_config()
    config["method"] = "full_finetune"

    with pytest.raises(TrainingConfigError, match="'method' must be one of"):
        validate_config(config)


def test_invalid_numeric_values_raise_validation_error():
    config = _base_config()
    config["epochs"] = 0

    with pytest.raises(TrainingConfigError, match="'epochs' must be a positive integer"):
        validate_config(config)


def test_missing_dataset_file_raises_validation_error():
    config = _base_config()
    config["train_file"] = str(BASE_DIR / "datasets" / "processed" / "missing_train.jsonl")

    with pytest.raises(TrainingConfigError, match="'train_file' does not exist"):
        validate_config(config)


def test_dry_run_returns_success_without_training(tmp_path):
    config_path = _write_config(tmp_path, _base_config())

    loaded = run_dry_run(config_path)
    exit_code = main(["--config", str(config_path), "--dry-run"])

    assert loaded.method == "qlora"
    assert exit_code == 0
