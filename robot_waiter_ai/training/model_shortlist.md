# Base Model Shortlist

## Goal
This document defines the practical base-model shortlist for future LoRA/QLoRA
fine-tuning experiments for the Turkish waiter-assistant project.

This is still a planning-only document:
- no model is downloaded in the repo task
- no model is loaded in the repo task
- no local training is started in the repo task

## Current Experiment Reality
Completed smoke-test results:
- `Qwen/Qwen3-0.6B`: `4/17` passed, `23.53%`
- `Qwen/Qwen3-1.7B`: `5/17` passed, `29.41%`

These results show that:
- the training pipeline works
- a slightly larger model helped only marginally
- model scaling alone did not solve menu faithfulness, exact prices, order integrity,
  allergy caution, or off-topic refusal

Because of that, model selection must now be paired with grounded-generation design.

## Project-Specific Model Requirements
Any future candidate should be:
- capable of Turkish or at least strong multilingual dialogue
- instruction-following or chat-oriented, rather than raw-base-only
- small enough to remain plausible for later Jetson Orin NX inference when quantized
- compatible with LoRA or QLoRA fine-tuning workflows
- suitable for polite waiter and customer-service dialogue
- usable as a constrained paraphrasing layer if grounded generation is adopted

The project does not currently need:
- multimodal reasoning
- tool calling
- very long context for normal restaurant turns
- a huge reasoning-focused model as the first production path

## Candidate Classes

### 0.5B-1.5B Models
Strengths:
- easiest class for early debugging
- cheapest class for smoke-test runs
- strongest chance of later fitting lightweight edge inference paths
- fastest training iteration speed

Weaknesses:
- more likely to underperform on role consistency and nuanced Turkish dialogue
- more likely to hallucinate or over-simplify menu behavior
- not trustworthy enough as raw end-to-end business-logic generators in current results

Use in this project:
- best class for plumbing tests and constrained paraphrasing experiments
- no longer sufficient evidence for using them as the main raw generator

### 2B-4B Models
Strengths:
- better balance between quality and cost
- still realistic for later quantized edge deployment depending on runtime and memory budget
- better chance of producing stronger Turkish phrasing quality

Weaknesses:
- slower and heavier than the smallest class
- more demanding for VRAM and iteration speed during experimentation
- still may fail on grounded restaurant requirements if used as a raw generator

Use in this project:
- possible next class after grounded-generation design exists
- not the immediate fix by itself

### 7B+ Models
Strengths:
- usually stronger general dialogue quality
- more robust instruction following and reasoning

Weaknesses:
- heavier training cost
- slower iteration cycle
- higher VRAM and RAM requirements
- harder future Jetson Orin NX deployment story

Use in this project:
- not recommended as the next step

## Candidate Shortlist

### Qwen3 Small Dense Instruct/Post-Trained Class
Suggested candidates:
- `Qwen/Qwen3-0.6B`
- `Qwen/Qwen3-1.7B`
- `Qwen/Qwen3-4B-Instruct-2507` or the closest stable 4B Qwen3 instruct/post-trained variant available at experiment time

Why this family is still attractive:
- strong multilingual and instruction-following positioning
- multiple dense sizes for staged experimentation
- practical progression path from debugging to stronger quality experiments
- good fit for text-only restaurant dialogue

Updated project note:
- the 0.6B and 1.7B sizes validated the pipeline but were not acceptable as the main raw waiter assistant
- the 4B class should not be tried immediately as a blind size escalation
- the next Qwen experiment should ideally happen after grounded generation is implemented or at least prototyped

### Gemma 3 Instruction-Tuned Class
Suggested candidates:
- `google/gemma-3-1b-it`
- `google/gemma-3-4b-it`

Why this family is attractive:
- small model options exist at 1B and 4B
- instruction-tuned variants are available
- useful as a comparison family against Qwen3

Project caution:
- use as a comparison family, not as an excuse to skip grounded generation

### SmolLM3-3B
Suggested candidate:
- `HuggingFaceTB/SmolLM3-3B`

Why this family is attractive:
- compact 3B class
- fully open positioning
- reasonable size for experimentation

Project caution:
- keep this optional
- evaluate it in both raw and grounded modes if it is ever tested

## Updated Recommendation
Current recommendation:
1. do not move directly to Qwen3 4B yet
2. implement or prototype grounded generation first
3. only then evaluate the next model step, potentially including the Qwen3 4B class

Why this is now the safest path:
- raw generation already failed on deterministic business-logic requirements at 0.6B and 1.7B
- bigger models may improve fluency while still hallucinating menu facts or weakening safety wording
- grounded generation attacks the failure mode more directly than pure scaling

## Evaluation Plan
When future model experiments are approved:
1. record the deterministic baseline benchmark result as the reference
2. generate raw model outputs for the existing `evaluation_cases.yaml` case IDs
3. score them with `generated_output_adapter.py`
4. generate grounded or paraphrased outputs built on deterministic structured results
5. score those as well
6. compare:
   - pass rate
   - Turkish quality
   - menu faithfulness
   - price accuracy
   - allergy caution
   - role consistency

## Decision Checklist
- [ ] model license is acceptable for the project
- [ ] model supports Turkish or practical multilingual usage
- [ ] model has an instruct or chat-oriented variant
- [ ] tokenizer and chat template are available
- [ ] model is compatible with LoRA or QLoRA fine-tuning
- [ ] model can later be quantized for Jetson inference
- [ ] grounded-generation design exists before larger raw-generation experiments are prioritized
- [ ] future evaluations compare both raw and grounded outputs

## Current Recommendation Status
No model is currently acceptable as the main waiter assistant.

Current planning recommendation:
- trusted runtime reference: deterministic baseline
- immediate architecture priority: grounded generation
- completed smoke-test candidates: Qwen3 0.6B and Qwen3 1.7B
- deferred larger fallback: Qwen3 4B class only after grounded generation is implemented or at least prototyped
- comparison families: Gemma 3 and SmolLM3, only if they are evaluated under the same grounded constraints
