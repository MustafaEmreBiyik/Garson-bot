# Testing Notes

## Windows Pytest Temp-Directory Note
This project has `tmp_path`-based tests in:
- `test_eval_runner.py`
- `test_generated_output_adapter.py`
- `test_train_lora_config.py`
- `test_training.py`

On Windows, the plain command:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

may fail if pytest uses a temp root that already contains unreadable leftover directories.
In this repository, the failure mode appeared as `PermissionError` during pytest
temp-directory setup rather than normal assertion failures.

## Recommended Windows Test Command
Use a project-local base temp:

```powershell
.venv\Scripts\python.exe -m pytest -q --basetemp robot_waiter_ai/.pytest_tmp
```

The test suite also provides a local `tmp_path` fixture in
`robot_waiter_ai/tests/conftest.py`. It still gives each test an isolated
`Path`, but it creates a unique directory manually under
`robot_waiter_ai/.test_tmp_runtime` instead of using pytest's default Windows
tmp-root machinery or `tempfile.mkdtemp(...)`, both of which were producing
permission failures in this environment.

## Why This Helps
- keeps pytest temp files inside the repository workspace
- avoids relying on a problematic global temp root
- makes temp state easier to inspect and clean up
- avoids the flaky built-in pytest temp-root behavior for `tmp_path` tests on this Windows setup

## Pytest Discovery Guardrails
The repository includes `pytest.ini` with:
- `testpaths = robot_waiter_ai/tests`
- `norecursedirs` entries for known temp and cache folders

This prevents pytest from trying to collect files from project-local temp directories such as:
- `robot_waiter_ai/.pytest_tmp`
- `robot_waiter_ai/.tmp_pytest`
- `robot_waiter_ai/.test_tmp_runtime`
- `.pytest_cache`

## Project-Local Temp Folders
If present and unlocked, these project-local temp folders are safe to remove between runs:
- `robot_waiter_ai/.pytest_tmp`
- `robot_waiter_ai/.tmp_pytest`
- `.pytest_cache`

Do not delete system temp directories outside the project without explicit confirmation.

## Scope Reminder
These notes are only about test execution reliability.
They do not change runtime logic, dataset schema, evaluation rules, or training behavior.
