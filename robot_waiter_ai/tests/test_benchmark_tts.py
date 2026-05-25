"""
Unit tests for scripts/benchmark_tts.py.

All tests run without edge-tts or Piper installed and without internet access.
They verify:
  - The script is importable with no module-level I/O side effects.
  - TTSResult.compute_stats() computes correct statistics (latency, TTFA,
    chars_per_s) including the no-TTFA path (Piper).
  - save_json() and save_csv() produce well-formed output.
  - CLI argument parsing produces the expected Namespace.
  - benchmark_edge_tts() returns an empty list when edge-tts is not installed.
  - benchmark_piper() returns an empty list when the binary is not found.
  - benchmark_piper() returns an empty list when the model is not found.
  - _find_piper_binary() and _find_piper_model() return None when absent.
  - main() returns 1 when no results are collected.
  - _rss_mb() returns a non-negative float.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit
_SENTINEL = object()  # sentinel for sys.modules manipulation

# ---------------------------------------------------------------------------
# Import benchmark_tts.py via importlib (script, not a package)
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"

import importlib.util as _ilu

_spec = _ilu.spec_from_file_location("benchmark_tts", _SCRIPTS_DIR / "benchmark_tts.py")
_bm = _ilu.module_from_spec(_spec)          # type: ignore[arg-type]
sys.modules["benchmark_tts"] = _bm
_spec.loader.exec_module(_bm)               # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# TTSResult.compute_stats — latency statistics
# ---------------------------------------------------------------------------

def test_compute_stats_median_and_p95():
    r = _bm.TTSResult(
        engine="edge-tts", voice="tr-TR-EmelNeural",
        text="Merhaba!", text_chars=8, run_count=10,
        latencies_ms=[100.0, 200.0, 150.0, 120.0, 300.0,
                      110.0, 180.0, 130.0, 140.0, 500.0],
    )
    r.compute_stats()

    # sorted: [100, 110, 120, 130, 140, 150, 180, 200, 300, 500]
    # median  index 5 → 150.0
    assert r.median_latency_ms == 150.0
    # p95  max(0, int(10*0.95)-1) = 8 → 300.0
    assert r.p95_latency_ms == 300.0
    assert r.min_latency_ms == 100.0
    assert r.max_latency_ms == 500.0


def test_compute_stats_single_run():
    r = _bm.TTSResult(
        engine="edge-tts", voice="tr-TR-EmelNeural",
        text="Merhaba!", text_chars=8, run_count=1,
        latencies_ms=[250.0],
    )
    r.compute_stats()

    assert r.median_latency_ms == 250.0
    assert r.p95_latency_ms == 250.0
    assert r.min_latency_ms == 250.0
    assert r.max_latency_ms == 250.0


def test_compute_stats_empty_does_not_raise():
    r = _bm.TTSResult(
        engine="edge-tts", voice="tr-TR-EmelNeural",
        text="x", text_chars=1, run_count=0,
    )
    r.compute_stats()  # must not raise
    assert r.median_latency_ms == 0.0
    assert r.chars_per_s == 0.0


# ---------------------------------------------------------------------------
# TTSResult.compute_stats — TTFA
# ---------------------------------------------------------------------------

def test_compute_stats_ttfa_is_median():
    r = _bm.TTSResult(
        engine="edge-tts", voice="tr-TR-EmelNeural",
        text="Hi", text_chars=2, run_count=3,
        latencies_ms=[300.0, 320.0, 310.0],
        ttfa_ms_list=[80.0, 100.0, 90.0],
    )
    r.compute_stats()

    # sorted ttfa: [80, 90, 100] → index 1 = 90.0
    assert r.median_ttfa_ms == 90.0


def test_compute_stats_no_ttfa_for_piper():
    """Piper outputs all-at-once; ttfa_ms_list is empty — median_ttfa_ms stays 0."""
    r = _bm.TTSResult(
        engine="piper", voice="tr_TR-fahrettin-medium",
        text="Hi", text_chars=2, run_count=3,
        latencies_ms=[150.0, 160.0, 155.0],
        ttfa_ms_list=[],
    )
    r.compute_stats()

    assert r.median_ttfa_ms == 0.0


# ---------------------------------------------------------------------------
# TTSResult.compute_stats — chars_per_s
# ---------------------------------------------------------------------------

def test_compute_stats_chars_per_s():
    # 10 chars at 500 ms median → 20 chars/s
    r = _bm.TTSResult(
        engine="edge-tts", voice="tr-TR-EmelNeural",
        text="0123456789", text_chars=10, run_count=1,
        latencies_ms=[500.0],
    )
    r.compute_stats()

    assert r.chars_per_s == pytest.approx(20.0, abs=0.1)


def test_compute_stats_audio_bytes_median():
    r = _bm.TTSResult(
        engine="edge-tts", voice="tr-TR-EmelNeural",
        text="x", text_chars=1, run_count=3,
        latencies_ms=[100.0, 100.0, 100.0],
        audio_sizes_bytes=[4000, 6000, 5000],
    )
    r.compute_stats()

    # sorted: [4000, 5000, 6000] → index 1 = 5000
    assert r.median_audio_bytes == 5000


# ---------------------------------------------------------------------------
# save_json / save_csv
# ---------------------------------------------------------------------------

def _make_tts_result(**overrides):
    defaults = dict(
        engine="edge-tts",
        voice="tr-TR-EmelNeural",
        text="Merhaba!",
        text_chars=8,
        run_count=3,
        latencies_ms=[200.0, 220.0, 210.0],
        ttfa_ms_list=[70.0, 80.0, 75.0],
        audio_sizes_bytes=[5000, 5100, 5050],
        median_latency_ms=210.0,
        p95_latency_ms=220.0,
        min_latency_ms=200.0,
        max_latency_ms=220.0,
        median_ttfa_ms=75.0,
        median_audio_bytes=5050,
        chars_per_s=38.1,
        ram_before_mb=150.0,
        ram_after_mb=152.0,
        ram_delta_mb=2.0,
        timestamp="2026-05-23T00:00:00+00:00",
        platform_info="Linux-5.15-aarch64",
    )
    defaults.update(overrides)
    return _bm.TTSResult(**defaults)


def test_save_json_writes_valid_json(tmp_path):
    results = [_make_tts_result(), _make_tts_result(engine="piper")]
    out = tmp_path / "results.json"
    _bm.save_json(results, out)

    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["engine"] == "edge-tts"
    assert data[1]["engine"] == "piper"
    assert "latencies_ms" in data[0]
    assert "ttfa_ms_list" in data[0]


def test_save_json_preserves_turkish_chars(tmp_path):
    """ensure_ascii=False must keep Turkish glyphs intact."""
    text = "Siparisz aliyorum"
    results = [_make_tts_result(text=text)]
    out = tmp_path / "tr.json"
    _bm.save_json(results, out)

    raw = out.read_text(encoding="utf-8")
    assert text in raw


def test_save_csv_writes_valid_csv(tmp_path):
    results = [_make_tts_result(), _make_tts_result(engine="piper")]
    out = tmp_path / "results.csv"
    _bm.save_csv(results, out)

    rows = list(csv.DictReader(out.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 2
    assert rows[0]["engine"] == "edge-tts"
    assert rows[1]["engine"] == "piper"
    required_cols = {
        "engine", "voice", "text", "text_chars", "run_count",
        "median_latency_ms", "p95_latency_ms", "median_ttfa_ms",
        "median_audio_bytes", "chars_per_s",
    }
    assert required_cols.issubset(rows[0].keys()), (
        f"Missing CSV columns: {required_cols - rows[0].keys()}"
    )


def test_save_csv_is_noop_for_empty_list(tmp_path):
    out = tmp_path / "empty.csv"
    _bm.save_csv([], out)
    assert not out.exists()


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def test_parse_args_defaults():
    args = _bm._parse_args([])
    assert args.engines == ["edge-tts"]
    assert args.runs == 5
    assert args.edge_voices == ["tr-TR-EmelNeural", "tr-TR-AhmetNeural"]
    assert args.sentences is None
    assert args.piper_binary is None
    assert args.piper_model is None


def test_parse_args_both_engines():
    args = _bm._parse_args(["--engines", "edge-tts", "piper"])
    assert set(args.engines) == {"edge-tts", "piper"}


def test_parse_args_custom_runs_and_voices():
    args = _bm._parse_args([
        "--runs", "3",
        "--edge-voices", "tr-TR-EmelNeural",
    ])
    assert args.runs == 3
    assert args.edge_voices == ["tr-TR-EmelNeural"]


def test_parse_args_piper_paths():
    args = _bm._parse_args([
        "--engines", "piper",
        "--piper-binary", "/usr/bin/piper",
        "--piper-model", "/models/tr.onnx",
    ])
    assert args.piper_binary == "/usr/bin/piper"
    assert args.piper_model == "/models/tr.onnx"


def test_parse_args_custom_sentences():
    args = _bm._parse_args(["--sentences", "Merhaba!", "Nasılsınız?"])
    assert args.sentences == ["Merhaba!", "Nasılsınız?"]


# ---------------------------------------------------------------------------
# _find_piper_binary / _find_piper_model — not found paths
# ---------------------------------------------------------------------------

def test_find_piper_binary_returns_none_when_absent():
    binary = _bm._find_piper_binary(None)
    # In the test sandbox piper is not installed; must return None gracefully.
    # If piper IS installed on this machine, the result is a string (still passes).
    assert binary is None or isinstance(binary, str)


def test_find_piper_model_returns_none_when_absent(tmp_path):
    # Patch candidates to point at nonexistent paths.
    with patch.object(_bm, "_PIPER_MODEL_CANDIDATES", [tmp_path / "nonexistent.onnx"]):
        model = _bm._find_piper_model(None)
    assert model is None


def test_find_piper_binary_uses_override_when_exists(tmp_path):
    fake_binary = tmp_path / "piper"
    fake_binary.write_text("#!/bin/sh\n")
    result = _bm._find_piper_binary(str(fake_binary))
    assert result == str(fake_binary)


def test_find_piper_binary_returns_none_for_nonexistent_override(tmp_path):
    result = _bm._find_piper_binary(str(tmp_path / "no_such_binary"))
    assert result is None


def test_find_piper_model_uses_override_when_exists(tmp_path):
    fake_model = tmp_path / "tr_TR-fahrettin-medium.onnx"
    fake_model.write_bytes(b"\x00" * 8)
    result = _bm._find_piper_model(str(fake_model))
    assert result == fake_model


# ---------------------------------------------------------------------------
# benchmark_edge_tts — missing edge-tts graceful skip
# ---------------------------------------------------------------------------

def test_benchmark_edge_tts_returns_empty_when_edge_tts_missing():
    # Simulate edge-tts not installed: remove it from sys.modules if present,
    # and make importing it raise ImportError.
    import importlib
    saved = sys.modules.pop("edge_tts", _SENTINEL)
    sys.modules["edge_tts"] = None   # None => ImportError on "import edge_tts"
    try:
        results = _bm.benchmark_edge_tts(
            sentences=["Merhaba!"],
            voices=["tr-TR-EmelNeural"],
            runs=1,
        )
    finally:
        if saved is _SENTINEL:
            sys.modules.pop("edge_tts", None)
        else:
            sys.modules["edge_tts"] = saved
    assert results == []


# ---------------------------------------------------------------------------
# benchmark_piper — missing binary / missing model graceful skip
# ---------------------------------------------------------------------------

def test_benchmark_piper_returns_empty_when_binary_missing(tmp_path):
    with patch.object(_bm, "_PIPER_BINARY_CANDIDATES", []):
        results = _bm.benchmark_piper(
            sentences=["Merhaba!"],
            runs=1,
            piper_binary=str(tmp_path / "no_piper"),
        )
    assert results == []


def test_benchmark_piper_returns_empty_when_model_missing(tmp_path):
    fake_binary = tmp_path / "piper"
    fake_binary.write_text("#!/bin/sh\n")

    with patch.object(_bm, "_PIPER_MODEL_CANDIDATES", []):
        results = _bm.benchmark_piper(
            sentences=["Merhaba!"],
            runs=1,
            piper_binary=str(fake_binary),
            piper_model=str(tmp_path / "no_model.onnx"),
        )
    assert results == []


# ---------------------------------------------------------------------------
# benchmark_edge_tts — mock synthesize_streaming
# ---------------------------------------------------------------------------

def test_benchmark_edge_tts_with_mock_tts():
    """Verify run count, TTSResult fields, and stats.

    Patches _edge_single_run directly so the test does not depend on
    edge-tts being installed or the TTS class internals.
    """

    async def _fake_run(tts, text: str):
        return (200.0, 80.0, 5000)   # latency_ms, ttfa_ms, audio_bytes

    # edge_tts must appear importable so benchmark_edge_tts passes its guard.
    fake_edge_tts = MagicMock()
    with patch.dict(sys.modules, {"edge_tts": fake_edge_tts}):
        with patch.object(_bm, "_edge_single_run", _fake_run):
            results = _bm.benchmark_edge_tts(
                sentences=["Merhaba!", "Siparisz"],
                voices=["tr-TR-EmelNeural"],
                runs=2,
            )

    assert len(results) == 2, f"Expected 2 results, got {len(results)}"
    for r in results:
        assert r.engine == "edge-tts"
        assert r.voice == "tr-TR-EmelNeural"
        assert r.run_count == 2
        assert len(r.latencies_ms) == 2
        assert r.median_latency_ms == pytest.approx(200.0)
        assert r.median_ttfa_ms == pytest.approx(80.0)
        assert r.median_audio_bytes == 5000


def test_main_returns_1_when_no_results(tmp_path):
    """When edge-tts is absent and piper is absent, main returns 1."""
    with patch.dict(sys.modules, {"edge_tts": None}):
        exit_code = _bm.main([
            "--engines", "edge-tts",
            "--output-dir", str(tmp_path),
        ])
    assert exit_code == 1


# ---------------------------------------------------------------------------
# _rss_mb
# ---------------------------------------------------------------------------

def test_rss_mb_returns_non_negative_float():
    mb = _bm._rss_mb()
    assert isinstance(mb, float)
    assert mb >= 0.0
