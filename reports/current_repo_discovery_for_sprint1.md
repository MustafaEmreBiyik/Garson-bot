# Repository Discovery & Sprint 1 Preparation Report

This report documents the status of the `robot_waiter_ai / Garson-bot` repository to prepare for Sprint 1.

---

## 1. What Is Currently Implemented?

*   **Deterministic Dialogue Manager (`robot_waiter_ai/assistant/dialogue_manager.py`)**:
    *   Handles Turkish user intent matching, order tracking (add/remove/clear/update/summarize), recommendations, price inquiries, ingredient details, and allergy warnings.
    *   Utilizes a local menu layout from `robot_waiter_ai/data/menu.yaml` and restaurant metadata from `robot_waiter_ai/data/restaurant_info.yaml`.
*   **Qwen LoRA Waiter Backend (`robot_waiter_ai/inference/qwen_lora_waiter.py`)**:
    *   Provides a PyTorch-based inference class (`QwenLoraWaiterBackend`) that loads the Qwen base model and PEFT LoRA adapter.
    *   Supports loading in 4-bit (via `bitsandbytes` on CUDA-enabled Linux) or FP32 fallback on CPU, custom system prompts, and dialog history.
    *   Features a CLI script wrapper to run text generation tests.
*   **Web-Based Voice Demo (`robot_waiter_ai/demo/voice_web_demo.py` & `.html`)**:
    *   A web interface running on `0.0.0.0:8000` that captures voice input via Web Speech API, passes it to the selected backend (`deterministic` or `qwen`), and plays back responses using Speech Synthesis (TTS).
*   **Hybrid NLU Orchestrator (`robot_waiter_ai/inference/hybrid_orchestrator.py`)**:
    *   An experimental orchestrator designed to parse queries using NLU schemas, matching categories/items, and redirecting unsupported/off-topic questions to deterministic fallbacks.
*   **Evaluation & Diagnostics Suite (`robot_waiter_ai/evals/`)**:
    *   Deterministic test runner (`eval_runner.py`) using YAML-defined test cases (`evaluation_cases.yaml`).
    *   System hardware diagnostics (`check_qwen_gpu_runtime.py`).
    *   Evaluation scripts for Qwen: `run_qwen_menu_context_probe.py` and `run_qwen_waiter_feature_probe.py`.

---

## 2. Qwen Base Model and LoRA Adapter Locations

Both model components exist locally in the repository and do not require downloading:
*   **Qwen Base Model**: Located at [Qwen2.5-3B-Instruct](file:///home/emre/Masa%C3%BCst%C3%BC/Garson-bot/robot_waiter_ai/models/Qwen2.5-3B-Instruct) (includes config, tokenizer, and safetensors split files).
*   **LoRA Adapter**: Located at [qwen25_3b_waiter_v1_1_lora](file:///home/emre/Masa%C3%BCst%C3%BC/Garson-bot/robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora) (contains `adapter_model.safetensors` and PEFT `adapter_config.json`).

---

## 3. Existing Scripts Index

| Category | Script Name / Path | Purpose |
|---|---|---|
| **Qwen Inference** | [qwen_lora_waiter.py](file:///home/emre/Masa%C3%BCst%C3%BC/Garson-bot/robot_waiter_ai/inference/qwen_lora_waiter.py) | CLI text prompt runner and backend integration class. |
| **Voice Demo** | [voice_web_demo.py](file:///home/emre/Masa%C3%BCst%C3%BC/Garson-bot/robot_waiter_ai/demo/voice_web_demo.py) | Local web server binding to port 8000 supporting deterministic and Qwen backends. |
| **Model Verification** | [check_qwen_model_files.ps1](file:///home/emre/Masa%C3%BCst%C3%BC/Garson-bot/scripts/check_qwen_model_files.ps1) | PowerShell script checking base/LoRA config and safetensors files. |
| **Diagnostics** | [check_qwen_gpu_runtime.py](file:///home/emre/Masa%C3%BCst%C3%BC/Garson-bot/robot_waiter_ai/evals/check_qwen_gpu_runtime.py) | Checks platform, PyTorch installation, CUDA availability, VRAM, and Jetson parameters. |
| **Dataset Building** | [dataset_builder.py](file:///home/emre/Masa%C3%BCst%C3%BC/Garson-bot/robot_waiter_ai/training/dataset_builder.py) | Compiles train/valid JSONL files from raw seed dialogue configs. |
| **Fine-Tuning Skel** | [train_lora.py](file:///home/emre/Masa%C3%BCst%C3%BC/Garson-bot/robot_waiter_ai/training/train_lora.py) | Config validation skeleton supporting `--dry-run` only; training logic is not yet implemented. |
| **Evaluation Probes** | [run_qwen_menu_context_probe.py](file:///home/emre/Masa%C3%BCst%C3%BC/Garson-bot/robot_waiter_ai/evals/run_qwen_menu_context_probe.py)<br>[run_qwen_waiter_feature_probe.py](file:///home/emre/Masa%C3%BCst%C3%BC/Garson-bot/robot_waiter_ai/evals/run_qwen_waiter_feature_probe.py) | Generates multi-turn context and single-turn feature test dialogues to output files. |
| **Reports** | [mock_qwen_50_soru_test_sonuc.md](file:///home/emre/Masa%C3%BCst%C3%BC/Garson-bot/robot_waiter_ai/evals/archive/mock_qwen_50_soru_test_sonuc.md)<br>[experiment_results.md](file:///home/emre/Masa%C3%BCst%C3%BC/Garson-bot/robot_waiter_ai/evals/experiment_results.md) | Quality logs detailing simulated 50-question outputs and past Colab run scores. |

---

## 4. Current Test Status (Passes & Failures)

Running the test suite yields **63 failures and 200 passes** out of 263 tests:
*   **Root Cause**: The file `robot_waiter_ai/data/menu.yaml` was recently updated with new category layout, IDs (e.g. `s1` -> `soup_1`, `b1` -> `drink_1`), and more descriptive item names (e.g. `Ayran` -> `Yayık Ayran`, `Domates Çorbası` -> `Kremalı Mantar Çorbası`).
*   **Affected Code Areas**:
    1.  **Mention Matching**: `MenuKnowledge.find_mentions()` relies on substring matching (`normalize_text(item.name) in normalized_text`). When `Ayran` became `Yayık Ayran`, a user saying "ayran" no longer matched the menu item since "yayik ayran" is not in "ayran". Thus, intent matching and order updates broke.
    2.  **Dataset Out of Sync**: The raw training/eval files (such as `datasets/raw/seed_dialogues.yaml`) still contain the old item names (Domates Çorbası, Sebzeli Makarna, Etli Güveç, Ayran) and prices, causing failures in scripts/tests validating dataset builder inputs.
    3.  **Strict Assertions**: Parametrized tests specifically assert older outputs like `"Ayran 45.00 TL."`, which mismatch the modified responses.
    4.  **Prompt Divergence**: `test_qwen_prompt_includes_do_not_invent_guardrails` fails because prompt templates in `qwen_lora_waiter.py` were revised, removing specific terms checked by the test suite (like "uydurma").

---

## 5. Missing Elements for Sprint 1 Quality Audit

1.  **Non-Simulated Model Output Evaluation**: [mock_qwen_50_soru_test_sonuc.md](file:///home/emre/Masa%C3%BCst%C3%BC/Garson-bot/robot_waiter_ai/evals/archive/mock_qwen_50_soru_test_sonuc.md) contains mock/simulated outputs. A real evaluation must be executed and logged.
2.  **Actual LoRA Training Pipeline**: `train_lora.py` lacks actual PEFT/SFT Trainer routines; it only checks configuration parameters.
3.  **Hardware Audit**: The current machine is a CPU-only environment (`torch.cuda.is_available(): False`), so local 4-bit quantization or GPU performance cannot be benchmarked here. Benchmarks must occur on the Jetson Orin NX.
4.  **Synchronized Dataset**: The raw dataset files must be rewritten to match the new item names and prices of `menu.yaml`.

---

## 6. Safest Next Implementation Task

*   **Option A (Align Menu via Aliases)**: Introduce an alias mapping list inside `MenuItem` or `MenuKnowledge` (e.g. mapping "ayran" as an alias for "Yayık Ayran"). This preserves backward compatibility for both user inputs and test assertions, restoring the 63 broken tests immediately.
*   **Option B (Synchronize Datasets & Tests)**: Re-align `seed_dialogues.yaml` and the test suite assertions to use the new IDs and item names (`drink_1`, `Yayık Ayran`, etc.) and regenerate SFT training splits using `dataset_builder.py`.
*   **Option C (Implement Training Loop)**: Fill out the training logic in `robot_waiter_ai/training/train_lora.py` using Hugging Face `SFTTrainer` or `Trainer` so the model can be retrained.
