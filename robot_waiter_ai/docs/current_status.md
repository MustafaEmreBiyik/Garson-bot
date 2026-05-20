# Current Status

## Stable Commands

Full tests:

```powershell
.venv\Scripts\python.exe -m pytest -q --basetemp robot_waiter_ai/.pytest_tmp
```

Deterministic evaluation:

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.evals.eval_runner
```

Interactive CLI demo:

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.app.main
```

Voice web demo:

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.demo.voice_web_demo
```

Default URL:

```text
http://localhost:8000
```

If port `8000` is occupied:

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.demo.voice_web_demo --port 8001
```

Then open:

```text
http://localhost:8001
```

Single-message grounded demo:

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.inference.grounded_demo --message "Ayran sipariş etmek istiyorum."
```

## Latest Known Results
- full test suite: `263 passed, 1 warning`
- deterministic evaluation: `17/17 passed`
- deterministic voice web demo smoke test: `passed`
- qwen text smoke test on Windows RTX 4050 laptop: `passed`
- qwen voice web demo smoke test on Windows RTX 4050 laptop: `passed`

## Important Files
- [main.py](C:/Users/Emre/Desktop/Garson-bot/robot_waiter_ai/app/main.py)
- [dialogue_manager.py](C:/Users/Emre/Desktop/Garson-bot/robot_waiter_ai/assistant/dialogue_manager.py)
- [menu.yaml](C:/Users/Emre/Desktop/Garson-bot/robot_waiter_ai/data/menu.yaml)
- [restaurant_info.yaml](C:/Users/Emre/Desktop/Garson-bot/robot_waiter_ai/data/restaurant_info.yaml)
- [eval_runner.py](C:/Users/Emre/Desktop/Garson-bot/robot_waiter_ai/evals/eval_runner.py)
- [evaluation_cases.yaml](C:/Users/Emre/Desktop/Garson-bot/robot_waiter_ai/evals/evaluation_cases.yaml)
- [grounded_demo.py](C:/Users/Emre/Desktop/Garson-bot/robot_waiter_ai/inference/grounded_demo.py)
- [boss_demo_summary.md](C:/Users/Emre/Desktop/Garson-bot/robot_waiter_ai/docs/boss_demo_summary.md)
- [boss_demo_script.md](C:/Users/Emre/Desktop/Garson-bot/robot_waiter_ai/docs/boss_demo_script.md)

## Dataset / Experiment Status
- Taskmaster extraction and filtering were completed safely.
- Direct Taskmaster row-level adaptation was low-yield.
- The project pivoted to safer menu-grounded seed and grounded-paraphrase preparation.
- Intermediate approved candidates exist.
- No intermediate candidates have been promoted into processed train/valid datasets.
- Second manual paraphrase pilot has accepted manual rows, but semantic review is intentionally paused for now.

## Known Limitations
- deterministic backend remains the default production-safe path
- qwen runtime integration exists only as an optional experimental local backend
- windows qwen runtime currently falls back away from 4-bit loading by default because that path degraded reply quality during smoke tests
- browser speech demo exists for local experimentation only; it is not treated as a production speech stack
- no robot motion/navigation stack
- no web/API/deployment layer
- no trained model ready to replace deterministic control
- some deterministic routing quirks still exist in non-demo dataset review paths

## Recommended Next Steps After Demo
- keep the current deterministic baseline as the supervisor-facing milestone
- gather feedback on scope, architecture, and demo expectations
- decide whether the next milestone should prioritize:
  - deterministic quality improvements
  - bounded grounded paraphrasing
  - speech/robot-system integration planning

## Freeze Decision
For the current milestone:
- do not expand dataset pilots further
- do not promote intermediate candidates into processed datasets
- do not train a model
- do not promote the experimental qwen backend as the primary runtime path
