"""
scripts/benchmark_stt.py — STT latency & RAM benchmark for Jetson Orin NX.

Compares faster-whisper model sizes (small, medium, …) on a set of WAV files.
Writes results to JSON and CSV under benchmarks/.

Usage
-----
Run on Jetson (or any machine) after installing requirements.txt:

    python scripts/benchmark_stt.py
    python scripts/benchmark_stt.py --models small medium --runs 10
    python scripts/benchmark_stt.py --models small --device cuda --compute-type float16 --runs 5

The script:
1. Warms up each model with one silent transcription (loads weights, JIT-compiles).
2. Runs N timed transcriptions per WAV file.
3. Reports median & p95 latency plus peak RSS memory delta per model.
4. Writes benchmarks/stt_<TIMESTAMP>.json and .csv.

Design notes
------------
* SpeechToText is imported from the project package — no duplication.
* Peak RAM is measured via /proc/self/status (Linux) or resource.getrusage
  (macOS / fallback).  On Jetson, both DRAM and swap are unified so RSS ≈ real use.
* asyncio.run() is intentional: each run is isolated just as a real request would be.
* Model loading happens once per model size during warm-up; inference runs re-use
  the loaded model.
* The script is safe to import in tests without triggering any I/O side effects.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import os
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List

# Ensure the project root is on sys.path when run as a script.
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_MODELS: list[str] = ["small", "medium"]
DEFAULT_DEVICE: str = "cpu"
DEFAULT_COMPUTE_TYPE: str = "int8"
DEFAULT_RUNS: int = 10
DEFAULT_AUDIO_DIR: Path = _SCRIPT_DIR / "benchmark_audio"
DEFAULT_OUTPUT_DIR: Path = _PROJECT_ROOT / "benchmarks"
WARMUP_AUDIO_DURATION_S: float = 0.5   # length of the silent warm-up clip


# ---------------------------------------------------------------------------
# RAM helpers
# ---------------------------------------------------------------------------

def _rss_mb() -> float:
    """Return current process RSS memory in megabytes.

    Uses /proc/self/status on Linux (Jetson) for accuracy.
    Falls back to resource.getrusage on macOS / unsupported platforms.
    """
    if platform.system() == "Linux":
        try:
            with open("/proc/self/status", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        kb = int(line.split()[1])
                        return kb / 1024.0
        except OSError:
            pass

    try:
        import resource
        kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # On Linux ru_maxrss is in KB; on macOS it is in bytes.
        if platform.system() == "Darwin":
            return kb / (1024.0 * 1024.0)
        return kb / 1024.0
    except ImportError:
        return 0.0


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class RunResult:
    """Timing and memory data for one (model, audio_file) pair."""

    model: str
    device: str
    compute_type: str
    audio_file: str
    audio_duration_s: float
    run_count: int
    latencies_ms: list[float] = field(default_factory=list)
    median_ms: float = 0.0
    p95_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    ram_before_mb: float = 0.0
    ram_after_mb: float = 0.0
    ram_delta_mb: float = 0.0
    timestamp: str = ""
    python_version: str = ""
    platform_info: str = ""

    def compute_stats(self) -> None:
        """Derive median, p95, min, max from latencies_ms."""
        if not self.latencies_ms:
            return
        sorted_lat = sorted(self.latencies_ms)
        n = len(sorted_lat)
        self.median_ms = sorted_lat[n // 2]
        p95_idx = max(0, int(n * 0.95) - 1)
        self.p95_ms = sorted_lat[p95_idx]
        self.min_ms = sorted_lat[0]
        self.max_ms = sorted_lat[-1]


# ---------------------------------------------------------------------------
# WAV duration helper
# ---------------------------------------------------------------------------

def _wav_duration_s(wav_path: Path) -> float:
    """Return WAV file duration in seconds (stdlib only)."""
    import wave as wave_module
    try:
        with wave_module.open(str(wav_path), "rb") as wf:
            return wf.getnframes() / wf.getframerate()
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Silent warm-up WAV
# ---------------------------------------------------------------------------

def _make_silent_wav(duration_s: float, sample_rate: int = 16000) -> bytes:
    """Return a silent WAV bytes object (16-bit PCM, mono) of *duration_s* seconds."""
    import io
    import struct
    import wave as wave_module

    num_frames = int(duration_s * sample_rate)
    buf = io.BytesIO()
    with wave_module.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Core benchmark runner
# ---------------------------------------------------------------------------

def run_model_benchmark(
    model_size: str,
    audio_paths: list[Path],
    *,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
    runs: int = DEFAULT_RUNS,
    use_vad: bool = True,
) -> list[RunResult]:
    """Benchmark a single model size against all *audio_paths*.

    Returns one RunResult per audio file.
    """
    from robot_waiter_ai.speech.stt import SpeechToText

    stt = SpeechToText(
        model_size=model_size,
        device=device,
        compute_type=compute_type,
    )

    # ---- Warm-up: load model weights (not timed) ----------------------------
    print(f"  [{model_size}] Warm-up (model loading)…", end=" ", flush=True)
    warmup_bytes = _make_silent_wav(WARMUP_AUDIO_DURATION_S)
    t_warmup_start = time.perf_counter()
    asyncio.run(stt.transcribe(warmup_bytes, use_vad=False))
    warmup_s = time.perf_counter() - t_warmup_start
    print(f"done ({warmup_s * 1000:.0f} ms — model now loaded)")

    results: list[RunResult] = []

    for audio_path in audio_paths:
        audio_bytes = audio_path.read_bytes()
        duration_s = _wav_duration_s(audio_path)

        ram_before = _rss_mb()
        latencies: list[float] = []

        for i in range(runs):
            t0 = time.perf_counter()
            asyncio.run(stt.transcribe(audio_bytes, use_vad=use_vad))
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)
            print(
                f"  [{model_size}] {audio_path.name} run {i + 1}/{runs}: "
                f"{elapsed_ms:.0f} ms",
                flush=True,
            )

        ram_after = _rss_mb()

        result = RunResult(
            model=model_size,
            device=device,
            compute_type=compute_type,
            audio_file=audio_path.name,
            audio_duration_s=round(duration_s, 3),
            run_count=runs,
            latencies_ms=[round(x, 1) for x in latencies],
            ram_before_mb=round(ram_before, 1),
            ram_after_mb=round(ram_after, 1),
            ram_delta_mb=round(ram_after - ram_before, 1),
            timestamp=datetime.now(timezone.utc).isoformat(),
            python_version=sys.version,
            platform_info=platform.platform(),
        )
        result.compute_stats()
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def save_json(results: list[RunResult], output_path: Path) -> None:
    payload = [asdict(r) for r in results]
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  JSON → {output_path}")


def save_csv(results: list[RunResult], output_path: Path) -> None:
    if not results:
        return
    fieldnames = [
        "model", "device", "compute_type", "audio_file", "audio_duration_s",
        "run_count", "median_ms", "p95_ms", "min_ms", "max_ms",
        "ram_before_mb", "ram_after_mb", "ram_delta_mb",
        "timestamp", "platform_info",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))
    print(f"  CSV  → {output_path}")


def print_summary(results: list[RunResult]) -> None:
    print("\n" + "=" * 70)
    print(f"{'Model':<10} {'File':<22} {'Median':>8} {'p95':>8} {'Min':>8} {'Max':>8} {'ΔRAM':>8}")
    print(f"{'':10} {'':22} {'(ms)':>8} {'(ms)':>8} {'(ms)':>8} {'(ms)':>8} {'(MB)':>8}")
    print("-" * 70)
    for r in results:
        print(
            f"{r.model:<10} {r.audio_file:<22} "
            f"{r.median_ms:>8.0f} {r.p95_ms:>8.0f} "
            f"{r.min_ms:>8.0f} {r.max_ms:>8.0f} "
            f"{r.ram_delta_mb:>8.1f}"
        )
    print("=" * 70)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark faster-whisper STT latency and RAM on Jetson or desktop.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        metavar="MODEL",
        help="faster-whisper model size(s) to benchmark (e.g. small medium large-v2)",
    )
    parser.add_argument(
        "--device",
        default=DEFAULT_DEVICE,
        choices=("cpu", "cuda"),
        help="Compute device",
    )
    parser.add_argument(
        "--compute-type",
        default=DEFAULT_COMPUTE_TYPE,
        choices=("int8", "float16", "float32"),
        help="Quantisation type",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_RUNS,
        help="Number of timed transcription runs per (model, audio_file) pair",
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=DEFAULT_AUDIO_DIR,
        help="Directory containing .wav benchmark audio files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where JSON and CSV results are written",
    )
    parser.add_argument(
        "--no-vad",
        action="store_true",
        help="Disable faster-whisper VAD filter (measures raw decode latency)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    args = _parse_args(argv)
    audio_dir: Path = args.audio_dir
    output_dir: Path = args.output_dir

    # ---- Validate audio directory ------------------------------------------
    if not audio_dir.exists():
        print(
            f"ERROR: Audio directory not found: {audio_dir}\n"
            f"       Create WAV files there or pass --audio-dir <path>.",
            file=sys.stderr,
        )
        return 1

    audio_paths = sorted(audio_dir.glob("*.wav"))
    if not audio_paths:
        print(
            f"ERROR: No .wav files found in {audio_dir}.",
            file=sys.stderr,
        )
        return 1

    # ---- Check faster-whisper availability ---------------------------------
    try:
        from faster_whisper import WhisperModel  # noqa: F401 — availability check
    except ImportError:
        print(
            "ERROR: faster-whisper is not installed.\n"
            "       Run: pip install faster-whisper",
            file=sys.stderr,
        )
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    print(f"\nGarson-bot STT Benchmark")
    print(f"  Models       : {', '.join(args.models)}")
    print(f"  Device       : {args.device} / {args.compute_type}")
    print(f"  Runs / file  : {args.runs}")
    print(f"  Audio dir    : {audio_dir}  ({len(audio_paths)} file(s))")
    print(f"  Output dir   : {output_dir}")
    print()

    all_results: list[RunResult] = []

    for model_size in args.models:
        print(f"--- Model: {model_size} ---")
        results = run_model_benchmark(
            model_size=model_size,
            audio_paths=audio_paths,
            device=args.device,
            compute_type=args.compute_type,
            runs=args.runs,
            use_vad=not args.no_vad,
        )
        all_results.extend(results)
        print()

    # ---- Save results -------------------------------------------------------
    print("Saving results…")
    json_path = output_dir / f"stt_{timestamp_tag}.json"
    csv_path = output_dir / f"stt_{timestamp_tag}.csv"
    save_json(all_results, json_path)
    save_csv(all_results, csv_path)

    print_summary(all_results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
