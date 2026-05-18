# Colab Training Checklist

## Before Colab
- Confirm the project scope is still conversational Turkish waiter AI only.
- Confirm the first approved real training environment is Google Colab.
- Confirm the first smoke-test base model is `Qwen/Qwen3-0.6B`.
- Confirm fallback order remains `Qwen/Qwen3-1.7B`, then Qwen3 4B class only after a successful smaller smoke test.
- Confirm the local repository still avoids heavy ML dependencies.
- Regenerate and validate the dataset if the raw examples changed.
- Keep the deterministic baseline benchmark result recorded as the reference point.
- Review [colab_qwen3_0_6b_lora_smoke_test.md](/C:/Users/Emre/Desktop/Garson-bot/robot_waiter_ai/notebooks/colab_qwen3_0_6b_lora_smoke_test.md).
- Review [colab_qwen3_0_6b_lora_smoke_test.ipynb](/C:/Users/Emre/Desktop/Garson-bot/robot_waiter_ai/notebooks/colab_qwen3_0_6b_lora_smoke_test.ipynb).

## Inside Colab
- Switch Colab to a GPU runtime.
- Run `nvidia-smi` and note the GPU type.
- Upload the project zip or mount Google Drive and open the project folder.
- Verify `waiter_sft_train.jsonl` and `waiter_sft_valid.jsonl` exist.
- Print a few dataset records and confirm the schema looks unchanged.
- Confirm current expected counts are 131 train and 23 valid records.
- Install dependencies in Colab only.
- Start with a conservative LoRA or QLoRA smoke-test configuration.
- Save adapter-only artifacts rather than aiming for a merged production model.
- Record brief notes about crashes, OOM issues, weak behavior, or obvious hallucinations.
- Save benchmark generations as `generated_outputs_qwen3_0_6b_smoke.jsonl`.

## After Training
- Confirm that training completed or note exactly where it failed.
- Save the adapter or checkpoint folder.
- Save tokenizer files if needed by the chosen flow.
- Save training logs or trainer metrics.
- Save a short manual notes file or text summary.
- Generate evaluation outputs as JSONL with `case_id` and `response`.
- Copy or download generated outputs back to the repository workspace.
- Preserve `backend_name` and `metadata` in the generated JSONL records.

## Evaluation
- Score the generated outputs with `robot_waiter_ai.evals.generated_output_adapter`.
- Compare results against the deterministic baseline rather than treating the trained model as the new default.
- Check for hallucinated menu items.
- Check for unsafe allergy answers.
- Check for Turkish waiter-role consistency.
- Review a small set of manual prompts in addition to benchmark scores.

## Rollback/Cleanup
- If the smoke test fails badly, keep the deterministic baseline as the active reference system.
- Do not change runtime dialogue logic based only on a weak smoke-test result.
- Delete incomplete or clearly bad Colab outputs if they would cause confusion.
- Preserve short notes about what failed so the next run can adjust only one or two variables at a time.
- Only move to `Qwen/Qwen3-1.7B` after documenting why `Qwen/Qwen3-0.6B` was insufficient.
