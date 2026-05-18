# Menu-Grounded Canonical Review Findings

The first review pass over the menu-grounded deterministic canonical preview found
`9` rejected deterministic matches.

These findings are runtime-quality observations, not dataset-pipeline failures.
The menu-grounded seed review, canonical preview export, and audit-trail review
steps all behaved as intended by surfacing the mismatches without writing anything
into processed training datasets.

This task does **not** fix runtime behavior.
The rejected rows should be investigated later in a separate deterministic routing
or dialogue-quality task.

Current rejected clusters:

- `ask_menu`: some menu questions were routed to `add_item` or `off_topic` instead of a menu-oriented answer
- `modify_order`: modification-style user messages were routed to `add_item` or generic `menu_question` answers
- `unsupported_item_probe`: one unsupported-item probe was treated more like off-topic than explicit unavailable-item rejection
- `off_topic_rejection_probe`: one off-topic probe returned a menu-category answer instead of a refusal/scope redirect

Recommended follow-up:

- keep these rejected rows out of grounded paraphrase candidate generation for now
- review the deterministic routing behavior separately from the dataset-preparation pipeline
- preserve the reviewed audit files as evidence of which rows are currently safe versus unsafe
