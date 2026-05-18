# Qwen Local Voice Demo Setup

This project has two browser voice demo backends:

- `deterministic`: the safe default and fallback
- `qwen`: optional local LLM mode for experiments

Deterministic mode remains the default. If local Qwen does not run on your Windows machine because of VRAM, `bitsandbytes`, `torch`, or driver issues, use the deterministic demo locally and test Qwen on Colab, Ubuntu, WSL2, or Jetson instead.

## Base Model vs LoRA Adapter

The LoRA adapter is not the full model.

- Base model: the original Qwen model weights and config
- LoRA adapter: the small fine-tuned delta that is applied on top of the base model

Offline/local Qwen requires both folders:

- `robot_waiter_ai/models/Qwen2.5-3B-Instruct/`
- `robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora/`

If you only have the LoRA adapter, the Qwen backend cannot run.

## Important PowerShell Note

Folder paths are not PowerShell commands.

This is wrong:

```powershell
robot_waiter_ai\models\Qwen2.5-3B-Instruct
```

Use `dir` to inspect a folder:

```powershell
dir .\robot_waiter_ai\models
dir .\robot_waiter_ai\models\Qwen2.5-3B-Instruct
dir .\robot_waiter_ai\models\qwen25_3b_waiter_v1_1_lora
```

## Recommended Windows Setup

Run these commands from the project root:

```powershell
cd C:\Users\Emre\Desktop\Garson-bot
```

Create the separate Python 3.10 LLM environment:

```powershell
py -3.10 -m venv .venv-llm
```

Install requirements:

```powershell
.\.venv-llm\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv-llm\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-llm\Scripts\python.exe -m pip install -r requirements-llm.txt
.\.venv-llm\Scripts\python.exe -m pip install huggingface_hub
```

Download the base model locally:

```powershell
.\.venv-llm\Scripts\python.exe -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Qwen/Qwen2.5-3B-Instruct', local_dir=r'robot_waiter_ai\models\Qwen2.5-3B-Instruct', local_dir_use_symlinks=False)"
```

If you want the scripted version, run:

```powershell
.\scripts\setup_qwen_local_windows.ps1
```

## Verify Local Model Files

```powershell
.\scripts\check_qwen_model_files.ps1
```

## Text Test

```powershell
.\.venv-llm\Scripts\python.exe -m robot_waiter_ai.inference.qwen_lora_waiter --base-model-path robot_waiter_ai\models\Qwen2.5-3B-Instruct --adapter-path robot_waiter_ai\models\qwen25_3b_waiter_v1_1_lora --message "2 ayran istiyorum" --no-4bit
```

Notes:

- `--no-4bit` is useful on Windows when `bitsandbytes` does not work
- `--no-4bit` may need more RAM or VRAM
- if loading still fails, that is an environment/runtime limitation, not a dataset or training failure

## Browser Voice Demo with Qwen

```powershell
.\.venv-llm\Scripts\python.exe -m robot_waiter_ai.demo.voice_web_demo --port 8001 --backend qwen --qwen-base-model-path robot_waiter_ai\models\Qwen2.5-3B-Instruct --qwen-adapter-path robot_waiter_ai\models\qwen25_3b_waiter_v1_1_lora --no-4bit
```

Then open:

```text
http://localhost:8001
```

## Safe Fallback

If Qwen local mode is too heavy for the current Windows machine, keep using the deterministic backend:

```powershell
python -m robot_waiter_ai.demo.voice_web_demo
```

That mode is still the default and should keep working even if Qwen local setup is incomplete.
