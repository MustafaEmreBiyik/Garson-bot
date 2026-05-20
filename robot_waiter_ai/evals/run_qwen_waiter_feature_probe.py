from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from robot_waiter_ai.inference.menu_context_builder import build_menu_context
from robot_waiter_ai.inference.qwen_lora_waiter import DEFAULT_BASE_MODEL_PATH, QwenLoraWaiterBackend

DEFAULT_ADAPTER_PATH = "robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora"
DEFAULT_OUTPUT_PATH = "robot_waiter_ai/evals/qwen_waiter_feature_probe_outputs.jsonl"
DEFAULT_DEVICE = "auto"
FEATURE_PROBE_CASES = [
    {"case_id": "feature_probe_greeting", "user_prompt": "Merhaba"},
    {"case_id": "feature_probe_add_item", "user_prompt": "2 ayran istiyorum"},
    {"case_id": "feature_probe_price_question", "user_prompt": "Ayran kaç lira?"},
    {"case_id": "feature_probe_allergen_question", "user_prompt": "Mercimek çorbasında alerjen var mı?"},
]


def run_feature_probe(
    base_model_path: str,
    adapter_path: str,
    output_path: Path | str = DEFAULT_OUTPUT_PATH,
    device: str = DEFAULT_DEVICE,
    load_in_4bit: bool = True,
) -> dict[str, Any]:
    backend = QwenLoraWaiterBackend(
        adapter_path=adapter_path,
        base_model_path=base_model_path,
        load_in_4bit=load_in_4bit,
        device=device,
    )
    menu_context = build_menu_context()
    runtime_metadata = backend.runtime_metadata()
    resolved_output_path = Path(output_path)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    with resolved_output_path.open("w", encoding="utf-8") as handle:
        for case in FEATURE_PROBE_CASES:
            response = backend.generate_reply(case["user_prompt"], menu_context=menu_context)
            row = {
                "case_id": case["case_id"],
                "response": response,
                "backend_name": runtime_metadata["backend_name"],
                "metadata": {
                    "user_prompt": case["user_prompt"],
                    "device_used": runtime_metadata["device_used"],
                    "torch_cuda_available": runtime_metadata["torch_cuda_available"],
                    "model_path": runtime_metadata["model_path"],
                    "adapter_path": runtime_metadata["adapter_path"],
                    "torch_dtype": runtime_metadata["torch_dtype"],
                    "load_in_4bit": runtime_metadata["load_in_4bit"],
                },
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows.append(row)

    return {
        "output_path": str(resolved_output_path),
        "record_count": len(rows),
        "backend_name": runtime_metadata["backend_name"],
        "device_used": runtime_metadata["device_used"],
        "torch_cuda_available": runtime_metadata["torch_cuda_available"],
        "model_path": runtime_metadata["model_path"],
        "adapter_path": runtime_metadata["adapter_path"],
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a small Qwen waiter feature probe and save JSONL outputs.")
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
        "--no-4bit",
        action="store_true",
        help="Disable 4-bit loading if bitsandbytes is unavailable or CPU fallback is needed",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    summary = run_feature_probe(
        base_model_path=args.base_model_path,
        adapter_path=args.adapter_path,
        output_path=args.output_path,
        device=args.device,
        load_in_4bit=not args.no_4bit,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
