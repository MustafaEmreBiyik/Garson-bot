# Boss Demo Summary

## Project Goal
Turkish conversational AI / language-model module for a waiter robot.

## Current Scope
This project currently focuses on menu-grounded waiter conversation logic.

In scope today:
- restaurant-scope Turkish text interaction
- deterministic intent detection
- menu-grounded responses
- order state tracking
- safety-aware allergy/off-topic handling
- evaluation and dataset-preparation tooling

Out of scope today:
- ROS
- Nav2
- SLAM
- motor control
- robot movement
- FastAPI
- STT/TTS
- database integration
- web dashboard
- production deployment
- real LLM runtime integration
- heavy ML dependencies

## Current Architecture
```text
user message
  -> deterministic intent/menu/order/safety layer
  -> GroundedResult
  -> optional future paraphrase candidate
  -> safety/grounding formatter
  -> final response
```

Current source-of-truth modules remain deterministic:
- menu availability
- prices
- order add/remove/summary/confirm logic
- allergy caution wording
- off-topic refusal

## Why a Pure Fine-Tuned Model Is Not the Main Decision-Maker
Raw waiter smoke-test results were not strong enough to replace deterministic logic:

| Model | Passed | Total | Pass Rate |
|---|---:|---:|---:|
| `Qwen/Qwen3-0.6B` | 4 | 17 | 23.53% |
| `Qwen/Qwen3-1.7B` | 5 | 17 | 29.41% |

Main conclusion:
- raw generation sounded natural in places
- but it was weak on menu faithfulness, exact prices, order integrity, allergy caution, and off-topic refusal
- therefore the model should not be the main decision-maker

## Current Deterministic Quality Status
- Deterministic evaluation: `17/17` passed
- Latest full test result: `160 passed, 1 warning`

## Dataset Work Summary
- Taskmaster-2 extraction/filtering/adaptation experiments were completed safely.
- `restaurant_search` was excluded from adaptation.
- Direct Taskmaster row-level adaptation was low-yield and fragment-heavy.
- The project pivoted to safer menu-grounded Turkish user-message seeds.
- Menu-grounded canonical review produced `39` grounded paraphrase candidates.
- First manual paraphrase pilot produced `8` approved intermediate candidates.
- Second manual paraphrase pilot now has `10` `accepted_manual_paraphrase` rows, but those still need semantic review later.
- No intermediate work has been promoted into processed train/valid datasets.

## What Is Demo-Ready Now
- deterministic waiter conversation flow
- menu-grounded item ordering
- grounded price answers
- grounded ingredient answers
- allergy-caution responses with kitchen-confirmation language
- unsupported-item rejection
- off-topic rejection
- deterministic evaluation report showing `17/17`
- test suite status showing `160 passed, 1 warning`

## What Is Not Demo-Ready Yet
- learned-model runtime assistant
- automatic paraphrase generation in production flow
- promotion of intermediate paraphrase candidates into processed datasets
- model training results strong enough to replace deterministic control
- robot motion, navigation, speech, or deployment infrastructure

## Future Work After This Milestone
- review the second manual paraphrase pilot semantically
- decide whether any approved intermediate candidates should be promoted later
- investigate deterministic routing mismatches separately from dataset work
- prototype bounded grounded paraphrasing only after deterministic quality remains protected
