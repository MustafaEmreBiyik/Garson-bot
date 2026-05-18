from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


REQUIRED_FIELDS = {
    "base_model_name_or_path",
    "output_dir",
    "train_file",
    "valid_file",
    "method",
    "epochs",
    "learning_rate",
    "batch_size",
    "gradient_accumulation_steps",
    "max_seq_length",
    "lora_r",
    "lora_alpha",
    "lora_dropout",
    "eval_steps",
    "save_steps",
    "seed",
}

ALLOWED_METHODS = {"lora", "qlora"}
POSITIVE_INT_FIELDS = {
    "epochs",
    "batch_size",
    "gradient_accumulation_steps",
    "max_seq_length",
    "lora_r",
    "lora_alpha",
    "eval_steps",
    "save_steps",
    "seed",
}
POSITIVE_FLOAT_FIELDS = {"learning_rate"}


class TrainingConfigError(ValueError):
    pass


@dataclass
class TrainingConfig:
    base_model_name_or_path: str
    output_dir: str
    train_file: str
    valid_file: str
    method: str
    epochs: int
    learning_rate: float
    batch_size: int
    gradient_accumulation_steps: int
    max_seq_length: int
    lora_r: int
    lora_alpha: int
    lora_dropout: float
    eval_steps: int
    save_steps: int
    seed: int

    @property
    def effective_batch_size(self) -> int:
        return self.batch_size * self.gradient_accumulation_steps


def load_config(config_path: Path | str) -> Dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Training config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise TrainingConfigError("Training config must be a YAML mapping.")
    return data


def _validate_required_fields(config: Dict[str, Any]) -> None:
    missing = sorted(field for field in REQUIRED_FIELDS if field not in config)
    if missing:
        joined = ", ".join(missing)
        raise TrainingConfigError(f"Missing required config field(s): {joined}")


def _validate_method(method: Any) -> str:
    if not isinstance(method, str) or method not in ALLOWED_METHODS:
        allowed = ", ".join(sorted(ALLOWED_METHODS))
        raise TrainingConfigError(f"'method' must be one of: {allowed}")
    return method


def _validate_positive_int(config: Dict[str, Any], field_name: str) -> int:
    value = config.get(field_name)
    if not isinstance(value, int) or value <= 0:
        raise TrainingConfigError(f"'{field_name}' must be a positive integer.")
    return value


def _validate_positive_float(config: Dict[str, Any], field_name: str) -> float:
    value = config.get(field_name)
    if not isinstance(value, (int, float)) or value <= 0:
        raise TrainingConfigError(f"'{field_name}' must be a positive number.")
    return float(value)


def _validate_dropout(config: Dict[str, Any]) -> float:
    value = config.get("lora_dropout")
    if not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
        raise TrainingConfigError("'lora_dropout' must be between 0 and 1.")
    return float(value)


def _validate_string(config: Dict[str, Any], field_name: str) -> str:
    value = config.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise TrainingConfigError(f"'{field_name}' must be a non-empty string.")
    return value


def _validate_existing_file(config: Dict[str, Any], field_name: str) -> str:
    value = _validate_string(config, field_name)
    path = Path(value)
    if not path.exists():
        raise TrainingConfigError(f"'{field_name}' does not exist: {value}")
    return value


def validate_config(config: Dict[str, Any]) -> TrainingConfig:
    _validate_required_fields(config)

    return TrainingConfig(
        base_model_name_or_path=_validate_string(config, "base_model_name_or_path"),
        output_dir=_validate_string(config, "output_dir"),
        train_file=_validate_existing_file(config, "train_file"),
        valid_file=_validate_existing_file(config, "valid_file"),
        method=_validate_method(config.get("method")),
        epochs=_validate_positive_int(config, "epochs"),
        learning_rate=_validate_positive_float(config, "learning_rate"),
        batch_size=_validate_positive_int(config, "batch_size"),
        gradient_accumulation_steps=_validate_positive_int(config, "gradient_accumulation_steps"),
        max_seq_length=_validate_positive_int(config, "max_seq_length"),
        lora_r=_validate_positive_int(config, "lora_r"),
        lora_alpha=_validate_positive_int(config, "lora_alpha"),
        lora_dropout=_validate_dropout(config),
        eval_steps=_validate_positive_int(config, "eval_steps"),
        save_steps=_validate_positive_int(config, "save_steps"),
        seed=_validate_positive_int(config, "seed"),
    )


def format_dry_run_summary(config: TrainingConfig) -> str:
    lines = [
        "LoRA/QLoRA Training Dry Run",
        "===========================",
        f"Base model path/name : {config.base_model_name_or_path}",
        f"Output directory     : {config.output_dir}",
        f"Train file           : {config.train_file}",
        f"Valid file           : {config.valid_file}",
        f"Method               : {config.method}",
        f"Epochs               : {config.epochs}",
        f"Learning rate        : {config.learning_rate}",
        f"Batch size           : {config.batch_size}",
        f"Grad accum steps     : {config.gradient_accumulation_steps}",
        f"Effective batch size : {config.effective_batch_size}",
        f"Max seq length       : {config.max_seq_length}",
        f"LoRA r               : {config.lora_r}",
        f"LoRA alpha           : {config.lora_alpha}",
        f"LoRA dropout         : {config.lora_dropout}",
        f"Eval steps           : {config.eval_steps}",
        f"Save steps           : {config.save_steps}",
        f"Seed                 : {config.seed}",
        "",
        "Dry-run only: configuration is valid, dataset paths exist, and no training was started.",
        "No model was loaded, no model was downloaded, and no checkpoint was created.",
    ]
    return "\n".join(lines)


def run_dry_run(config_path: Path | str) -> TrainingConfig:
    raw_config = load_config(config_path)
    return validate_config(raw_config)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a future LoRA/QLoRA training config without starting training."
    )
    parser.add_argument("--config", required=True, help="Path to the training YAML config file.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and dataset paths, then print a dry-run summary.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.dry_run:
        parser.error("Only --dry-run is supported in this training skeleton.")

    config = run_dry_run(args.config)
    print(format_dry_run_summary(config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
