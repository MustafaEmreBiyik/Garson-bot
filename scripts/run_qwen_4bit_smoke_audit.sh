#!/usr/bin/env bash

# run_qwen_4bit_smoke_audit.sh
# Safety‑checked wrapper to execute a small real 4‑bit smoke audit on a CUDA‑enabled device.
# It validates the environment, checks model/adapter paths, creates a *category‑balanced* subset,
# and runs the audit.

set -euo pipefail

# --- Configuration ----------------------------------------------------------
REPO_ROOT="$(git rev-parse --show-toplevel)"
BASE_MODEL_DIR="$REPO_ROOT/robot_waiter_ai/models/Qwen2.5-3B-Instruct"
LORA_ADAPTER_DIR="$REPO_ROOT/robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora"
EVAL_FILE="$REPO_ROOT/robot_waiter_ai/evals/pure_qwen_restaurant_eval_200.jsonl"
SUBSET_FILE="$REPO_ROOT/reports/smoke_subset.jsonl"
OUTPUT_JSONL="$REPO_ROOT/reports/qwen_lora_v1_4bit_smoke_outputs.jsonl"
PYTHON="python3"

# --- Helper functions -------------------------------------------------------
function err() {
  echo "[ERROR] $*" >&2
  exit 1
}

# --- 1. Ensure we are inside the repository --------------------------------
cd "$REPO_ROOT"

# --- 2. Optional: abort if there are uncommitted changes ---------------------
if [[ -n $(git status --short) ]]; then
  echo "[WARN] Uncommitted changes detected. Continue? (y/N)"
  read -r answer
  [[ "$answer" == "y" || "$answer" == "Y" ]] || err "Aborted due to pending changes."
fi

# --- 3. Validate CUDA availability ------------------------------------------
if ! $PYTHON - <<'PY'
import torch, sys
sys.exit(0 if torch.cuda.is_available() else 1)
PY
then
  err "CUDA not available. This script must run on a GPU/Jetson machine."
fi

echo "[INFO] CUDA available."

# --- 4. Verify model and adapter directories exist --------------------------
[[ -d "$BASE_MODEL_DIR" ]] || err "Base model directory not found: $BASE_MODEL_DIR"
[[ -d "$LORA_ADAPTER_DIR" ]] || err "LoRA adapter directory not found: $LORA_ADAPTER_DIR"

echo "[INFO] Model and adapter directories verified."

# --- 5. Verify the eval file exists -----------------------------------------
[[ -f "$EVAL_FILE" ]] || err "Eval file not found: $EVAL_FILE"

echo "[INFO] Eval file found: $EVAL_FILE"

# --- 6. Create a category‑balanced subset (default 3 per category) -----------
$PYTHON scripts/generate_smoke_subset.py \
  --source "$EVAL_FILE" \
  --dest "$SUBSET_FILE" \
  --max-per-category 3

echo "[INFO] Created balanced subset at $SUBSET_FILE"

# --- 7. Run the real 4‑bit smoke audit --------------------------------------
CMD="$PYTHON -m robot_waiter_ai.evals.run_qwen_quality_audit \
  --eval-file \"$SUBSET_FILE\" \
  --output-file \"$OUTPUT_JSONL\" \
  --device cuda"

echo "[INFO] Executing real 4‑bit smoke audit:"
echo "   $CMD"

# Execute the audit (set -e will abort on failure)
eval $CMD

echo "[SUCCESS] Smoke audit completed. Results saved to $OUTPUT_JSONL"

# End of script
