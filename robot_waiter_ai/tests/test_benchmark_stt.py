"""
Unit tests for scripts/benchmark_stt.py.

All tests run without faster-whisper installed and without real audio files.
They verify:
  - The script is importable with no module-level I/O side effects.
  - CLI argument parsing produces the expected Namespace.
  - RunResult.compute_stats() computes correct statistics.
  - save_json() and save_csv() produce well-formed output.
  - run_model_benchmark() measures timing correctly with a mock SpeechToText.
  - main() exits with code 1 when audio-dir is missing or faster-whisper absent.
  - _rss_mb() returns a non-negative float.
  - _make_silent_wav() returns valid WAV bytes.
"""
from __future__ import annotations

import csv
import json
import sys
import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Import benchmark_stt.py (not a package — use importlib.util)
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"

import importlib.util as _ilu

_spec = _ilu.spec_from_file_location("benchmark_stt", _SCRIPTS_DIR / "benchmark_stt.py")
_bm = _ilu.module_from_spec(_spec)          # type: ignore[arg-type]
sys.modules["benchmark_stt"] = _bm          # register BEFORE exec so @dataclass finds the module
_spec.loader.exec_module(_bm)               # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# _make_silent_wav
# ---------------------------------------------------------------------------

def test_make_silent_wav_returns_valid_wav():
    wav_bytes = _bm._make_silent_wav(1.0, sample_rate=16000)

    assert isinstance(wav_bytes, bytes)
    assert wav_bytes[:4] == b"RIFF", "Must start with RIFF header"


def test_make_silent_wav_correct_duration():
    sample_rate = 16000
    duration_s = 2.0
    wav_bytes = _bm._make_silent_wav(duration_s, sample_rate=sample_rate)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    with wave.open(tmp_path, "rb") as wf:
        assert wf.getnframes() == int(duration_s * sample_rate)
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == sample_rate

    Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# RunResult.compute_stats
# ---------------------------------------------------------------------------

def test_compute_stats_median_and_p95():
    result = _bm.RunResult(
        model="small", device="cpu", compute_type="int8",
        audio_file="test.wav", audio_duration_s=2.0, run_count=10,
        latencies_ms=[100.0, 200.0, 150.0, 120.0, 300.0,
                      110.0, 180.0, 130.0, 140.0, 500.0],
    )
    result.compute_stats()

    # sorted: [100, 110, 120, 130, 140, 150, 180, 200, 300, 500]
    # median index 5 → 150.0
    assert result.median_ms == 150.0
    # p95 index max(0, int(10*0.95)-1) = 8 → 300.0
    assert result.p95_ms == 300.0
    assert result.min_ms == 100.0
    assert result.max_ms == 500.0


def test_compute_stats_single_run():
    result = _bm.RunResult(
        model="small", device="cpu", compute_type="int8",
        audio_file="x.wav", audio_duration_s=1.0, run_count=1,
        latencies_ms=[42.0],
    )
    result.compute_stats()

    assert result.median_ms == 42.0
    assert result.p95_ms == 42.0
    assert result.min_ms == 42.0
    assert result.max_ms == 42.0


def test_compute_stats_empty_does_not_raise():
    result = _bm.RunResult(
        model="small", device="cpu", compute_type="int8",
        audio_file="x.wav", audio_duration_s=1.0, run_count=0,
    )
    result.compute_stats()  # no-op on empty latencies
    assert result.median_ms == 0.0


# ---------------------------------------------------------------------------
# save_json / save_csv
# ---------------------------------------------------------------------------

def _make_result(**overrides):
    defaults = dict(
        model="small", device="cpu", compute_type="int8",
        audio_file="silence_2s.wav", audio_duration_s=2.0,
        run_count=3, latencies_ms=[100.0, 120.0, 110.0],
        median_ms=110.0, p95_ms=120.0, min_ms=100.0, max_ms=120.0,
        ram_before_mb=200.0, ram_after_mb=210.0, ram_delta_mb=10.0,
        timestamp="2026-05-23T00:00:00+00:00",
        python_version="3.10.0", platform_info="Linux-5.15-aarch64",
    )
    defaults.update(overrides)
    return _bm.RunResult(**defaults)


def test_save_json_writes_valid_json(tmp_path):
    results = [_make_result(), _make_result(model="medium")]
    out = tmp_path / "results.json"
    _bm.save_json(results, out)

    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["model"] == "small"
    assert data[1]["model"] == "medium"
    assert "latencies_ms" in data[0]


def test_save_csv_writes_valid_csv(tmp_path):
    results = [_make_result(), _make_result(model="medium")]
    out = tmp_path / "results.csv"
    _bm.save_csv(results, out)

    rows = list(csv.DictReader(out.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 2
    assert rows[0]["model"] == "small"
    assert rows[1]["model"] == "medium"
    assert "median_ms" in rows[0]
    assert "p95_ms" in rows[0]


def test_save_csv_is_noop_for_empty_list(tmp_path):
    out = tmp_path / "empty.csv"
    _bm.save_csv([], out)
    assert not out.exists()


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def test_parse_args_defaults():
    args = _bm._parse_args([])
    assert args.models == ["small", "medium"]
    assert args.device == "cpu"
    assert args.compute_type == "int8"
    assert args.runs == 10
    assert not args.no_vad


def test_parse_args_custom_models_and_runs():
    args = _bm._parse_args(["--models", "tiny", "medium", "--runs", "5"])
    assert args.models == ["tiny", "medium"]
    assert args.runs == 5


def test_parse_args_no_vad_flag():
    args = _bm._parse_args(["--no-vad"])
    assert args.no_vad is True


def test_parse_args_cuda_device():
    args = _bm._parse_args(["--device", "cuda", "--compute-type", "float16"])
    assert args.device == "cuda"
    assert args.compute_type == "float16"


# ---------------------------------------------------------------------------
# main() — early-exit paths (no faster-whisper, missing dir)
# ---------------------------------------------------------------------------

def test_main_exits_1_when_audio_dir_missing(tmp_path):
    exit_code = _bm.main([
        "--audio-dir", str(tmp_path / "does_not_exist"),
        "--output-dir", str(tmp_path),
    ])
    assert exit_code == 1


def test_main_exits_1_when_audio_dir_has_no_wav_files(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    (audio_dir / "README.txt").write_text("not a wav")

    exit_code = _bm.main([
        "--audio-dir", str(audio_dir),
        "--output-dir", str(tmp_path),
    ])
    assert exit_code == 1


def test_main_exits_1_when_faster_whisper_not_installed(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    (audio_dir / "test.wav").write_bytes(_bm._make_silent_wav(0.5))

    with patch.dict(sys.modules, {"faster_whisper": None}):
        exit_code = _bm.main([
            "--audio-dir", str(audio_dir),
            "--output-dir", str(tmp_path),
        ])
    assert exit_code == 1


# ---------------------------------------------------------------------------
# run_model_benchmark — mock SpeechToText
# ---------------------------------------------------------------------------

def test_run_model_benchmark_with_mock_stt(tmp_path):
    """Loop calls transcribe() (1 warmup + N*files) and records latencies."""
    import asyncio

    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    wav = _bm._make_silent_wav(1.0)
    paths = [audio_dir / "a.wav", audio_dir / "b.wav"]
    for p in paths:
        p.write_bytes(wav)

    call_log: list[str] = []

    class MockSTT:
        def __init__(self, **_):
            pass

        async def transcribe(self, audio_bytes, **_):
            call_log.append("t")
            return {"text": "", "segments": [], "language": "tr",
                    "language_probability": 0.9, "low_confidence": False}

    with patch("robot_waiter_ai.speech.stt.SpeechToText", MockSTT):
        results = _bm.run_model_benchmark(
            model_size="small",
            audio_paths=paths,
            device="cpu",
            compute_type="int8",
            runs=3,
        )

    # 1 warmup + 2 files * 3 runs = 7 calls
    assert len(call_log) == 7
    assert len(results) == 2
    for r in results:
        assert r.run_count == 3
        assert len(r.latencies_ms) == 3
        assert r.median_ms > 0
        assert r.model == "small"


# ---------------------------------------------------------------------------
# _rss_mb
# ---------------------------------------------------------------------------

def test_rss_mb_returns_non_negative_float():
    mb = _bm._rss_mb()
    assert isinstance(mb, float)
    assert mb >= 0.0
