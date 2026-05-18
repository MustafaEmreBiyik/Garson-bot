# External Taskmaster Data

This project uses Taskmaster-2 only as a **local source of English user utterance diversity**
for a future manual or reviewable adaptation step.

Do not use Taskmaster assistant/system replies as training targets.
Do not translate full dialogues directly into SFT records.
Do not write extracted data into the existing processed train/valid JSONL files.

## Place Downloaded Files Here

Copy the two manually downloaded JSON files into:

- `robot_waiter_ai/datasets/external/taskmaster/TM-2-2020/food-ordering.json`
- `robot_waiter_ai/datasets/external/taskmaster/TM-2-2020/restaurant-search.json`

These raw files are intended to stay local and reviewable.

## Safe Extraction Command

From the project root, run:

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.training.extract_taskmaster_user_utterances
```

The extractor writes only to:

- `robot_waiter_ai/datasets/intermediate/taskmaster_user_utterances_raw.jsonl`

## Current Adaptation Scope

`restaurant-search` data may still be extracted and reviewed locally, but it is intentionally
excluded from the next adaptation worksheet by default.

Reason:
- many `restaurant-search` utterances are really about restaurant discovery
- location search, atmosphere filtering, cuisine filtering, or recommendation search
- these are outside the current single-restaurant, menu-grounded waiter scope

For now, the manual adaptation worksheet should be built only from:

- `robot_waiter_ai/datasets/intermediate/taskmaster_food_ordering_candidates.jsonl`

This produces a review-only template at:

- `robot_waiter_ai/datasets/intermediate/taskmaster_food_ordering_adaptation_template.jsonl`
