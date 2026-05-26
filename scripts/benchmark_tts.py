"""
scripts/benchmark_tts.py — TTS latency, TTFA, and RAM benchmark.

Compares edge-tts (online, current default) vs Piper TTS (offline, local) on
a set of Turkish restaurant sentences.  Helps decide which engine to use in
production on the Jetson Orin NX.

Metrics per (engine, voice, sentence):
  latency_ms  — wall-clock time from start to complete audio bytes
  ttfa_ms     — time to first audio chunk (streaming mode; Piper: N/A)
  audio_bytes — total synthesised audio size in bytes
  chars_per_s — characters per second throughput

Usage
-----
    python scripts/benchmark_tts.py
    python scripts/benchmark_tts.py --engines edge-tts
    python scripts/benchmark_tts.py --engines piper --piper-model models/tr_TR-fahrettin-medium.onnx
    python scripts/benchmark_tts.py --runs 5 --output-dir benchmarks/

Requirements
------------
  edge-tts : pip install edge-tts  (requires internet)
  Piper    : https://github.com/rhasspy/piper/releases  (binary + .onnx model)
             OR pip install piper-tts  (includes binary on some platforms)
             Recommended Turkish model: tr_TR-fahrettin-medium.onnx

Design notes
------------
* edge-tts latency includes round-trip network time — run on the same Wi-Fi
  as the Jetson to get realistic production numbers.
* Piper latency is pure local CPU/GPU inference — deterministic across runs.
* TTFA (time-to-first-audio) matters for perceived responsiveness; edge-tts
  streams chunks so TTFA is typically 200-600 ms; Piper outputs all at once.
* RAM delta is measured via /proc/self/status (Linux) or resource.getrusage.
* The script is safe to import in tests: no I/O at module level.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import os
import platform
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_ENGINES: list[str] = ["edge-tts"]
DEFAULT_RUNS: int = 5
DEFAULT_OUTPUT_DIR: Path = _PROJECT_ROOT / "benchmarks"

# Sentences cover short, medium, and long Turkish restaurant utterances,
# including characters with diacritics (ı, ü, ö, ç, ş, ğ).
DEFAULT_SENTENCES: list[str] = [
    "Merhaba!",
    "Siparişinizi alıyorum.",
    "Teşekkür ederim, afiyet olsun.",
    "Bugün şefin önerisi mercimek çorbası ve kuzu tandır.",
    "Siparişinizi onayladım: iki kişilik masa, bir adet döner dürüm ve iki ayran.",
]

# Default edge-tts Turkish voices to test.
DEFAULT_EDGE_VOICES: list[str] = [
    "tr-TR-EmelNeural",
    "tr-TR-AhmetNeural",
]

# Where to look for the Piper binary when --piper-binary is not set.
_PIPER_BINARY_CANDIDATES: list[str] = [
    "piper",
    str(_PROJECT_ROOT / "piper" / "piper"),
    str(_PROJECT_ROOT / "piper" / "piper.exe"),
    str(_SCRIPT_DIR / "piper"),
    str(_SCRIPT_DIR / "piper.exe"),
]

# Where to look for the Turkish Piper model when --piper-model is not set.
_PIPER_MODEL_CANDIDATES: list[Path] = [
    _PROJECT_ROOT / "robot_waiter_ai" / "models" / "tr_TR-fahrettin-medium.onnx",
    _PROJECT_ROOT / "robot_waiter_ai" / "models" / "tr_TR-fahrettin-high.onnx",
    _PROJECT_ROOT / "models" / "tr_TR-fahrettin-medium.onnx",
    _PROJECT_ROOT / "models" / "tr_TR-fahrettin-high.onnx",
    _SCRIPT_DIR / "tr_TR-fahrettin-medium.onnx",
]


# ---------------------------------------------------------------------------
# RAM helper
# ---------------------------------------------------------------------------

def _rss_mb() -> float:
    if platform.system() == "Linux":
        try:
            with open("/proc/self/status", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) / 1024.0
        except OSError:
            pass
    try:
        import resource
        kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return kb / (1024.0 * 1024.0) if platform.system() == "Darwin" else kb / 1024.0
    except ImportError:
        return 0.0


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class TTSResult:
    engine: str
    voice: str
    text: str
    text_chars: int
    run_count: int
    latencies_ms: list[float] = field(default_factory=list)
    ttfa_ms_list: list[float] = field(default_factory=list)   # edge-tts only
    audio_sizes_bytes: list[int] = field(default_factory=list)
    median_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    median_ttfa_ms: float = 0.0
    median_audio_bytes: int = 0
    chars_per_s: float = 0.0
    ram_before_mb: float = 0.0
    ram_after_mb: float = 0.0
    ram_delta_mb: float = 0.0
    timestamp: str = ""
    platform_info: str = ""

    def compute_stats(self) -> None:
        if not self.latencies_ms:
            return
        s = sorted(self.latencies_ms)
        n = len(s)
        self.median_latency_ms = s[n // 2]
        self.p95_latency_ms = s[max(0, int(n * 0.95) - 1)]
        self.min_latency_ms = s[0]
        self.max_latency_ms = s[-1]
        if self.ttfa_ms_list:
            tf = sorted(self.ttfa_ms_list)
            self.median_ttfa_ms = tf[len(tf) // 2]
        if self.audio_sizes_bytes:
            self.median_audio_bytes = sorted(self.audio_sizes_bytes)[len(self.audio_sizes_bytes) // 2]
        if self.median_latency_ms > 0:
            self.chars_per_s = round(self.text_chars / (self.median_latency_ms / 1000.0), 1)


# ---------------------------------------------------------------------------
# edge-tts benchmark
# ---------------------------------------------------------------------------

async def _edge_single_run(tts, text: str) -> tuple[float, float, int]:
    """One streaming synthesis run.  Returns (latency_ms, ttfa_ms, audio_bytes)."""
    chunks: list[bytes] = []
    ttfa_ms = 0.0
    t0 = time.perf_counter()
    async for chunk in tts.synthesize_streaming(text):
        if not chunks:
            ttfa_ms = (time.perf_counter() - t0) * 1000.0
        chunks.append(chunk)
    latency_ms = (time.perf_counter() - t0) * 1000.0
    audio_bytes = sum(len(c) for c in chunks)
    return latency_ms, ttfa_ms, audio_bytes


def benchmark_edge_tts(
    sentences: list[str],
    voices: list[str],
    runs: int,
) -> list[TTSResult]:
    # Check edge-tts availability upfront — fail fast before any looping.
    try:
        import edge_tts as _edge_tts_check  # noqa: F401
    except ImportError:
        print("  [edge-tts] Not installed. Run: pip install edge-tts", file=sys.stderr)
        return []

    try:
        from robot_waiter_ai.speech.tts import TextToSpeech
    except ImportError as exc:
        print(f"  [edge-tts] Cannot import TextToSpeech: {exc}", file=sys.stderr)
        return []

    results: list[TTSResult] = []
    ts = datetime.now(timezone.utc).isoformat()
    plat = platform.platform()

    for voice in voices:
        tts = TextToSpeech(voice=voice)
        for text in sentences:
            print(f"  [edge-tts / {voice}] {text[:40]!r}…", flush=True)
            ram_before = _rss_mb()
            latencies, ttfas, sizes = [], [], []

            for i in range(runs):
                try:
                    lat, ttfa, sz = asyncio.run(_edge_single_run(tts, text))
                except Exception as exc:
                    print(f"    run {i+1}/{runs} FAILED: {exc}", file=sys.stderr)
                    continue
                latencies.append(round(lat, 1))
                ttfas.append(round(ttfa, 1))
                sizes.append(sz)
                print(
                    f"    run {i+1}/{runs}: latency={lat:.0f} ms  "
                    f"ttfa={ttfa:.0f} ms  audio={sz:,} bytes",
                    flush=True,
                )

            ram_after = _rss_mb()
            r = TTSResult(
                engine="edge-tts",
                voice=voice,
                text=text,
                text_chars=len(text),
                run_count=len(latencies),
                latencies_ms=latencies,
                ttfa_ms_list=ttfas,
                audio_sizes_bytes=sizes,
                ram_before_mb=round(ram_before, 1),
                ram_after_mb=round(ram_after, 1),
                ram_delta_mb=round(ram_after - ram_before, 1),
                timestamp=ts,
                platform_info=plat,
            )
            r.compute_stats()
            results.append(r)

    return results


# ---------------------------------------------------------------------------
# Piper TTS benchmark
# ---------------------------------------------------------------------------

def _find_piper_binary(override: Optional[str]) -> Optional[str]:
    import shutil
    if override:
        return override if Path(override).is_file() else None
    for candidate in _PIPER_BINARY_CANDIDATES:
        p = Path(candidate)
        if p.is_file() and os.access(str(p), os.X_OK):
            return str(p)
        # Also check PATH (only makes sense for bare names, not paths)
        if "/" not in candidate:
            found = shutil.which(candidate)
            if found:
                return found
    return None


def _find_piper_model(override: Optional[str]) -> Optional[Path]:
    if override:
        return Path(override) if Path(override).exists() else None
    for candidate in _PIPER_MODEL_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def _piper_single_run(binary: str, model: Path, text: str) -> tuple[float, int]:
    """Run piper once; return (latency_ms, audio_bytes)."""
    cmd = [
        binary,
        "--model", str(model),
        "--output-raw",   # raw PCM to stdout
        "--quiet",
    ]
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        input=text.encode("utf-8"),
        capture_output=True,
        timeout=30,
    )
    latency_ms = (time.perf_counter() - t0) * 1000.0
    if proc.returncode != 0:
        raise RuntimeError(
            f"piper exited {proc.returncode}: {proc.stderr.decode(errors='replace')[:200]}"
        )
    return latency_ms, len(proc.stdout)


def benchmark_piper(
    sentences: list[str],
    runs: int,
    piper_binary: Optional[str] = None,
    piper_model: Optional[str] = None,
) -> list[TTSResult]:
    binary = _find_piper_binary(piper_binary)
    if not binary:
        print(
            "  [piper] Binary not found.  Install from:\n"
            "    https://github.com/rhasspy/piper/releases\n"
            "  or pass --piper-binary <path>",
            file=sys.stderr,
        )
        return []

    model = _find_piper_model(piper_model)
    if not model:
        print(
            "  [piper] Turkish model not found.  Download:\n"
            "    https://huggingface.co/rhasspy/piper-voices/tree/main/tr/tr_TR/fahrettin/medium\n"
            "  Save to: robot_waiter_ai/models/tr_TR-fahrettin-medium.onnx\n"
            "  or pass --piper-model <path>",
            file=sys.stderr,
        )
        return []

    print(f"  [piper] binary={binary}  model={model.name}", flush=True)
    results: list[TTSResult] = []
    ts = datetime.now(timezone.utc).isoformat()
    plat = platform.platform()

    for text in sentences:
        print(f"  [piper] {text[:40]!r}…", flush=True)
        ram_before = _rss_mb()
        latencies, sizes = [], []

        for i in range(runs):
            try:
                lat, sz = _piper_single_run(binary, model, text)
            except Exception as exc:
                print(f"    run {i+1}/{runs} FAILED: {exc}", file=sys.stderr)
                continue
            latencies.append(round(lat, 1))
            sizes.append(sz)
            print(
                f"    run {i+1}/{runs}: latency={lat:.0f} ms  audio={sz:,} bytes",
                flush=True,
            )

        ram_after = _rss_mb()
        r = TTSResult(
            engine="piper",
            voice=str(model.stem),
            text=text,
            text_chars=len(text),
            run_count=len(latencies),
            latencies_ms=latencies,
            ttfa_ms_list=[],        # Piper outputs all at once
            audio_sizes_bytes=sizes,
            ram_before_mb=round(ram_before, 1),
            ram_after_mb=round(ram_after, 1),
            ram_delta_mb=round(ram_after - ram_before, 1),
            timestamp=ts,
            platform_info=plat,
        )
        r.compute_stats()
        results.append(r)

    return results


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def save_json(results: list[TTSResult], output_path: Path) -> None:
    output_path.write_text(
        json.dumps([asdict(r) for r in results], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  JSON -> {output_path}")


def save_csv(results: list[TTSResult], output_path: Path) -> None:
    if not results:
        return
    fieldnames = [
        "engine", "voice", "text", "text_chars", "run_count",
        "median_latency_ms", "p95_latency_ms", "min_latency_ms", "max_latency_ms",
        "median_ttfa_ms", "median_audio_bytes", "chars_per_s",
        "ram_before_mb", "ram_after_mb", "ram_delta_mb",
        "timestamp", "platform_info",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))
    print(f"  CSV  -> {output_path}")


def print_summary(results: list[TTSResult]) -> None:
    if not results:
        print("  (no results to display)")
        return

    print()
    print("=" * 88)
    print(
        f"{'Engine':<10} {'Voice':<24} {'Chars':>5} "
        f"{'Median':>8} {'p95':>8} {'TTFA':>8} {'B/run':>8} {'ch/s':>6}"
    )
    print(
        f"{'':10} {'':24} {'':5} "
        f"{'(ms)':>8} {'(ms)':>8} {'(ms)':>8} {'(bytes)':>8} {'':6}"
    )
    print("-" * 88)
    for r in results:
        ttfa = f"{r.median_ttfa_ms:.0f}" if r.median_ttfa_ms else "  n/a"
        short_text = (r.text[:20] + "...") if len(r.text) > 20 else r.text
        print(
            f"{r.engine:<10} {r.voice:<24} {r.text_chars:>5} "
            f"{r.median_latency_ms:>8.0f} {r.p95_latency_ms:>8.0f} "
            f"{ttfa:>8} {r.median_audio_bytes:>8,} {r.chars_per_s:>6.0f}"
        )
    print("=" * 88)

    # Decision hint
    print()
    edge_results = [r for r in results if r.engine == "edge-tts"]
    piper_results = [r for r in results if r.engine == "piper"]
    if edge_results and piper_results:
        edge_med = sum(r.median_latency_ms for r in edge_results) / len(edge_results)
        piper_med = sum(r.median_latency_ms for r in piper_results) / len(piper_results)
        faster = "edge-tts" if edge_med < piper_med else "piper"
        print(f"  Throughput comparison:")
        print(f"    edge-tts avg median latency : {edge_med:.0f} ms")
        print(f"    piper    avg median latency : {piper_med:.0f} ms")
        print(f"    Faster engine               : {faster}")
        print()
        print("  NOTE: edge-tts requires internet; Piper runs fully offline.")
        print("        For Jetson production use, prefer Piper if latency < 300 ms.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark edge-tts vs Piper TTS latency, TTFA, and RAM.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--engines",
        nargs="+",
        default=DEFAULT_ENGINES,
        choices=("edge-tts", "piper"),
        metavar="ENGINE",
        help="TTS engine(s) to benchmark: edge-tts, piper",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_RUNS,
        help="Number of timed synthesis runs per (engine, voice, sentence)",
    )
    parser.add_argument(
        "--edge-voices",
        nargs="+",
        default=DEFAULT_EDGE_VOICES,
        metavar="VOICE",
        help="edge-tts voice names to benchmark",
    )
    parser.add_argument(
        "--sentences",
        nargs="+",
        default=None,
        metavar="TEXT",
        help="Custom Turkish sentences to synthesise (overrides defaults)",
    )
    parser.add_argument(
        "--piper-binary",
        default=None,
        metavar="PATH",
        help="Path to the piper binary (auto-detected if omitted)",
    )
    parser.add_argument(
        "--piper-model",
        default=None,
        metavar="PATH",
        help="Path to Piper .onnx model file (auto-detected if omitted)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        metavar="DIR",
        help="Directory where JSON and CSV results are written",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    args = _parse_args(argv)
    sentences = args.sentences or DEFAULT_SENTENCES
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    print()
    print("Garson-bot TTS Benchmark")
    print(f"  Engines      : {', '.join(args.engines)}")
    print(f"  Runs / sent. : {args.runs}")
    print(f"  Sentences    : {len(sentences)}")
    print(f"  Output dir   : {output_dir}")
    print()

    all_results: list[TTSResult] = []

    if "edge-tts" in args.engines:
        print("--- edge-tts ---")
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            print("  edge-tts not installed. Run: pip install edge-tts", file=sys.stderr)
        else:
            results = benchmark_edge_tts(
                sentences=sentences,
                voices=args.edge_voices,
                runs=args.runs,
            )
            all_results.extend(results)
        print()

    if "piper" in args.engines:
        print("--- piper ---")
        results = benchmark_piper(
            sentences=sentences,
            runs=args.runs,
            piper_binary=args.piper_binary,
            piper_model=args.piper_model,
        )
        all_results.extend(results)
        print()

    if not all_results:
        print("No results collected. Check engine availability above.", file=sys.stderr)
        return 1

    print("Saving results...")
    json_path = output_dir / f"tts_{timestamp_tag}.json"
    csv_path = output_dir / f"tts_{timestamp_tag}.csv"
    save_json(all_results, json_path)
    save_csv(all_results, csv_path)

    print_summary(all_results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
