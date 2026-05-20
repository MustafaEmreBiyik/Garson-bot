---
## Jetson / GPU Qwen 4‑bit Smoke‑Audit Runbook

### Purpose
Execute a **small real 4‑bit smoke audit** of the `Qwen2.5‑3B‑Instruct` + LoRA waiter model on a CUDA‑enabled device (Jetson Orin NX or any NVIDIA GPU). This is a quick sanity‑check, not a full benchmark.

---

### Preconditions & Checklist
| ✅ | Requirement |
|---|---|
| ✅ | **Hardware**: Jetson Orin NX **or** Linux machine with an NVIDIA GPU and CUDA installed |
| ✅ | **CUDA**: `torch.cuda.is_available()` must be `True` |
| ✅ | **Repo**: `robot_waiter_ai` cloned/pulled on the target machine |
| ✅ | **Python env**: Virtual environment with `requirements-llm.txt` (and `requirements.txt`) installed |
| ✅ | **Base model**: `robot_waiter_ai/models/Qwen2.5-3B-Instruct` directory present |
| ✅ | **LoRA adapter**: `robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora` directory present |
| ✅ | **Eval dataset**: `robot_waiter_ai/evals/pure_qwen_restaurant_eval_200.jsonl` present |

---

### Commands
```bash
# 1. Navigate to repo root
cd /path/to/robot_waiter_ai   # adjust as needed

# 2. (Optional) Verify a clean git state
git status --short

# 3. Run the full test suite – ensures the codebase is healthy
pytest -q --basetemp robot_waiter_ai/.pytest_tmp

# 4. Confirm CUDA availability
python - <<'PY'
import torch
print('CUDA available:', torch.cuda.is_available())
PY

# 5. Verify model & LoRA directories exist
if [ ! -d "robot_waiter_ai/models/Qwen2.5-3B-Instruct" ]; then echo "❌ Base model missing"; exit 1; fi
if [ ! -d "robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora" ]; then echo "❌ LoRA adapter missing"; exit 1; fi

# 6. Optional dry‑run (CPU‑safe) to sanity‑check the runner
python -m robot_waiter_ai.evals.run_qwen_quality_audit \
  --dry-run \
  --eval-file robot_waiter_ai/evals/pure_qwen_restaurant_eval_200.jsonl \
  --output-file reports/dry_run_smoke.jsonl

# 7. Create a small, *category‑balanced* subset (≈ 15 records)
python scripts/generate_smoke_subset.py \
  --source robot_waiter_ai/evals/pure_qwen_restaurant_eval_200.jsonl \
  --dest reports/smoke_subset.jsonl \
  --max-per-category 3   # up to 3 records per category

# 8. Run the real 4‑bit smoke audit (GPU)
python -m robot_waiter_ai.evals.run_qwen_quality_audit \
  --eval-file reports/smoke_subset.jsonl \
  --output-file reports/qwen_lora_v1_4bit_smoke_outputs.jsonl \
  --device cuda   # 4‑bit loading is default; omit --no-4bit
```

---

### Expected Output Files
| File | Description |
|---|---|
| `reports/qwen_lora_v1_4bit_smoke_outputs.jsonl` | One JSON‑L line per evaluated case (model response, latency, pass/fail). |
| `reports/qwen_lora_v1_4bit_smoke_report.md` | Markdown report (based on the sprint‑1 template) summarising pass rate, latency, and any failure categories. |

---

### OOM / “Killed 137” Guidance
* **Do NOT** automatically add `--no-4bit`; FP16 generally uses **more** memory than 4‑bit. If OOM occurs:
  1. Reduce the number of cases (`--max-per-category 1` or edit `reports/smoke_subset.jsonl`).
  2. Close other GPU‑intensive processes; monitor memory with `nvidia‑smi`.
  3. As a last resort, retry with `--no-4bit` **only** if the 4‑bit loader itself crashes due to library issues.

---

### Interpreting Results
| Metric | What to Observe |
|---|---|
| **Pass Rate** | Reasonable pass‑rate (no strict threshold – this is a sanity check). |
| **Average Latency** | Record the value; avoid assuming a target like “≤ 1 s/turn” until measured on your hardware. |
| **Broken Turkish / Unexpected Characters** | Any non‑Turkish glyphs indicate tokenisation/quantisation problems. |
| **Over‑Refusal** | Model refuses valid in‑menu queries – may need safety‑filter tuning. |
| **Menu Hallucination** | Model mentions items not present in `menu.yaml`. |

---

### Completion Report Template (Markdown)
Copy the following into `reports/qwen_lora_v1_4bit_smoke_report.md` and fill after the run:

```markdown
# Qwen 4‑bit Smoke Audit – Jetson/GPU Run

**Date**: YYYY‑MM‑DD
**Auditor**: <Name / CI>

## Execution Summary
- **Status**: PASS / BLOCKED / FAILED
- **Device**: Jetson Orin NX / NVIDIA RTX …
- **CUDA Available**: True / False
- **Base Model Path**: robot_waiter_ai/models/Qwen2.5-3B-Instruct
- **LoRA Adapter Path**: robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora
- **Command Run**:
  ```bash
  python -m robot_waiter_ai.evals.run_qwen_quality_audit \
    --eval-file reports/smoke_subset.jsonl \
    --output-file reports/qwen_lora_v1_4bit_smoke_outputs.jsonl \
    --device cuda
  ```
- **Cases Run**: N (≈ 15)
- **Output JSONL**: `reports/qwen_lora_v1_4bit_smoke_outputs.jsonl`

## Metrics
- **Total Records**: X
- **Passed**: Y (Z %)
- **Failed**: W (V %)
- **Average Latency**: A sec/turn

## Failure Analysis (examples)
| Category | Record ID | User Message | Model Response | Issue |
|---|---|---|---|---|
| Over‑Refusal | pq_012 | "Yayık ayran ne kadar?" | "Üzgünüm, yardımcı olamıyorum." | Refused in‑menu query |
| Hallucination | pq_045 | "Şalgam suyu var mı?" | "Evet, menümüzde şalgam suyu var." | Item not in menu |
| Broken Token | pq_078 | "Merhaba" | "一一" | Non‑Turkish characters |

## OOM / Killed 137
- **Observed?** Yes / No
- **Details**: (e.g., memory usage before kill, number of cases processed)

## Recommendations
- **If PASS**: Proceed to the full 100‑case audit.
- **If FAIL**: Review failure categories, consider adjusting `--max-per-category` or investigating memory usage.
```

---

### Helper Script Usage
The wrapper script `scripts/run_qwen_4bit_smoke_audit.sh` performs all safety checks, creates the balanced subset using `generate_smoke_subset.py`, and then runs the audit with the exact command shown in step 8. Execute it from the repository root:
```bash
bash scripts/run_qwen_4bit_smoke_audit.sh
```
It will abort with a clear error message if CUDA is unavailable or required model directories are missing.

---

### Final Notes
* This runbook is intended for **validation only** – run on a Jetson or GPU before any larger benchmark.
* No model files are downloaded or modified by the scripts.
* Ensure the virtual environment matches the `requirements-llm.txt` specifications.
---
