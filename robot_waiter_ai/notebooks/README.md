# Notebooks

This directory contains notebook planning and notebook-oriented documentation for future
fine-tuning experiments, with the current emphasis on grounded paraphraser smoke-test
preparation rather than runtime integration.

The current stage is Markdown-first on purpose:
- no notebook is executed from this repository task
- no model is downloaded from this repository task
- no heavy ML dependency is added to the local project
- no training is started locally

## Current Notebook Planning Assets

| File | Purpose |
|---|---|
| `colab_qwen3_0_6b_lora_smoke_test.md` | Legacy/reference-only raw waiter SFT smoke-test plan kept for comparison runs |
| `colab_qwen3_0_6b_lora_smoke_test.ipynb` | Legacy/reference-only raw waiter Colab notebook kept for comparison runs |
| `colab_grounded_paraphraser_qwen3_0_6b_smoke_test.md` | Primary Markdown-first Colab plan for the grounded paraphraser smoke test |
| `colab_grounded_paraphraser_qwen3_0_6b_smoke_test.ipynb` | Primary executable Colab notebook template for grounded paraphraser smoke-test training |
| `validate_notebook.py` | Standard-library validator for notebook JSON structure and required section headings |

## Scope Reminder
- This project is a Turkish conversational AI module for a waiter robot
- Navigation, ROS, SLAM, speech runtime integration, databases, and dashboards are outside this notebook-planning task
- Jetson Orin NX remains a future inference target, not the first training machine

## Intended Workflow
1. Prepare and review the Markdown notebook plan in this folder.
2. Use the executable Colab notebook in this folder as the first approved training template.
3. Use Google Colab as the first approved real training environment.
4. Run a conservative smoke-test experiment with `Qwen/Qwen3-0.6B`.
5. Treat the raw waiter SFT notebook as legacy/reference-only unless a comparison run is explicitly needed.
6. Use the grounded paraphraser notebook for canonical-response-to-safe-paraphrase experiments.
7. After a Colab grounded paraphraser run, place the held-out outputs at `robot_waiter_ai/evals/generated_grounded_paraphrase_qwen3_0_6b_smoke.jsonl`.
8. Score them locally with:
   - `.venv\Scripts\python.exe -m robot_waiter_ai.evals.grounded_paraphrase_output_scorer --reference robot_waiter_ai/evals/grounded_paraphrase_valid_reference.jsonl --outputs robot_waiter_ai/evals/generated_grounded_paraphrase_qwen3_0_6b_smoke.jsonl`
9. Use the matching scorer for any other saved evaluation outputs:
   - `robot_waiter_ai.evals.generated_output_adapter` for waiter benchmark outputs
   - `robot_waiter_ai.evals.grounded_paraphrase_output_scorer` for grounded paraphraser outputs

The deterministic baseline remains the reference system throughout this stage.
