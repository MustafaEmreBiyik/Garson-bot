from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from robot_waiter_ai.evals.menu_context_prompt_builder import (
    build_menu_context_system_prompt,
    load_menu_context,
)
from robot_waiter_ai.inference.qwen_lora_waiter import DEFAULT_BASE_MODEL_PATH, QwenLoraWaiterBackend

DEFAULT_ADAPTER_PATH = "robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora"
DEFAULT_MENU_CONTEXT_PATH = "robot_waiter_ai/evals/sample_menu_context.json"
DEFAULT_DIALOGUES_PATH = "robot_waiter_ai/evals/qwen_menu_context_probe_dialogues.jsonl"
DEFAULT_OUTPUT_PATH = "robot_waiter_ai/evals/qwen_menu_context_probe_outputs.jsonl"
DEFAULT_DEVICE = "auto"


def _get_torch_cuda_available() -> bool:
    import torch

    return bool(torch.cuda.is_available())


def _load_dialogues(dialogues_path: Path | str) -> list[dict[str, Any]]:
    path = Path(dialogues_path)
    dialogues: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        record = json.loads(stripped)
        if not isinstance(record, dict):
            raise ValueError(f"Dialogue line {line_number} must be a JSON object.")
        turns = record.get("turns")
        if not isinstance(turns, list) or not turns:
            raise ValueError(f"Dialogue line {line_number} must include a non-empty 'turns' list.")
        dialogues.append(record)
    return dialogues


def run_menu_context_probe(
    base_model_path: str,
    adapter_path: str,
    menu_context_path: Path | str = DEFAULT_MENU_CONTEXT_PATH,
    dialogues_path: Path | str = DEFAULT_DIALOGUES_PATH,
    output_path: Path | str = DEFAULT_OUTPUT_PATH,
    device: str = DEFAULT_DEVICE,
    limit_dialogues: int | None = None,
    load_in_4bit: bool = True,
) -> dict[str, Any]:
    cuda_available = _get_torch_cuda_available()
    print(f"torch.cuda.is_available(): {cuda_available}")
    if device == "cuda" and not cuda_available:
        raise RuntimeError("CUDA device was requested but torch.cuda.is_available() is False on this machine.")

    menu_context = load_menu_context(menu_context_path)
    system_prompt = build_menu_context_system_prompt(menu_context)
    dialogues = _load_dialogues(dialogues_path)
    if limit_dialogues is not None:
        dialogues = dialogues[:limit_dialogues]

    backend = QwenLoraWaiterBackend(
        adapter_path=adapter_path,
        base_model_path=base_model_path,
        load_in_4bit=load_in_4bit,
        device=device,
    )
    runtime_metadata = backend.runtime_metadata()

    resolved_output_path = Path(output_path)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    with resolved_output_path.open("w", encoding="utf-8") as handle:
        for dialogue in dialogues:
            history: list[dict[str, str]] = []
            for turn_index, turn in enumerate(dialogue["turns"]):
                user_message = str(turn.get("user", "")).strip()
                if not user_message:
                    raise ValueError(f"Dialogue '{dialogue.get('id', 'unknown')}' has an empty user turn.")

                model_response = backend.generate_reply(
                    user_message,
                    conversation_history=history,
                    system_prompt_override=system_prompt,
                )
                history.append({"role": "user", "content": user_message})
                history.append({"role": "assistant", "content": model_response})

                row = {
                    "dialogue_id": dialogue.get("id", ""),
                    "scenario": dialogue.get("scenario", ""),
                    "turn_index": turn_index,
                    "user_message": user_message,
                    "model_response": model_response,
                    "expected_observations": dialogue.get("expected_observations", []),
                    "metadata": {
                        "base_model_path": runtime_metadata["model_path"],
                        "adapter_path": runtime_metadata["adapter_path"],
                        "device_used": runtime_metadata["device_used"],
                        "torch_cuda_available": runtime_metadata["torch_cuda_available"],
                        "torch_dtype": runtime_metadata["torch_dtype"],
                        "load_in_4bit": runtime_metadata["load_in_4bit"],
                        "menu_context_file": str(Path(menu_context_path)),
                    },
                }
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                rows.append(row)

    return {
        "output_path": str(resolved_output_path),
        "dialogue_count": len(dialogues),
        "turn_count": len(rows),
        "backend_name": runtime_metadata["backend_name"],
        "device_used": runtime_metadata["device_used"],
        "torch_cuda_available": runtime_metadata["torch_cuda_available"],
        "base_model_path": runtime_metadata["model_path"],
        "adapter_path": runtime_metadata["adapter_path"],
        "menu_context_path": str(Path(menu_context_path)),
        "dialogues_path": str(Path(dialogues_path)),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a multi-turn Qwen menu-context probe and save JSONL outputs.")
    parser.add_argument(
        "--base-model-path",
        default=DEFAULT_BASE_MODEL_PATH,
        help=f"Local base model path or Hugging Face model id (default: {DEFAULT_BASE_MODEL_PATH})",
    )
    parser.add_argument(
        "--adapter-path",
        default=DEFAULT_ADAPTER_PATH,
        help=f"Path to the LoRA adapter directory (default: {DEFAULT_ADAPTER_PATH})",
    )
    parser.add_argument(
        "--menu-context-path",
        default=DEFAULT_MENU_CONTEXT_PATH,
        help=f"Path to the sample menu context JSON file (default: {DEFAULT_MENU_CONTEXT_PATH})",
    )
    parser.add_argument(
        "--dialogues-path",
        default=DEFAULT_DIALOGUES_PATH,
        help=f"Path to the probe dialogues JSONL file (default: {DEFAULT_DIALOGUES_PATH})",
    )
    parser.add_argument(
        "--output-path",
        default=DEFAULT_OUTPUT_PATH,
        help=f"Where to write JSONL outputs (default: {DEFAULT_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--device",
        default=DEFAULT_DEVICE,
        choices=("auto", "cuda", "cpu"),
        help="Runtime device preference (default: auto)",
    )
    parser.add_argument(
        "--limit-dialogues",
        type=int,
        default=None,
        help="Optional maximum number of dialogues to run from the input JSONL.",
    )
    parser.add_argument(
        "--no-4bit",
        action="store_true",
        help="Disable 4-bit loading if bitsandbytes is unavailable or CPU fallback is needed",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    summary = run_menu_context_probe(
        base_model_path=args.base_model_path,
        adapter_path=args.adapter_path,
        menu_context_path=args.menu_context_path,
        dialogues_path=args.dialogues_path,
        output_path=args.output_path,
        device=args.device,
        limit_dialogues=args.limit_dialogues,
        load_in_4bit=not args.no_4bit,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
