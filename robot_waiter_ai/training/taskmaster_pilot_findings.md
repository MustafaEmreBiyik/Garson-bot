# Taskmaster Pilot Findings

## Summary

The Taskmaster-2 adaptation pipeline worked safely as an intermediate workflow:

- raw extraction worked
- lightweight candidate filtering worked
- `restaurant_search` was safely excluded from adaptation
- manual food-ordering adaptation review worked
- the deterministic canonical preview gate caught a bad route mismatch before anything could move forward

## What Worked

- External Taskmaster data stayed isolated under `datasets/intermediate`.
- No runtime behavior or processed train/valid datasets were changed.
- Manual review gates prevented unsupported menu items, restaurant search behavior, and unsafe deterministic matches from flowing into later steps.

## Main Limitation

Direct row-level adaptation from Taskmaster `food_ordering` had low yield.

Across multiple pilots:

- many rows referenced unsupported foods or broad cuisine requests
- many rows were duplicate generic order-start messages
- later stricter selectors still surfaced short conversational fragments and context-dependent turns
- deterministic preview review showed that even accepted manual rewrites could still map poorly to current deterministic intent routing

## Current Conclusion

Taskmaster should be treated as:

- pattern inspiration
- intent inspiration
- conversation-shape inspiration

Taskmaster should **not** be treated as a direct row-to-training conversion source.

## Recommended Next Step

Prefer menu-first, intent-first, project-grounded review worksheets built from:

- the actual supported menu
- the deterministic scope already implemented in the project

That produces safer Turkish user-message seeds for later reviewed deterministic preview steps.
