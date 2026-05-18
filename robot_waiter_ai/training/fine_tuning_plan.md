# Fine-Tuning Experiment Plan

## Goal
The next model-oriented step is no longer just "train a slightly larger model." The goal
is to improve Turkish waiter dialogue while keeping deterministic control over menu data,
order state, and safety behavior.

The deterministic baseline remains the reference system. Any learned model should be
compared against that baseline rather than treated as a replacement by default.

## Current Assets
- 350 hand-authored Turkish seed dialogue examples in `datasets/raw/seed_dialogues.yaml`
- `waiter_sft_train.jsonl` with 298 records
- `waiter_sft_valid.jsonl` with 52 records
- `dataset_validator.py` for structural validation
- `dataset_builder.py` for JSONL generation with deterministic shuffling before split
- `evaluation_cases.yaml` benchmark cases
- `eval_runner.py` for deterministic baseline evaluation
- `generated_output_adapter.py` for scoring saved model outputs against the same benchmark
- `evals/experiment_results.md` for learned-model smoke-test outcomes
- `inference/grounded_generation_plan.md` for the next architecture direction
- A deterministic runtime baseline that already passes the current benchmark

## What Has Happened So Far
- The first `Qwen/Qwen3-0.6B` Colab smoke test completed end to end
- The second `Qwen/Qwen3-1.7B` Colab smoke test also completed
- The training pipeline worked and adapter outputs were exported
- Generated outputs were scored through `generated_output_adapter.py`
- `Qwen/Qwen3-0.6B` scored `4/17` for `23.53%`
- `Qwen/Qwen3-1.7B` scored `5/17` for `29.41%`
- The workflow is validated, but raw generated quality is still too weak

## Current Conclusion
The main problem is not only model size.

The smoke-test failures show that raw generation remains weak on:
- menu faithfulness
- exact prices
- order-state wording and integrity
- allergy caution
- off-topic refusal

This means the next step should not be blind escalation to a larger model. It should be a
grounded-generation design that keeps deterministic business logic as the source of truth.

## Approved Training Environment
The first real training environment is:
- Google Colab GPU runtime

Why this remains appropriate:
- avoids adding heavy ML dependencies to the local repository
- keeps the workstation setup lightweight
- is sufficient for LoRA or QLoRA smoke tests

Jetson Orin NX remains:
- a future inference target
- a future deployment target
- not the first training machine

## Current Model Sequence Status
Completed smoke tests:
- `Qwen/Qwen3-0.6B`
- `Qwen/Qwen3-1.7B`

Planning note:
- do not move to Qwen3 4B yet
- grounded generation should be implemented or at least prototyped first

Future model experiments should evaluate both:
- raw generation
- grounded or paraphrased generation built on deterministic structured results

## Why The Dataset Was Expanded
The dataset was expanded after the first smoke test to target benchmark-critical failures:
- add-item responses with `Ekledim`
- remove-item responses with `Çıkardım`
- clear-order responses with `Siparişiniz temizlendi`
- price responses with exact `TL` values
- summaries and confirmations with `Toplam` and `MVP/demo`
- empty-order safety handling with `aktif bir siparişiniz görünmüyor` and `Önce`
- recommendation/category wording with `Öneri` and `Kategori`
- allergy caution with `Alerji` and `teyit`
- off-topic refusal with `yardımcı olamıyorum`
- unsupported menu requests through `unavailable_item`

That expansion improved the dataset, but the 1.7B result shows that dataset growth alone
is still not enough to make raw generation trustworthy for core waiter logic.

## Training Objective
- Training type: supervised fine-tuning
- Input: system instruction plus user message
- Target output: `assistant_response`
- Preserve cautious allergy behavior
- Preserve the restaurant waiter role
- Avoid inventing menu items or unsupported restaurant capabilities
- Strengthen response-style consistency on benchmark-critical wording

## Grounded Paraphraser Track
The next preferred training objective is no longer a raw end-to-end waiter brain.

Grounded paraphraser objective:
- input:
  - `user_message`
  - `canonical_response`
  - `must_preserve_terms`
  - `must_not_introduce`
- target:
  - `safe_paraphrase`

Why this track is now preferred:
- deterministic menu, order, and safety logic remain the source of truth
- the model is trained to improve Turkish phrasing, not to invent business facts
- held-out paraphraser outputs can be scored directly with `grounded_paraphrase_output_scorer.py`

Current grounded paraphrase assets:
- `grounded_paraphrase_seed.yaml`: 252 examples
- `grounded_paraphrase_train.jsonl`: 215 records
- `grounded_paraphrase_valid.jsonl`: 37 records
- `grounded_paraphrase_valid_reference.jsonl`: held-out scorer reference
- `grounded_paraphrase_valid_output_template.jsonl`: fill-ready output template
- `evals/generated_grounded_paraphrase_qwen3_0_6b_smoke.jsonl`: expected repo path for a Colab smoke-test output file before local scoring

The dedicated first notebook for this track should be:
- `notebooks/colab_grounded_paraphraser_qwen3_0_6b_smoke_test.ipynb`

## Evaluation Protocol
1. Record the deterministic baseline result with the existing evaluation runner.
2. Evaluate raw generated outputs against the benchmark.
3. Evaluate grounded or paraphrased outputs against the same benchmark once prototyped.
4. Compare:
   - pass rate
   - safety behavior
   - menu faithfulness
   - price accuracy
   - Turkish naturalness
5. Manually inspect failures rather than relying only on training loss.

## Risks
- Overfitting because the dataset is still relatively small
- Hallucinated menu items despite added unavailable-item coverage
- Unsafe allergy responses
- Response-style overfitting to benchmark phrases
- Raw generated models staying weak even as parameter count increases
- Evaluation benchmark still being too small to fully judge model behavior

## Key Planning Decision
Do not treat the 4B class as the immediate next fix.

Implementing or prototyping grounded generation is a higher-priority step because the
observed failures are concentrated in deterministic business-logic areas rather than in
pure linguistic fluency alone.

## Proposed Next Implementation Steps
1. Keep the deterministic baseline as the trusted runtime reference
2. Design the structured action/result contract for grounded generation
3. Prototype an optional LLM paraphraser with deterministic fallback
4. Evaluate future models in both raw and grounded modes
5. Revisit the 4B class only after grounded generation has been implemented or at least prototyped
