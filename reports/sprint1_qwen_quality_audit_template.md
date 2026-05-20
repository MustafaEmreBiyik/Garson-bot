# Sprint 1 Pure Qwen Quality Audit Report (Template)

**Date**: [YYYY-MM-DD]
**Auditor**: [Name/CI]
**Target Model**: Qwen2.5-3B-Instruct + LoRA Waiter Adapter
**Hardware**: [e.g., Jetson Orin NX 16GB / RTX 4090 / CPU Mock]

## 1. Execution Command
```bash
# Example of the real audit command used for this report:
python -m robot_waiter_ai.evals.run_qwen_quality_audit \
  --eval-file robot_waiter_ai/evals/pure_qwen_restaurant_eval_200.jsonl \
  --output-file robot_waiter_ai/evals/pure_qwen_audit_results_YYYYMMDD.jsonl \
  --device cuda \
  --no-4bit  # (Or use 4-bit depending on hardware)
```

## 2. Infrastructure & Metadata
- **Backend**: `[e.g., qwen_lora_waiter]`
- **Device Used**: `[e.g., cuda:0]`
- **Torch DType**: `[e.g., float16 / bfloat16]`
- **4-bit Loading**: `[Enabled / Disabled]`
- **Dry Run Mode**: `[True / False]`

## 3. High-Level Metrics
- **Total Eval Records**: [e.g., 100]
- **Passed**: [e.g., 92]
- **Failed**: [e.g., 8]
- **Pass Rate**: [e.g., 92.0%]
- **Average Latency**: [e.g., 0.85 sec/turn]
- **Total Execution Time**: [e.g., 85.0 sec]

## 4. Failure Categories Analysis
| Category | Failures | Typical Failure Mode |
|---|---|---|
| Ask Price | [X] | [e.g., Model hallucinated a wrong price] |
| Ask Ingredient | [Y] | [e.g., Model omitted a key allergen] |
| Place Order | [Z] | [e.g., Model did not explicitly confirm] |
| Out of Menu | [W] | [e.g., Model hallucinated that the item exists] |
| Allergy | [V] | [e.g., Model failed to warn about gluten] |

## 5. Top 3 Worst Failures (Qualitative)
1. **[ID: pq_0XX]**:
   - User: `[Query]`
   - Expected: `[Expected Behavior]`
   - Actual: `[Actual Behavior]`
   - Risk: `[High/Medium/Low]`

2. **[ID: pq_0YY]**:
   - (Same format)

3. **[ID: pq_0ZZ]**:
   - (Same format)

## 6. Next Steps & Recommendations
- [e.g., Require stronger prompt grounding for out-of-menu items]
- [e.g., Adjust LoRA temperature or repetition penalty]
- [e.g., Ready for Sprint 2 Voice Integration]
