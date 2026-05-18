# Grounded Generation Plan

## Goal
Define a safer future model-usage strategy for GarsonBot so any learned model is
constrained by deterministic restaurant logic instead of being trusted as a raw answer
generator.

## Why Pure Generated Responses Are Unsafe
The first `Qwen/Qwen3-0.6B` and `Qwen/Qwen3-1.7B` smoke tests showed that pure generated
responses are unsafe for this task because they can:
- invent menu items that do not exist
- invent or distort prices
- lose exact order-state wording
- weaken allergy caution language
- answer off-topic requests instead of refusing them

In a waiter-assistant setting, those are not cosmetic failures. They are core trust and
safety failures.

## What Must Remain Deterministic
The following responsibilities should remain grounded in deterministic source-of-truth
logic:
- menu availability
- prices
- order add/remove/update/clear behavior
- order summary and order confirmation
- allergy caution behavior
- off-topic refusal

These must continue to come from structured runtime logic and project data files rather
than from free-form model recall.

## What The Model Can Safely Do
A future model can still be useful in a constrained role:
- paraphrase deterministic responses into more natural Turkish
- smooth tone and phrasing without changing facts
- handle polite small talk that stays inside restaurant scope
- improve wording variety while preserving exact structured content

This means the model should be treated as a controlled language layer, not as the main
business-logic layer.

## Proposed Architecture

```text
user input
  -> deterministic intent/menu/order/safety layer
  -> structured action/result
  -> optional LLM paraphraser
  -> final safety/grounding check
  -> final response
```

## Structured Action/Result Concept
The deterministic layer should produce a structured result that captures the trusted
facts, for example:
- detected intent
- matched menu items
- quantities
- total price
- safety flags
- whether the request is unsupported or off-topic
- canonical deterministic response

The optional LLM receives only that grounded result plus a constrained paraphrasing task.

The concrete schema now lives in:
- `robot_waiter_ai/inference/structured_result.py`
- `robot_waiter_ai/inference/grounded_result_builder.py`
- `robot_waiter_ai/inference/grounded_response_formatter.py`
- `robot_waiter_ai/inference/grounded_demo.py`

The first version is intentionally lightweight and standard-library only. It defines:
- `GroundedAction` for intent, entities, support state, and safety need
- `MenuGrounding` for matched items, unavailable items, prices, and categories
- `OrderGrounding` for order-action facts, item rows, totals, and demo-confirmation state
- `SafetyGrounding` for required safety terms and forbidden claims
- `GroundedResult` for the full deterministic result, canonical response, and paraphrase constraints

This schema prepares future grounded paraphrasing. It does not yet integrate an LLM or
change runtime behavior.

The first non-invasive builder prototype now:
- takes a user message
- derives a deterministic grounded intent/result
- includes a canonical deterministic response
- reuses the existing `DialogueManager` and menu/order logic where practical
- does not replace or rewrite the current runtime

The first non-invasive formatter prototype now:
- returns the canonical deterministic response by default
- accepts a paraphrase candidate only if grounding checks pass
- falls back to the canonical response when a candidate is unsafe
- can explain simple rejection reasons for future debugging

The first non-invasive grounded demo utility now:
- runs the full local grounded path for manual inspection
- builds a `GroundedResult`
- optionally validates a supplied paraphrase candidate
- returns the final grounded response plus debugging fields as JSON
- remains a manual/demo tool rather than a production runtime path

To protect this path against accidental drift, the repo now also includes small grounded
demo regression fixtures in:
- `robot_waiter_ai/inference/grounded_demo_regression_cases.yaml`

These fixtures lock a few critical grounded behaviors such as:
- unsupported item refusal
- allergy caution wording
- exact price preservation
- safe empty-order confirmation handling
- off-topic refusal

The repo now also includes a separate grounded paraphrase dataset foundation:
- `robot_waiter_ai/datasets/raw/grounded_paraphrase_seed.yaml`
- `robot_waiter_ai/training/grounded_paraphrase_validator.py`
- `robot_waiter_ai/training/grounded_paraphrase_builder.py`

This dataset is meant for a future constrained paraphraser, not for replacing the
deterministic source of truth. Each example pairs:
- user message
- canonical deterministic response
- preserve terms
- forbidden terms
- safe natural Turkish paraphrase

## Grounding Rules

### Menu and Price Rule
The final response must not introduce items, categories, or prices that are not present
in the structured result or the deterministic menu source of truth.

### Allergy Rule
Allergy responses must preserve the deterministic caution meaning and must keep
`Alerji` and `teyit`.

### Off-Topic Rule
Off-topic responses must preserve refusal meaning. The paraphrased output may be more
natural, but it must still clearly refuse the unrelated request.

### Order Integrity Rule
Order-action responses must preserve the exact item, quantity, and price information from
the structured result.

### Confirmation and Summary Rule
Confirmation and summary responses must preserve deterministic order totals and any
required operational note such as `MVP/demo`.

## Recommended Safety Check
Before returning any model-paraphrased answer, run a final grounding check that verifies:
- no unsupported item names were introduced
- no unexpected prices were introduced
- required safety wording remains present when applicable
- required refusal meaning remains present when applicable
- required order facts still match the structured result

If the paraphrased answer fails the check, the system should fall back to the canonical
deterministic response.

The schema also includes helper checks for that future layer:
- `validate_grounded_result(result)`
- `ensure_required_terms(response, terms)`
- `ensure_forbidden_terms_absent(response, forbidden_terms)`
- `check_paraphrase_safety(original_result, paraphrased_text)`

The formatting layer uses those checks through:
- `format_grounded_response(result, paraphrase_candidate=None)`
- `explain_paraphrase_rejection(result, paraphrase_candidate)`

## Evaluation Plan For Future Experiments
Future model experiments should evaluate two modes separately:
1. raw generated responses
2. grounded or paraphrased responses built on deterministic structured results

This is important because raw generation quality alone does not measure the value of a
constrained language layer.

## Planning Decision
Do not move to the Qwen3 4B class yet.

Grounded generation should be implemented or at least prototyped first, because current
evidence suggests that scaling raw generation alone is unlikely to solve menu faithfulness,
price accuracy, order integrity, safety wording, and off-topic refusal.
