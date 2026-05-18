# Garson-bot

Turkish conversational AI module for a waiter robot. The current milestone is a deterministic, menu-grounded, safety-conscious assistant with CLI and demo tooling, plus data/eval pipelines to support future local fine-tuning.

## Highlights
- Deterministic dialogue manager with Turkish intent matching
- Menu-aware, polite, and safety-focused responses
- Order state tracking (add, remove, update, clear, summarize)
- CLI demo and a local voice web demo wrapper
- Evaluation runner with measurable baseline
- Data preparation utilities for future local fine-tuning

## What This Repo Is (and Is Not)
**In scope**
- Menu-aware conversation in Turkish
- Deterministic assistant logic and safety rules
- CLI demo and local voice web demo
- Evaluation and dataset tooling

**Out of scope (current milestone)**
- ROS2, Nav2, SLAM, motion, sensors
- Payment or POS integrations
- External LLM providers
- Production speech stack or deployment API

## Quick Start (Windows PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Run the CLI demo:
```powershell
python -m robot_waiter_ai.app.main
```

Run the evaluation suite:
```powershell
python -m robot_waiter_ai.evals.eval_runner
```

Run the voice web demo:
```powershell
python -m robot_waiter_ai.demo.voice_web_demo
```
Then open:
```
http://localhost:8000
```

## Tests
```powershell
python -m pytest -q --basetemp robot_waiter_ai/.pytest_tmp
```

## Project Notes
- Menu and restaurant data live in [robot_waiter_ai/data/menu.yaml](robot_waiter_ai/data/menu.yaml) and [robot_waiter_ai/data/restaurant_info.yaml](robot_waiter_ai/data/restaurant_info.yaml).
- Core logic is in [robot_waiter_ai/assistant/dialogue_manager.py](robot_waiter_ai/assistant/dialogue_manager.py).
- Evaluation cases are in [robot_waiter_ai/evals/evaluation_cases.yaml](robot_waiter_ai/evals/evaluation_cases.yaml).
- Voice demo details are in [robot_waiter_ai/demo/README.md](robot_waiter_ai/demo/README.md).

## Documentation
- [robot_waiter_ai/docs/project_brief.md](robot_waiter_ai/docs/project_brief.md)
- [robot_waiter_ai/docs/mvp_scope.md](robot_waiter_ai/docs/mvp_scope.md)
- [robot_waiter_ai/docs/current_status.md](robot_waiter_ai/docs/current_status.md)

## License
Not specified yet.
