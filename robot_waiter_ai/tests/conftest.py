from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

_TMP_ROOT = Path(__file__).resolve().parents[1] / ".test_tmp_runtime"


@pytest.fixture
def tmp_path() -> Path:
    """Provide a per-test temp directory without relying on pytest's Windows tmp root.

    The built-in pytest tmp-path machinery is hitting PermissionError on this
    environment during temp-root creation and cleanup. These tests only need an
    isolated writable Path. In this environment, `tempfile.mkdtemp()` also creates
    directories that end up unwritable, so we create a unique directory manually.
    """

    _TMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = _TMP_ROOT / f"garsonbot-test-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
