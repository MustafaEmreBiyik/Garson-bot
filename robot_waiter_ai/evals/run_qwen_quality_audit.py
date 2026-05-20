from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from robot_waiter_ai.inference.qwen_lora_waiter import QwenLoraWaiterBackend

DEFAULT_EVAL_FILE = "robot_waiter_ai/evals/pure_qwen_restaurant_eval_200.jsonl"
DEFAULT_OUTPUT_FILE = "robot_waiter_ai/evals/pure_qwen_audit_results.jsonl"


def run_audit(
    eval_file: str | Path = DEFAULT_EVAL_FILE,
    output_file: str | Path = DEFAULT_OUTPUT_FILE,
    adapter_path: str = "robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora",
    base_model_path: str = "robot_waiter_ai/models/Qwen2.5-3B-Instruct",
    dry_run: bool = True,
    load_in_4bit: bool = True,
    device: str = "auto",
) -> dict[str, Any]:
    eval_path = Path(eval_file)
    if not eval_path.exists():
        raise FileNotFoundError(f"Eval file not found: {eval_path}")

    records: list[dict[str, Any]] = []
    with open(eval_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    backend = None
    if not dry_run:
        backend = QwenLoraWaiterBackend(
            adapter_path=adapter_path,
            base_model_path=base_model_path,
            load_in_4bit=load_in_4bit,
            device=device,
        )

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    start_time = time.time()
    
    passed = 0
    failed = 0

    with open(out_path, "w", encoding="utf-8") as f:
        for record in records:
            user_msg = record.get("user_message", "")
            
            turn_start = time.time()
            if dry_run:
                reply = f"[MOCK] yanit: {user_msg}"
                latency = 0.01
            else:
                reply = backend.generate_reply(user_msg)
                latency = time.time() - turn_start

            # Dummy mock scoring based on exact match for the skeleton.
            # In a real environment, string inclusion, LLM-as-a-judge, or specialized metrics would apply.
            score_pass = True
            for word in record.get("must_include", []):
                if not dry_run and str(word).lower() not in reply.lower():
                    score_pass = False
                    
            if score_pass:
                passed += 1
            else:
                failed += 1

            result_row = {
                "id": record.get("id"),
                "category": record.get("category"),
                "user_message": user_msg,
                "model_response": reply,
                "latency_sec": latency,
                "passed": score_pass,
                "dry_run": dry_run
            }
            results.append(result_row)
            f.write(json.dumps(result_row, ensure_ascii=False) + "\n")

    total_time = time.time() - start_time
    
    metadata = {}
    if backend:
        metadata = backend.runtime_metadata()
    else:
        metadata = {"backend_name": "mock", "device_used": "mock", "load_in_4bit": load_in_4bit}

    summary = {
        "total_records": len(records),
        "passed": passed,
        "failed": failed,
        "pass_rate": (passed / len(records)) if records else 0.0,
        "total_time_sec": total_time,
        "avg_latency_sec": total_time / len(records) if records else 0.0,
        "dry_run": dry_run,
        "metadata": metadata
    }
    
    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Pure Qwen Quality Audit")
    parser.add_argument("--eval-file", default=DEFAULT_EVAL_FILE, help="Path to JSONL eval file")
    parser.add_argument("--output-file", default=DEFAULT_OUTPUT_FILE, help="Path to JSONL output results")
    parser.add_argument("--dry-run", action="store_true", help="Run without loading real model (CPU-safe mock)")
    parser.add_argument("--no-4bit", action="store_true", help="Disable 4-bit loading (if not dry run)")
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"], help="Device to use")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        summary = run_audit(
            eval_file=args.eval_file,
            output_file=args.output_file,
            dry_run=args.dry_run,
            load_in_4bit=not args.no_4bit,
            device=args.device,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(f"Error during audit: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
