# Training Module

This directory contains the planning and data-preparation tools for GarsonBot's future
supervised fine-tuning workflow. The current milestone still does **not** train a model;
it prepares the dataset, evaluation approach, and experiment plan only.

The current dataset revision reflects post-smoke-test strengthening after the first
`Qwen/Qwen3-0.6B` Colab run showed that the pipeline worked but the model was too weak on
response-style consistency, allergy phrasing, unavailable-menu refusals, and benchmark
keyword coverage.

## Files

| File | Purpose |
|---|---|
| `dataset_builder.py` | Converts `datasets/raw/seed_dialogues.yaml` into JSONL SFT format |
| `dataset_validator.py` | Validates the seed YAML for required fields, allowed intents, and entity coverage |
| `grounded_paraphrase_builder.py` | Builds the separate grounded paraphrase JSONL dataset for future paraphraser training |
| `grounded_paraphrase_validator.py` | Validates the grounded paraphrase seed YAML and grounding constraints |
| `extract_taskmaster_user_utterances.py` | Safely extracts raw USER utterances from local Taskmaster-2 JSON into a reviewable intermediate JSONL file |
| `filter_taskmaster_candidates.py` | Applies small rule-based candidate labels to extracted Taskmaster USER utterances and writes capped review files |
| `build_taskmaster_food_ordering_adaptation_template.py` | Builds a manual review-only adaptation worksheet from food-ordering Taskmaster candidates only |
| `build_taskmaster_food_ordering_adaptation_pilot.py` | Builds a small 30-row manual pilot worksheet from the food-ordering adaptation template |
| `build_taskmaster_food_ordering_adaptation_pilot_v2.py` | Builds a second menu-aware manual pilot that excludes first-pilot rows and down-ranks unsupported-item patterns |
| `build_taskmaster_food_ordering_adaptation_pilot_v3.py` | Builds a third targeted raw-utterance pilot with stronger noise filtering, deduplication, and a cap on generic order-start prompts |
| `build_taskmaster_food_ordering_adaptation_pilot_v4.py` | Builds a fourth tightened high-precision pilot with stricter fragment, price, allergy, and modification filtering |
| `taskmaster_pilot_findings.md` | Short note summarizing why Taskmaster should remain inspiration rather than a direct row-to-training source |
| `build_menu_grounded_user_message_seed.py` | Builds a menu-first, review-only Turkish user-message seed worksheet from supported project menu items |
| `refine_menu_grounded_user_message_seed.py` | Trims and rebalances the menu-grounded seed worksheet into a smaller, less redundant review-only set |
| `review_menu_grounded_user_message_seed.py` | Adds conservative review metadata to the refined menu-grounded seed worksheet before any canonical preview step |
| `build_menu_grounded_canonical_preview.py` | Runs reviewed menu-grounded seed rows through the deterministic waiter path and writes review-only canonical previews |
| `review_menu_grounded_canonical_preview.py` | Adds reviewer-style approval/rejection metadata to menu-grounded canonical previews before any grounded paraphrase use |
| `build_menu_grounded_paraphrase_candidates.py` | Builds a review-only grounded paraphrase candidate worksheet from approved menu-grounded canonical review rows |
| `menu_grounded_canonical_review_findings.md` | Summarizes the rejected deterministic clusters from menu-grounded canonical preview review without changing runtime behavior |
| `build_menu_grounded_paraphrase_manual_pilot.py` | Selects a small diverse manual safe-paraphrase pilot from approved menu-grounded paraphrase candidates |
| `build_menu_grounded_paraphrase_manual_pilot_v2.py` | Selects a second 10-row manual safe-paraphrase pilot from unused menu-grounded paraphrase candidates with a stronger diversity preference |
| `review_menu_grounded_paraphrase_manual_pilot.py` | Applies a semantic review gate to manually written menu-grounded paraphrase pilot rows without promoting them into processed datasets |
| `export_approved_grounded_paraphrase_candidates.py` | Exports only semantically approved menu-grounded paraphrase pilot rows into a clean approved-candidates intermediate JSONL file |
| `menu_grounded_paraphrase_manual_review_guide.md` | Reviewer guidance for writing safe Turkish paraphrases without weakening grounding or safety constraints |
| `export_taskmaster_accepted_adaptations.py` | Exports only manually accepted food-ordering pilot rows into a clean intermediate JSONL file |
| `build_taskmaster_canonical_preview.py` | Runs accepted food-ordering adaptations through the existing deterministic waiter logic and writes review-only canonical previews |
| `review_taskmaster_canonical_preview.py` | Adds manual review metadata to deterministic preview rows without changing runtime logic |
| `taskmaster_food_ordering_manual_adaptation_guide.md` | Reviewer guidance for safely filling the food-ordering adaptation worksheet by hand |
| `export_grounded_paraphrase_valid_reference.py` | Exports the held-out grounded paraphrase valid split as scorer-ready JSONL reference data |
| `export_grounded_paraphrase_output_template.py` | Exports a fill-ready JSONL output template for the held-out grounded paraphrase valid split |
| `robot_waiter_ai.evals.grounded_paraphrase_output_scorer` | Scores saved grounded paraphrase outputs against preserve-term and forbidden-term constraints |
| `fine_tuning_plan.md` | Practical plan for the first supervised fine-tuning experiment |
| `model_shortlist.md` | Practical shortlist of candidate base models for the first LoRA/QLoRA experiment |
| `colab_finetuning_notebook_plan.md` | Earlier Colab planning notes kept for reference |
| `colab_qwen3_smoke_test.ipynb` | Earlier notebook draft kept for reference, not the primary planning artifact |
| `colab_training_checklist.md` | Pre-flight and post-run checklist for the first Colab smoke test |
| `training_config.example.yaml` | Example training configuration for a future LoRA/QLoRA run |
| `train_lora.py` | Dry-run training skeleton that validates config and dataset paths without starting training |

## How to Run Current Tools

From the project root, run:

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.training.dataset_validator
.venv\Scripts\python.exe -m robot_waiter_ai.training.dataset_builder
.venv\Scripts\python.exe -m robot_waiter_ai.training.grounded_paraphrase_validator
.venv\Scripts\python.exe -m robot_waiter_ai.training.grounded_paraphrase_builder
.venv\Scripts\python.exe -m robot_waiter_ai.training.extract_taskmaster_user_utterances
.venv\Scripts\python.exe -m robot_waiter_ai.training.filter_taskmaster_candidates
.venv\Scripts\python.exe -m robot_waiter_ai.training.build_taskmaster_food_ordering_adaptation_template
.venv\Scripts\python.exe -m robot_waiter_ai.training.export_grounded_paraphrase_valid_reference
.venv\Scripts\python.exe -m robot_waiter_ai.training.export_grounded_paraphrase_output_template
.venv\Scripts\python.exe -m robot_waiter_ai.evals.grounded_paraphrase_output_scorer --outputs robot_waiter_ai/evals/sample_grounded_paraphrase_outputs.jsonl
.venv\Scripts\python.exe -m robot_waiter_ai.evals.grounded_paraphrase_output_scorer --reference robot_waiter_ai/evals/grounded_paraphrase_valid_reference.jsonl --outputs robot_waiter_ai/evals/sample_grounded_paraphrase_valid_outputs.jsonl
.venv\Scripts\python.exe -m robot_waiter_ai.evals.grounded_paraphrase_output_scorer --reference robot_waiter_ai/evals/grounded_paraphrase_valid_reference.jsonl --outputs robot_waiter_ai/evals/grounded_paraphrase_valid_output_template.jsonl
.venv\Scripts\python.exe -m robot_waiter_ai.training.train_lora --config robot_waiter_ai/training/training_config.example.yaml --dry-run
```

After a real Colab grounded paraphraser smoke test, copy the held-out generation file into:
- `robot_waiter_ai/evals/generated_grounded_paraphrase_qwen3_0_6b_smoke.jsonl`

Then score it locally with:

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.evals.grounded_paraphrase_output_scorer --reference robot_waiter_ai/evals/grounded_paraphrase_valid_reference.jsonl --outputs robot_waiter_ai/evals/generated_grounded_paraphrase_qwen3_0_6b_smoke.jsonl
```

## Current Assets
- Raw seed dataset: 350 examples
- Processed training split: 298 records
- Processed validation split: 52 records
- Grounded paraphrase seed dataset: 252 examples
- Grounded paraphrase processed split: 215 train / 37 valid
- Grounded paraphrase format-contract regression tests for raw YAML and built JSONL records
- Grounded paraphrase output scorer for saved paraphrase JSONL evaluation
- Validation-only grounded paraphrase reference export for held-out scoring
- Validation-only grounded paraphrase sample outputs fixture with one intentional failure
- Validation-only grounded paraphrase output template export for future model-filled runs
- Separate Colab notebook/template path for grounded paraphraser smoke-test training
- Deterministic evaluation runner
- Deterministic baseline runtime
- Failure-targeted response-style coverage for add/remove/clear/summary/confirm flows
- Expanded unavailable-menu refusal coverage through the `unavailable_item` intent
- Separate menu-grounded paraphrase dataset for future safe paraphraser experiments

## What Is Not Included Yet
- No model downloads
- No `transformers`, `peft`, `trl`, `bitsandbytes`, `torch`, or `unsloth`
- No fine-tuned checkpoint
- No actual training execution

## Fine-Tuning Planning Status
- The dataset foundation has been strengthened for the next smoke-test experiment
- A separate grounded paraphrase dataset foundation now exists for future constrained paraphraser training
- The next approved Colab notebook should treat the model as a grounded paraphraser, not as the source of truth
- The benchmark baseline exists and should remain the reference system
- The first recommended experiment is a conservative LoRA or QLoRA run on an instruct/chat model
- Jetson Orin NX remains a later inference target rather than the first training machine
- The current model recommendation is to start from the Qwen3 small dense class before considering heavier options
- The builder now applies a deterministic shuffle before the 85/15 split so validation coverage is not skewed by grouped seed examples

## Example Config
Use `training_config.example.yaml` as a template for future training configuration.
It documents fields such as:
- model path or name
- train and validation files
- method (`lora` or `qlora`)
- batch and optimization settings
- LoRA hyperparameters
- evaluation and save intervals

## Dry-Run Training Skeleton
`train_lora.py` currently supports config validation and dry-run reporting only.
It checks:
- required config fields
- valid training method (`lora` or `qlora`)
- numeric constraints
- `lora_dropout` range
- existence of train and validation JSONL files

It does **not**:
- import heavy ML libraries
- load a model
- download a model
- start training
- write checkpoints

## Future Steps
- Keep expanding benchmark-targeted Turkish examples where learned-model failures cluster
- Grow the separate grounded paraphrase dataset before any real paraphraser training run
- Retry smoke-test training with a stronger small model only after the refreshed dataset is scored
