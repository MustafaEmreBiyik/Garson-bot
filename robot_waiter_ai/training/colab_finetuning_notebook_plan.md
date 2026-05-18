# Colab-First Fine-Tuning Notebook Plan

## Purpose
This document defines the first practical Google Colab workflow for supervised fine-tuning
of the Turkish waiter-assistant module.

This is a Colab-first plan and template guide only:
- no local heavy ML dependencies are added to this repo
- no model is downloaded locally
- no training is started from this repository environment
- the deterministic baseline remains the reference system

The first smoke-test target is:
- base model: `Qwen/Qwen3-0.6B`
- method: `qlora`
- environment: Google Colab GPU runtime

## Notebook Goals
The first notebook should help us do five things safely:
1. mount storage and prepare a Colab workspace
2. validate that the repo and processed datasets are present
3. install training libraries inside Colab only
4. run one conservative QLoRA smoke test
5. save artifacts for later evaluation with the existing benchmark harness

## Why Colab First
- avoids adding `torch`, `transformers`, `peft`, `trl`, or `bitsandbytes` locally
- gives us a fast path to test the training stack
- keeps the workstation repo lightweight
- lets us debug model formatting, trainer wiring, and checkpoint saving before thinking about deployment

## Recommended Notebook Structure

### 1. Header And Safety Notes
Include:
- project reminder: conversational Turkish waiter AI only
- non-goals: no navigation, no ROS, no robot control
- current dataset size and split counts
- warning that this is a smoke test, not a production training recipe

### 2. Runtime Check
Check:
- GPU presence
- Python version
- available VRAM if possible

If there is no GPU, stop early.

### 3. Workspace Setup
Preferred options:
- mount Google Drive for persistent outputs
- clone the repo into `/content/Garson-bot`
- switch into the repo root

Expected repo-relative files:
- `robot_waiter_ai/datasets/processed/waiter_sft_train.jsonl`
- `robot_waiter_ai/datasets/processed/waiter_sft_valid.jsonl`
- `robot_waiter_ai/evals/evaluation_cases.yaml`

### 4. Dataset Sanity Checks
Before installing the heavy stack, confirm:
- train file exists
- valid file exists
- line counts match expectation closely
- records include `messages`
- each conversation ends with an `assistant` turn

This keeps debugging simple if the Colab session starts from the wrong folder or an outdated repo copy.

### 5. Colab-Only Dependency Install
Install in Colab only:
- `torch`
- `transformers`
- `datasets`
- `accelerate`
- `peft`
- `trl`
- `bitsandbytes`

Optional:
- `sentencepiece`

Keep version pins conservative and easy to update.

## First Smoke-Test Configuration
Use conservative defaults for the first run:

```yaml
base_model_name_or_path: "Qwen/Qwen3-0.6B"
method: "qlora"
epochs: 3
learning_rate: 0.0002
batch_size: 2
gradient_accumulation_steps: 8
max_seq_length: 1024
lora_r: 16
lora_alpha: 32
lora_dropout: 0.05
eval_steps: 10
save_steps: 25
seed: 42
```

Notes:
- keep batch size small for Colab compatibility
- keep sequence length at `1024` for the first pass
- prefer adapter-only saving rather than a merged full model

## Data Formatting Strategy
The existing processed dataset already uses chat-style `messages`.

The notebook should:
1. load each JSONL record
2. extract the `messages` array
3. render it into model text with the tokenizer chat template when available
4. train on the resulting text field

Expected record shape:

```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "metadata": {
    "id": "example_id"
  }
}
```

## Minimal Training Flow
The first notebook should cover:
1. load tokenizer
2. load quantized base model for QLoRA
3. create LoRA config
4. load train and valid datasets
5. format records into training text
6. run `SFTTrainer`
7. save adapter checkpoints and tokenizer
8. run a few manual Turkish smoke prompts

## Manual Smoke Prompts
After training, manually inspect prompts like:
- `Merhaba`
- `Bir mercimek corbasi ve bir ayran alabilir miyim?`
- `Fistik alerjim var, ne onerirsiniz?`
- `Menude olmayan sushi var mi?`

Check for:
- Turkish fluency
- waiter-role consistency
- allergy caution
- no invented menu items

## Artifact Expectations
The notebook should save:
- adapter checkpoint directory
- tokenizer files if needed
- trainer state and metrics
- a small `smoke_generations.jsonl` file with prompt/response pairs

Recommended output root:
- `/content/drive/MyDrive/garsonbot_runs/run_001_qwen3_0p6b_smoke`

## Post-Training Evaluation Hand-Off
The existing repo benchmark should remain the scoring source of truth.

The notebook does not need to fully replace the local evaluation pipeline on day one.
Instead, it should prepare one of these hand-off paths:

### Option A
Generate a JSONL file with:
- `case_id`
- `response`

Then later score it with:

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.evals.generated_output_adapter --outputs path\to\generated_outputs.jsonl
```

### Option B
Add a later Colab cell that mirrors the same output schema and scoring logic.

For the first notebook version, Option A is enough.

## Success Criteria For Notebook V1
- runs in Colab without depending on local ML installs
- loads the repo dataset files successfully
- completes at least one short training run
- saves an adapter artifact
- produces a few Turkish sample generations
- leaves a clear path to benchmark scoring with existing repo tools

## Known Risks
- Colab GPU type may vary
- package versions may shift over time
- Qwen tokenizer or chat-template behavior may need adjustment
- tiny dataset may overfit quickly
- a very small model may still underperform the deterministic baseline

## Recommended Repo Artifacts
This plan pairs with:
- `colab_qwen3_smoke_test.ipynb`
- `training_config.example.yaml`
- `model_shortlist.md`
- `fine_tuning_plan.md`

## What This Plan Does Not Do Yet
- no claim that the notebook is production-ready
- no automated hyperparameter sweep
- no merged-model export workflow
- no Jetson deployment path
- no benchmark pass/fail claims for a learned model yet
