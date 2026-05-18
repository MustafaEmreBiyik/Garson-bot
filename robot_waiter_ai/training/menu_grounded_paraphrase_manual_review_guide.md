# Menu-Grounded Safe Paraphrase Manual Review Guide

This guide applies to:

- `robot_waiter_ai/datasets/intermediate/menu_grounded_grounded_paraphrase_candidates.jsonl`
- `robot_waiter_ai/datasets/intermediate/menu_grounded_paraphrase_manual_pilot_10.jsonl`

These files are **manual review worksheets only**.
They are **not training data**.

## Purpose

At this stage, the goal is to write a natural Turkish `safe_paraphrase` for an
already reviewed `canonical_response`.

The paraphrase must stay grounded to the same facts and safety constraints as the
canonical response.

## What `safe_paraphrase` Should Do

`safe_paraphrase` should be:

- a natural Turkish rewrite of `canonical_response`
- semantically equivalent to the canonical response
- grounded to the same menu facts, prices, cautions, and rejection signals

It should **not**:

- answer the user differently
- add extra menu facts
- add new prices
- introduce delivery, pickup, stock, timing, or discount claims
- weaken safety language

## Preserve Terms

Every row includes `must_preserve_terms`.

Your paraphrase must preserve these terms faithfully, especially:

- menu item names
- price strings such as `45.00 TL`
- quantity strings such as `1 x Ayran`
- caution phrases such as `Lütfen mutfakla teyit ediniz.`
- rejection phrases such as `menümüzde bulunmuyor`

If the row contains allergy caution, do not drop or soften that caution.

## Must-Not-Introduce Rules

Every row includes `must_not_introduce`.

Do not introduce:

- unsupported menu items
- new prices
- discounts
- stock claims
- preparation time
- delivery or pickup promises
- allergy safety guarantees
- ingredients not present in `canonical_response`
- order state changes not present in `canonical_response`

## Rejection Responses

For `rejection_probe_response` rows, the paraphrase must still clearly reject or
redirect the unsupported or off-topic request.

Do not turn a rejection into:

- a soft acceptance
- a recommendation for an unsupported item
- an unrelated menu answer

## Status Fields

In the manual pilot stage:

- keep `safe_paraphrase` empty until a human fills it
- keep `paraphrase_status` as `needs_manual_review` until that human review happens
- keep `include_for_processed_dataset` as `false`

No row should be promoted into a processed dataset in this stage.
