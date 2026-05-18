# Experiment Results

## Summary
Two Google Colab smoke-test fine-tuning runs were completed and scored with
`generated_output_adapter.py` against the same 17-case benchmark.

The training pipeline worked in both runs, but response quality stayed far below the
deterministic baseline.

## Comparison Table

| Model | Total Cases | Passed | Failed | Pass Rate |
|---|---:|---:|---:|---:|
| `Qwen/Qwen3-0.6B` | 17 | 4 | 13 | 23.53% |
| `Qwen/Qwen3-1.7B` | 17 | 5 | 12 | 29.41% |

## Key Observations
- `Qwen/Qwen3-1.7B` improved only slightly over `Qwen/Qwen3-0.6B`.
- Model scaling alone did not solve the core task requirements.
- Both models produced natural-sounding fragments in some cases, but they remained weak on
  grounded restaurant behavior.
- The deterministic baseline is still the only currently acceptable main waiter assistant.

## Failed Case Patterns

### Menu Faithfulness
- The generated models hallucinated unsupported items such as pizza and hamburger.
- The 1.7B run still claimed pizza was available and implied hamburger ordering was valid.
- Menu-category answers were not reliably grounded in the actual YAML menu structure.

### Exact Prices
- Price handling remained unsafe.
- The 1.7B run gave `Ayran` as `15 TL` instead of the menu-grounded `45 TL`.
- This shows that learned generation cannot currently be trusted as the source of truth for prices.

### Order-State Language
- Add, remove, clear, summarize, and confirm responses often missed benchmark-critical wording.
- Common misses included:
  - missing `Ekledim`
  - missing `Çıkardım`
  - missing `Toplam`
  - missing `MVP/demo`
  - weak empty-order confirmation handling

### Allergy Caution
- Both runs were too soft or too vague on allergy safety.
- They often avoided the stronger deterministic caution style and did not reliably preserve
  `Alerji` plus `teyit`.

### Off-Topic Refusal
- Both runs failed the off-topic refusal requirement.
- Instead of preserving a restaurant-scope refusal, they answered the unrelated poetry request.

## Interpretation
These results suggest the problem is not only model size.

The failure patterns are concentrated in places where the assistant must:
- stay anchored to structured menu data
- preserve exact order state
- keep safety wording intact
- refuse unsupported or off-topic actions

Those are better handled by deterministic logic than by unconstrained raw generation.

## Conclusion
Neither `Qwen/Qwen3-0.6B` nor `Qwen/Qwen3-1.7B` is currently acceptable as the main waiter
assistant.

The correct next direction is not immediate scale-up to a 4B model. The next direction is
to prototype grounded generation so future model usage is constrained by deterministic
menu, order, and safety logic.
