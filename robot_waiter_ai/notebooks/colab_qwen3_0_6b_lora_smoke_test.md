# Colab Qwen3 0.6B LoRA Smoke Test

## A. Purpose
This document is the Markdown-first notebook plan for the first real supervised
fine-tuning smoke test in Google Colab.

This is not production training.

The goal is to validate the end-to-end training pipeline:
- project access inside Colab
- dataset loading
- dependency installation in Colab only
- conservative LoRA or QLoRA wiring
- adapter/checkpoint saving
- benchmark-output generation for later scoring

The target model for the first smoke test is:
- primary: `Qwen/Qwen3-0.6B`

Fallback order after this first attempt:
- `Qwen/Qwen3-1.7B` if `Qwen/Qwen3-0.6B` is too weak
- Qwen3 4B instruct/post-trained class only after the smaller smoke test succeeds

## B. Runtime Setup
Use a Google Colab GPU runtime.

Notes:
- GPU availability varies by Colab session and plan
- available VRAM may change from run to run
- a run may need small parameter adjustments if the allocated GPU is weaker than expected

Recommended first runtime check cell:

```python
!nvidia-smi
```

Recommended environment check cell:

```python
import platform
import sys

print("Python:", sys.version)
print("Platform:", platform.platform())
```

If no GPU is visible, stop and switch to a GPU runtime before continuing.

## C. Project Upload Options
Use one of these two project access options in Colab.

### Option 1. Upload Project Zip Manually To Colab
1. Create a zip of the current project on the local machine.
2. Upload it to the Colab session.
3. Extract it into `/content/Garson-bot`.
4. Change into the project directory.

Draft cells:

```python
from google.colab import files
uploaded = files.upload()
```

```python
!mkdir -p /content/Garson-bot
!unzip -q Garson-bot.zip -d /content/Garson-bot
%cd /content/Garson-bot
```

### Option 2. Mount Google Drive And Use Project Folder There
1. Put the project folder or a zip in Google Drive.
2. Mount Drive in Colab.
3. Work from the Drive copy directly, or copy it into `/content` for speed.

Draft cells:

```python
from google.colab import drive
drive.mount("/content/drive")
```

```python
%cd /content/drive/MyDrive/Garson-bot
```

Optional faster-working copy:

```python
!cp -r /content/drive/MyDrive/Garson-bot /content/Garson-bot
%cd /content/Garson-bot
```

## D. Dataset Preparation
Use the existing processed dataset files:
- `robot_waiter_ai/datasets/processed/waiter_sft_train.jsonl`
- `robot_waiter_ai/datasets/processed/waiter_sft_valid.jsonl`

The notebook should verify file paths, print the first few records, and confirm the
train/valid counts before any training library setup is trusted.

Draft cells:

```python
from pathlib import Path

train_path = Path("robot_waiter_ai/datasets/processed/waiter_sft_train.jsonl")
valid_path = Path("robot_waiter_ai/datasets/processed/waiter_sft_valid.jsonl")

print("Train exists:", train_path.exists(), train_path)
print("Valid exists:", valid_path.exists(), valid_path)
```

```python
import json

def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

train_rows = load_jsonl(train_path)
valid_rows = load_jsonl(valid_path)

print("Train count:", len(train_rows))
print("Valid count:", len(valid_rows))
```

```python
for row in train_rows[:3]:
    print(json.dumps(row, ensure_ascii=False, indent=2))
    print("-" * 80)
```

Expected current counts:
- train: `131`
- valid: `23`

Quick structure checks:
- each record should contain `messages`
- each conversation should end in an `assistant` response
- `metadata.id` should exist for traceability

## E. Dependencies
These are draft Colab install cells only. They are not to be run locally in this repo task.

Core future dependencies:
- `transformers`
- `datasets`
- `peft`
- `trl`
- `accelerate`
- `bitsandbytes` if QLoRA is used
- `sentencepiece` if needed

Draft install cell for a QLoRA path:

```python
!pip install -q -U transformers datasets peft trl accelerate bitsandbytes sentencepiece
```

If LoRA is used without 4-bit quantization, `bitsandbytes` may be omitted:

```python
!pip install -q -U transformers datasets peft trl accelerate sentencepiece
```

## F. Model
Primary first smoke-test model:
- `Qwen/Qwen3-0.6B`

Reason:
- smallest conservative option in the chosen family
- suitable for first pipeline validation
- lower cost and faster iteration than larger candidates

Fallback:
- use `Qwen/Qwen3-1.7B` only if the `0.6B` smoke test is clearly too weak

Later-only fallback:
- consider a Qwen3 4B instruct/post-trained class only after the smaller smoke test succeeds

Do not include any Hugging Face access token in this file.

## G. Training Approach
Training style:
- supervised fine-tuning
- LoRA or QLoRA

Conservative first-run approach:
- small epoch count
- low learning rate
- small batch size
- gradient accumulation
- adapter-only saving

Suggested first smoke-test configuration:

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

The notebook should keep the current dataset schema unchanged and use the existing
chat-style `messages` structure.

Planned workflow:
1. load tokenizer
2. load model in LoRA or QLoRA-compatible mode
3. convert `messages` into model text using the tokenizer chat template when available
4. train for a small smoke-test run
5. save adapter-only artifacts

## H. Evaluation After Training
After training, the notebook should generate responses for all cases in
`robot_waiter_ai/evals/evaluation_cases.yaml`.

Save outputs in JSONL format with:
- `case_id`
- `response`

Optional extra fields are acceptable because `generated_output_adapter.py` also supports:
- `backend_name`
- `metadata`

Target JSONL example:

```json
{"case_id": "eval_001", "response": "Merhaba, hos geldiniz."}
```

Planned workflow:
1. load evaluation cases
2. run generation for each `user` prompt
3. save outputs to JSONL
4. download or copy the JSONL file back into the repo workspace
5. score it with `generated_output_adapter.py`

Repo-side scoring command:

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.evals.generated_output_adapter --outputs path\to\generated_outputs.jsonl
```

## I. Safety And Honesty
This smoke-test workflow does not prove production readiness.

During review, specifically watch for:
- hallucinated menu items
- unsafe allergy answers
- broken waiter-role behavior
- weak Turkish naturalness
- benchmark regressions against the deterministic baseline

The deterministic baseline remains the reference system until a learned model earns trust.

## J. Expected Outputs
The first Colab smoke test should produce:
- adapter or checkpoint folder
- generated outputs JSONL for benchmark scoring
- training logs or trainer metrics
- short manual notes about observed strengths and failures

Recommended manual notes format:
- Colab date and GPU type
- model name
- LoRA or QLoRA
- whether training completed
- obvious hallucination or allergy issues
- benchmark score after repo-side evaluation

## Suggested Colab Cell Order
1. Runtime check
2. Upload or mount project
3. Verify dataset files and counts
4. Install dependencies in Colab
5. Define training config values
6. Load tokenizer and model
7. Load and format datasets
8. Run short LoRA or QLoRA training
9. Save adapter/checkpoint
10. Generate benchmark outputs JSONL
11. Copy or download outputs back to the repo
12. Score outputs with `generated_output_adapter.py` outside Colab

## Non-Goals In This Notebook Plan
- no local training from this repo task
- no model download from this repo task
- no architecture rewrite
- no dataset schema change
- no benchmark rewrite
- no FastAPI, ROS, speech runtime, database, or dashboard work
