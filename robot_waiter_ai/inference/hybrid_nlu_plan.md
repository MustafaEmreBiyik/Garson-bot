# Hybrid NLU Plan

## Goal

Add a future-ready hybrid understanding layer for Turkish waiter conversations without allowing a probabilistic model to become the final authority. The assistant should understand more phrasing variation, but every business-critical decision must still be checked by deterministic restaurant logic.

## Why Direct LLM Final Answers Are Unsafe

A direct free-form LLM answer is unsafe for this project because it can:

- invent menu items, prices, allergens, or restaurant policies
- claim availability without checking the menu source of truth
- update or summarize orders incorrectly
- respond confidently to unsupported or off-topic prompts
- downplay allergy risk instead of keeping the required caution language

For a waiter assistant, those are not style problems. They are product and safety failures.

## Why Hybrid NLU Plus Deterministic Execution Is Safer

The safer split is:

1. NLU proposes structure.
2. Deterministic code validates that structure against real menu and order state.
3. Deterministic code produces the canonical answer.

This gives us flexibility on input phrasing while preserving hard guarantees on restaurant facts and safety behavior.

## Target Architecture

```text
user message
-> deterministic quick checks
-> NLU intent/slot parser
-> menu/order/safety validator
-> deterministic executor
-> canonical response
-> optional safe paraphrase
-> final response
```

## Deterministic Quick Checks

These checks should remain available before or alongside NLU:

- empty input
- clear off-topic requests
- existing restaurant information rules
- direct known-item detection where already stable
- safety-sensitive fallbacks

Quick checks reduce unnecessary NLU calls and preserve already-working behavior.

## Decisions That Must Remain Deterministic

The following decisions must never be left to NLU or a future LLM:

- whether an item really exists on the menu
- which category an item truly belongs to
- the actual item price
- whether an item is currently available
- official allergy/allergen caution wording
- order-state mutations and totals
- unsupported item rejection
- off-topic policy and refusal
- final user-visible action outcome

## What the NLU Layer May Propose

The NLU layer may only propose structured fields such as:

- `intent`
- `item_name`
- `category`
- `quantity`
- `constraints`
- `confidence`
- `needs_clarification`
- `raw_text`
- `notes`

These are hypotheses, not facts.

## Low-Confidence Fallback

When NLU confidence is low, or the parsed intent is unclear:

- if the message appears restaurant-related, return a deterministic clarification request
- if it is clearly off-topic, return the existing style of off-topic rejection
- do not guess missing items, prices, or actions

The system should prefer clarification over hallucination.

## Future LLM Integration

This design is intentionally model-agnostic. A future adapter may wrap:

- a local small model
- an API-based LLM
- a rule plus model ensemble

No matter which parser is used later, the contract stays the same:

- parser outputs `ParsedUserIntent`
- validator checks against menu and order state
- deterministic executor remains the source of truth

## Safe Future Extension Path

When a real model is added later, integration should happen in this order:

1. Keep deterministic baseline as default.
2. Add model-backed adapter behind the same interface.
3. Log parsed structures for evaluation before enabling action routing broadly.
4. Measure clarification rate, unsupported-item rejection, and off-topic stability.
5. Only allow optional safe paraphrasing after canonical responses are already correct.

This keeps the hybrid architecture small, reversible, and safe.
