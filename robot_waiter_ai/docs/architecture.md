# Architecture

## Overview
A lightweight, text-first conversational module with clear boundaries between menu data,
order state, dialogue logic, dataset preparation, deterministic evaluation, and future
grounded model usage.

## Runtime Modules
- **app** - CLI entrypoint and configuration
- **assistant** - persona, menu knowledge, order state, safety rules, dialogue manager
- **inference** - backend-agnostic request/response contract, runtime adapters, structured grounding schema, and future grounded-generation planning
- **data** - `menu.yaml` and `restaurant_info.yaml` as structured source-of-truth files
- **prompts** - prompt templates reserved for later model-oriented work
- **speech** - placeholders only, outside the current implementation scope

## Training and Dataset Pipeline
- **datasets/raw/** - `seed_dialogues.yaml` with Turkish waiter conversations
- **datasets/raw/** - `grounded_paraphrase_seed.yaml` for future grounded paraphraser supervision
- **datasets/processed/** - generated JSONL training and validation files
- **notebooks/** - Colab assets for both raw waiter SFT smoke tests and grounded paraphraser smoke tests
- **training/dataset_builder.py** - converts seed dialogues into JSONL
- **training/dataset_validator.py** - validates seed data fields and intent structure
- **training/grounded_paraphrase_builder.py** - converts grounded paraphrase seed data into JSONL
- **training/grounded_paraphrase_validator.py** - validates preserve-term and forbidden-term constraints
- **training/fine_tuning_plan.md** - documents fine-tuning strategy and current experiment conclusions
- **training/model_shortlist.md** - compares candidate base-model families
- **training/colab_training_checklist.md** - execution checklist for Colab smoke tests
- **training/training_config.example.yaml** - example future training configuration
- **training/train_lora.py** - dry-run-only config validation skeleton for future LoRA/QLoRA work

## Evaluation Layer
- **evals/evaluation_cases.yaml** - human-authored benchmark cases
- **evals/eval_runner.py** - evaluation harness that defaults to the deterministic backend through the inference abstraction
- **evals/generated_output_adapter.py** - scores saved generated responses against the same benchmark without loading a model
- **evals/grounded_paraphrase_output_scorer.py** - scores saved paraphrase outputs against preserve-term and forbidden-term grounding constraints
- **evals/experiment_results.md** - documents learned-model smoke-test outcomes and failure patterns

## Runtime Data Flow Today
```text
user message -> inference request -> deterministic backend adapter -> assistant response
```

## Evaluation Data Flow
```text
evaluation_cases.yaml -> eval_runner -> inference backend -> pass/fail report
```

## Generated Output Evaluation Flow
```text
evaluation_cases.yaml + generated_outputs.jsonl -> generated_output_adapter -> pass/fail report
```

## Grounded Paraphrase Evaluation Flow
```text
grounded_paraphrase_seed.yaml + grounded_paraphrase_outputs.jsonl
  -> grounded_paraphrase_output_scorer
  -> constraint pass/fail report
```

## Grounded Paraphraser Smoke-Test Flow
```text
grounded_paraphrase_seed.yaml
  -> grounded_paraphrase_builder
  -> grounded_paraphrase_train.jsonl / grounded_paraphrase_valid.jsonl
  -> export_grounded_paraphrase_valid_reference
  -> export_grounded_paraphrase_output_template
  -> Colab grounded paraphraser notebook
  -> evals/generated_grounded_paraphrase_qwen3_0_6b_smoke.jsonl
  -> grounded_paraphrase_output_scorer
```

The evaluation runner keeps the current MVP deterministic:
- no external APIs
- no LLM calls
- no model training

The default backend remains the current `DialogueManager` through
`inference/deterministic_adapter.py`, so existing CLI and evaluation behavior stay intact.

## Training Data Flow
```text
seed_dialogues.yaml -> dataset_validator -> dataset_builder -> waiter_sft_train.jsonl
                                                       -> waiter_sft_valid.jsonl
```

## Grounded Paraphrase Data Flow
```text
grounded_paraphrase_seed.yaml -> grounded_paraphrase_validator -> grounded_paraphrase_builder -> grounded_paraphrase_train.jsonl
                                                                                               -> grounded_paraphrase_valid.jsonl
```

## Fine-Tuning Experiment Flow
```text
model_shortlist -> Colab notebook plan -> training_config -> dry-run validation -> Google Colab smoke test -> adapter/checkpoint
adapter/checkpoint -> generated outputs JSONL -> generated_output_adapter -> benchmark comparison
```

At the current stage, the training entrypoint is intentionally limited to dry-run
validation. It does not import ML frameworks, load a model, or execute training.

Saved model outputs can already be benchmarked before runtime integration by using
`generated_output_adapter.py` with a JSONL file of `case_id` / `response` pairs.

## Experiment Outcome So Far
The first two learned-model smoke tests established:
- the training and export pipeline works
- raw generated responses are currently weaker than the deterministic baseline
- menu faithfulness, exact prices, order integrity, allergy caution, and off-topic refusal
  should not be delegated to unconstrained generation

Neither the 0.6B nor the 1.7B Qwen3 smoke-test model is currently acceptable as the main
waiter assistant.

## Planned Grounded Generation Direction
The next model-oriented architecture should remain grounded:

```text
user input
  -> deterministic intent/menu/order/safety layer
  -> structured action/result
  -> optional LLM paraphraser
  -> final safety/grounding check
  -> final response
```

The deterministic layer should remain the source of truth for:
- menu availability
- prices
- order add/remove/clear/summary/confirm logic
- allergy caution
- off-topic refusal

The model, if used, should mainly help with:
- more natural Turkish phrasing
- bounded paraphrasing of deterministic responses
- small-talk polish inside restaurant scope

The current repo now includes a concrete structured grounding contract in:
- `inference/structured_result.py`
- `inference/grounded_result_builder.py`
- `inference/grounded_response_formatter.py`
- `inference/grounded_demo.py`

That contract is intentionally lightweight and non-invasive. It defines deterministic
result objects for:
- action classification and support status
- menu grounding
- order grounding
- safety grounding
- canonical deterministic response plus paraphrase constraints

This prepares future grounded paraphrasing while keeping current runtime behavior
unchanged.

The builder prototype is a bridge layer:
- it derives `GroundedResult` objects from user messages
- it keeps the deterministic baseline as the source of truth
- it captures canonical response text alongside structured facts
- it does not yet change CLI/runtime output paths

The formatter prototype is the next safety layer:
- it returns the canonical deterministic response when no paraphrase candidate exists
- it accepts a paraphrase candidate only if the grounded safety checks pass
- it falls back to the canonical response when a candidate is unsafe
- it remains non-invasive and is not yet wired into runtime behavior

The grounded demo utility is the current end-to-end inspection tool:
- it exercises `user message -> grounded result -> optional paraphrase validation -> final response`
- it outputs readable JSON for manual testing
- it does not alter the main runtime path

The repo also now carries a small fixture-based grounded demo regression suite:
- `inference/grounded_demo_regression_cases.yaml`
- `tests/test_grounded_demo_regression.py`

This protects a handful of high-risk grounded behaviors from accidental regressions
before any real paraphraser is introduced.

The repo also now includes a separate grounded paraphrase dataset foundation. Its role is
different from the original waiter SFT dataset:
- the original SFT dataset teaches waiter behavior end to end
- the grounded paraphrase dataset teaches safer rewording of canonical deterministic responses
- the grounded paraphrase scorer evaluates saved paraphrase outputs against those same grounding constraints before any runtime integration

The preferred next training notebook is therefore also separate:
- raw waiter SFT notebook for legacy/reference-only smoke-test comparisons
- grounded paraphraser notebook for canonical-response-to-safe-paraphrase training

## Current Architectural Decision
Do not move directly to a 4B raw-generation experiment as the main next bet.

Grounded generation should be implemented or at least prototyped first, and future model
experiments should compare:
- raw generation
- grounded or paraphrased generation built on deterministic structured results

## Planned Future Use
The current baseline and benchmark are designed to support later comparison between:
- the deterministic baseline
- a future grounded local model layer
- a future routing or model-selection layer
