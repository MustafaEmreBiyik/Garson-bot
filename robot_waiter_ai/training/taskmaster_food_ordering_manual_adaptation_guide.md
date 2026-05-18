# Taskmaster Food-Ordering Manual Adaptation Guide

This guide explains how to manually review and fill:

- `robot_waiter_ai/datasets/intermediate/taskmaster_food_ordering_adaptation_template.jsonl`
- `robot_waiter_ai/datasets/intermediate/taskmaster_food_ordering_adaptation_pilot_30.jsonl`
- `robot_waiter_ai/datasets/intermediate/taskmaster_food_ordering_adaptation_pilot_50_v2.jsonl`

This stage is a **manual worksheet only**.
It is **not training data**.

The pilot file is a small human-review worksheet created from the food-ordering template.
It is also **not training data**.

The first pilot (`pilot_30`) was intentionally safe but had low yield because many examples
referenced unsupported items or broad cuisine requests.

The second pilot (`pilot_50_v2`) uses more conservative selection:

- excludes rows already used in the first pilot
- prefers shorter and clearer food-ordering candidates
- down-ranks obvious unsupported item and cuisine patterns
- stays review-only and is still **not training data**

## Purpose

Taskmaster-2 `food_ordering` is used only as a source of **English user utterance diversity**.

The goal is to review an English user utterance and decide whether it can be safely rewritten as:

- a natural Turkish customer message
- within the current single-restaurant scope
- grounded to our menu-driven waiter interaction setting

This worksheet is only for preparing candidate user-side inputs for later human-reviewed pipeline steps.

## Allowed Manual Adaptation

You may manually rewrite an English utterance into Turkish only when it can be safely interpreted as an in-scope waiter interaction such as:

- ordering an item
- asking what is on the menu
- asking about ingredients
- asking about price
- modifying an order
- removing an item or ingredient
- asking a cautious dietary question that stays within what the system can safely handle

The rewritten Turkish message should sound like a real customer speaking naturally to a waiter in one restaurant.

Keep the rewrite:

- short
- natural
- menu-grounded
- compatible with the project’s deterministic restaurant assistant scope

## Reject Criteria

Reject or leave unadapted when the utterance depends on anything outside current scope, including:

- unsupported menu items
- delivery address flow
- payment flow
- phone number handling
- restaurant discovery or restaurant search
- reservation flow
- real-world restaurant recommendation
- external business/location information
- allergy guarantees the system cannot safely make

If the utterance cannot be safely rewritten into an in-scope Turkish waiter message, do not force it.

## Menu-Grounding Rule

Do **not** blindly translate unsupported items.

If an English item does not exist in our menu:

- adapt it only if there is a semantically safe mapping to a supported menu item or category
- otherwise reject it or leave a clear review note

Examples:

- `burger` should not automatically become an arbitrary Turkish menu item unless the menu supports a genuinely safe equivalent
- `burrito`, `ribs`, or other external items should usually be rejected or flagged for review unless there is a clearly approved mapping rule

When in doubt, reject or mark for review instead of over-adapting.

## Template Field Instructions

Each template row contains:

- `source_dataset`
- `source_domain`
- `conversation_id`
- `turn_index`
- `original_text`
- `candidate_category`
- `turkish_adapted_user_message`
- `adaptation_status`
- `adaptation_notes`
- `include_for_future_grounded_generation`

Fill fields as follows.

### `turkish_adapted_user_message`

Write a Turkish customer utterance only if the example is safely in scope.

Good characteristics:

- sounds like a customer talking to a waiter
- does not invent unsupported restaurant capabilities
- does not mention external restaurants
- does not assume unavailable items are available

Leave empty if rejected.

### `adaptation_status`

Use one of:

- `needs_manual_review`
- `accepted_adapted`
- `rejected_out_of_scope`
- `rejected_unsupported_item`
- `rejected_unsafe_allergy`
- `rejected_unclear`

Guidance:

- `accepted_adapted`: safe Turkish rewrite completed
- `rejected_out_of_scope`: discovery, reservation, delivery, payment, external info, or similar
- `rejected_unsupported_item`: item cannot be safely grounded to menu
- `rejected_unsafe_allergy`: would require guarantees the system should not make
- `rejected_unclear`: user intent is too ambiguous or incomplete

### `adaptation_notes`

Use short notes explaining the decision, especially for rejections.

Examples:

- `Unsupported item not in menu`
- `Requires delivery address handling`
- `Asks for allergy guarantee beyond safe scope`
- `Adapted to in-scope menu inquiry`

### `include_for_future_grounded_generation`

Set to `true` only when:

- the Turkish user message is safely adapted
- it is clearly in scope
- it is appropriate for a later manual grounded-generation step

Otherwise keep it `false`.

## Examples

### 1. Order item

Original English:
- `Can I get a soup and a tea?`

Decision:
- Accept

Turkish adapted user message:
- `Bir çorba ve bir çay alabilir miyim?`

Reason:
- Simple in-scope item order if both items are supported by menu

### 2. Ask menu

Original English:
- `What drinks do you have?`

Decision:
- Accept

Turkish adapted user message:
- `İçecek olarak neler var?`

Reason:
- Natural menu exploration request within single-restaurant scope

### 3. Modify order

Original English:
- `Can you make that without onions?`

Decision:
- Accept

Turkish adapted user message:
- `Onu soğansız hazırlayabilir misiniz?`

Reason:
- In-scope modification request if tied to a supported item

### 4. Ask ingredient

Original English:
- `What is in the lentil soup?`

Decision:
- Accept

Turkish adapted user message:
- `Mercimek çorbasının içinde neler var?`

Reason:
- Safe ingredient question when the referenced item is on menu

### 5. Allergy or dietary caution

Original English:
- `Do you have anything without dairy?`

Decision:
- Accept with caution

Turkish adapted user message:
- `Süt ürünü içermeyen bir seçeneğiniz var mı?`

Reason:
- Allowed as a cautious dietary question, but do not turn it into a safety guarantee

### 6. Reject unsupported item

Original English:
- `I'd like to order a burrito combo.`

Decision:
- Reject

Turkish adapted user message:
- leave empty

Reason:
- `rejected_unsupported_item`
- Item is not safely grounded to the project menu

### 7. Reject delivery flow

Original English:
- `Can you send it to my home address?`

Decision:
- Reject

Turkish adapted user message:
- leave empty

Reason:
- `rejected_out_of_scope`
- Requires delivery/address handling

### 8. Reject payment flow

Original English:
- `Can I pay with cash when it arrives?`

Decision:
- Reject

Turkish adapted user message:
- leave empty

Reason:
- `rejected_out_of_scope`
- Involves payment and delivery flow

### 9. Reject reservation

Original English:
- `Book a table for four at 7 PM.`

Decision:
- Reject

Turkish adapted user message:
- leave empty

Reason:
- `rejected_out_of_scope`
- Reservation flow is outside scope

### 10. Reject unsafe allergy guarantee

Original English:
- `Can you guarantee this is completely peanut-free?`

Decision:
- Reject

Turkish adapted user message:
- leave empty

Reason:
- `rejected_unsafe_allergy`
- Requires a guarantee the system should not safely imply

## Explicit Warning

Do **not** create assistant responses in this stage.

Do **not** create canonical deterministic responses in this stage.

Do **not** add records directly into:

- `grounded_paraphrase_train.jsonl`
- `grounded_paraphrase_valid.jsonl`
- `waiter_sft_train.jsonl`
- `waiter_sft_valid.jsonl`

Do **not** use `restaurant_search` candidates for this worksheet stage.

Only review and fill the food-ordering adaptation template manually.
