# Evaluation Cases

This directory contains the benchmark definitions and automated runner for GarsonBot.

## Files

| File | Purpose |
|---|---|
| `evaluation_cases.yaml` | Human-authored benchmark cases for the deterministic waiter assistant |
| `eval_runner.py` | Automated evaluation runner for the current deterministic `DialogueManager` |
| `generated_output_adapter.py` | Scores saved generated responses from a JSONL file against the same benchmark |
| `sample_generated_outputs.jsonl` | Small deterministic sample file for generated-output evaluation |

## Case Format

```yaml
evaluation_cases:
  - id: eval_001
    user: "Merhaba"
    expected_intent: greeting
    expected_contains: ["Hoş geldiniz", "Merhaba"]
    expected_not_contains: []
    notes: "System must respond with a greeting."
```

Supported fields:
- `id`
- `user`
- `expected_intent`
- `expected_contains`
- `expected_not_contains`
- `notes`

## How to Run

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.evals.eval_runner
.venv\Scripts\python.exe -m robot_waiter_ai.evals.generated_output_adapter --outputs robot_waiter_ai/evals/sample_generated_outputs.jsonl
```

The runner:
- loads `evaluation_cases.yaml`
- validates basic case structure
- runs each case through a single deterministic `DialogueManager` session
- checks expected intent, required substrings, and forbidden substrings
- prints total cases, passed, failed, invalid, pass rate, and failed-case reasons

The generated-output adapter:
- loads saved JSONL records with `case_id` and `response`
- validates output-record structure
- matches responses to benchmark case IDs
- reuses the same expected text and forbidden text scoring logic
- reports matched outputs, missing outputs, failed cases, invalid output records, and pass rate

## Why This Exists

This runner is the shared benchmark harness for:
- the deterministic baseline
- a future fine-tuned model
- a future routing or comparison layer
- a future generated-output comparison workflow

It intentionally does not use an LLM or any external API.

## Pure Qwen Quality Audit (Sprint 1)

The Pure Qwen Quality Audit runner evaluates the model against a specialized restaurant dataset (`pure_qwen_restaurant_eval_200.jsonl`).

### How to Run the Mock/Dry-Run (CPU Safe)
This mode tests the runner framework itself without loading the model into memory.
```bash
python -m robot_waiter_ai.evals.run_qwen_quality_audit --dry-run
```

### How to Run the Real Audit (GPU/Jetson)
Use this command on a capable GPU machine to perform the real LLM inference and quality check.
```bash
python -m robot_waiter_ai.evals.run_qwen_quality_audit --device cuda
```
*(On Windows or memory-constrained setups, if bitsandbytes fails, append `--no-4bit`)*

The results are saved to `robot_waiter_ai/evals/pure_qwen_audit_results.jsonl`, which you can summarize using the template in `reports/sprint1_qwen_quality_audit_template.md`.
