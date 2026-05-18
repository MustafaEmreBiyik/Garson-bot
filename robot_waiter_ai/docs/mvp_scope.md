# MVP Scope

## Current Status
- **Text-based CLI MVP is working and demo-ready.**
- Deterministic dialogue management with Turkish normalization and evaluation coverage is in place.

## In Scope
- Menu-aware conversation
- Order state tracking: add, remove, update, clear, summarize
- Safety rules for allergies and unknown requests
- Deterministic dialogue manager
- CLI demo for text interaction
- Dataset preparation and evaluation tooling for future model comparison

## Out of Scope
- ROS 2, Nav2, SLAM
- Robot motion, navigation, or sensors
- Speech processing beyond placeholders
- Payments, dashboards, or database-backed management systems
- Actual model training in the current milestone

## Acceptance Criteria
- [x] Loads menu from YAML
- [x] Responds to common waiter intents
- [x] Confirms and summarizes orders
- [x] Handles unknowns safely
- [x] Provides a measurable automated evaluation baseline

## Demo Scenario
1. User greets the assistant
2. User asks for a recommendation
3. User orders two items
4. User modifies or removes an item
5. Assistant summarizes the order and asks for confirmation
