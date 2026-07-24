#!/usr/bin/env python3
"""
W-BOT TTS Kayıt Scripti — Piper/VITS eğitimi için corpus kaydı
22050 Hz mono 16-bit WAV, cümle başına ayrı dosya.

Kullanım:
    python scripts/record_corpus.py
    python scripts/record_corpus.py --device 3
    python scripts/record_corpus.py --list-devices
    python scripts/record_corpus.py --corpus scripts/tts_corpus.txt --out data/recordings
"""

import argparse
import json
import os
import sys
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

# ── Sabitler ──────────────────────────────────────────────────────────────────
SAMPLE_RATE   = 22050
CHANNELS      = 1
DTYPE         = "int16"
BLOCKSIZE     = 1024

SCRIPT_DIR    = Path(__file__).parent
PROJECT_ROOT  = SCRIPT_DIR.parent
CORPUS_FILE   = SCRIPT_DIR / "tts_corpus.txt"
OUT_DIR       = PROJECT_ROOT / "data" / "recordings"
PROGRESS_FILE = OUT_DIR / ".corpus_progress.json"
FILE_PREFIX   = "corpus_"

# ── Platform key capture (stdlib only, no pynput/keyboard) ────────────────────
if sys.platform == "win32":
    import msvcrt

    def _get_key() -> str:
        ch = msvcrt.getch()
        # Arrow / function keys send two bytes; swallow the second
        if ch in (b"\xe0", b"\x00"):
            msvcrt.getch()
            return ""
        return ch.decode("utf-8", errors="ignore").lower()

    def _wait_for_enter():
        while True:
            ch = msvcrt.getch()
            if ch in (b"\r", b"\n"):
                return
else:
    import termios
    import tty

    def _get_key() -> str:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1).lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def _wait_for_enter():
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch in ("\r", "\n"):
                    return
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


# ── Corpus ────────────────────────────────────────────────────────────────────
def load_corpus(path: Path) -> list[tuple[str, str]]:
    """(cümle, kategori) listesi döner; # satırları kategori başlığıdır."""
    sentences = []
    current_cat = ""
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                current_cat = line.lstrip("#").strip()
                # "── X. KATEGORİ: ..." → sadece etiket kısmı
                if ":" in current_cat:
                    current_cat = current_cat.split(":", 1)[1].strip()
                # parantez içini temizle: "Karşılama (40 cümle)" → "Karşılama"
                if "(" in current_cat:
                    current_cat = current_cat.split("(")[0].strip()
            else:
                sentences.append((line, current_cat))
    return sentences


# ── İlerleme ──────────────────────────────────────────────────────────────────
def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"recorded": [], "skipped": []}


def save_progress(progress: dict):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# ── WAV kaydet ────────────────────────────────────────────────────────────────
def save_wav(audio: np.ndarray, path: Path):
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())


def _find_record_rate(device) -> int:
    """Cihazın desteklediği ilk sample rate'i döner (22050 öncelikli)."""
    for rate in [22050, 44100, 48000, 96000]:
        try:
            with sd.InputStream(samplerate=rate, channels=CHANNELS, dtype=DTYPE,
                                device=device, blocksize=BLOCKSIZE):
                return rate
        except sd.PortAudioError:
            continue
    raise RuntimeError("Desteklenen sample rate bulunamadı.")


def _resample(audio: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
    """Linear interpolation ile yeniden örnekleme (speech için yeterli)."""
    if from_rate == to_rate:
        return audio
    n = int(len(audio) * to_rate / from_rate)
    return np.interp(np.linspace(0, len(audio) - 1, n),
                     np.arange(len(audio)), audio).astype(np.int16)


# ── Kayıt ─────────────────────────────────────────────────────────────────────
def record_until_enter(device=None) -> tuple:
    """
    Native sample rate'de kayıt edip (audio, record_rate) döner.
    Çağıran SAMPLE_RATE'e resample eder.
    """
    record_rate = _find_record_rate(device)
    chunks: list[np.ndarray] = []
    stop_flag = [False]

    def _cb(indata, frames, time, status):
        if not stop_flag[0]:
            chunks.append(indata.copy())

    stream = sd.InputStream(
        samplerate=record_rate,
        channels=CHANNELS,
        dtype=DTYPE,
        device=device,
        blocksize=BLOCKSIZE,
        callback=_cb,
    )
    with stream:
        if record_rate != SAMPLE_RATE:
            print(f"  \033[91m●\033[0m KAYIT ({record_rate} Hz → {SAMPLE_RATE} Hz)  — ENTER ile durdur", flush=True)
        else:
            print("  \033[91m●\033[0m KAYIT  — ENTER ile durdur", flush=True)
        _wait_for_enter()
        stop_flag[0] = True

    if not chunks:
        return None, record_rate
    return np.concatenate(chunks, axis=0).flatten(), record_rate


# ── Ekran ─────────────────────────────────────────────────────────────────────
def clear():
    os.system("cls" if sys.platform == "win32" else "clear")


def show_sentence_screen(idx: int, total: int, cat: str, sentence: str):
    clear()
    sep = "─" * 55
    print("═" * 55)
    print("  W-BOT TTS Kayıt Scripti")
    print("═" * 55)
    print(f"\n  [ {idx + 1:3d} / {total} ]  {cat}")
    print(f"  {sep}")
    print(f'\n    \033[1m"{sentence}"\033[0m\n')
    print(f"  {sep}")
    print("\n  [SPACE] Kayda başla   [S] Atla   [R] Tekrar   [Q] Çık\n")


# ── Ana döngü ─────────────────────────────────────────────────────────────────
def run(corpus_path: Path, out_dir: Path, device=None):
    global PROGRESS_FILE
    PROGRESS_FILE = out_dir / ".corpus_progress.json"

    out_dir.mkdir(parents=True, exist_ok=True)

    sentences = load_corpus(corpus_path)
    total = len(sentences)
    if total == 0:
        print("Corpus boş, çıkılıyor.")
        return

    progress   = load_progress()
    recorded   = set(progress.get("recorded", []))
    skipped    = set(progress.get("skipped", []))

    # Başlangıç özeti
    clear()
    print("═" * 55)
    print("  W-BOT TTS Kayıt Scripti")
    print(f"  Corpus : {corpus_path.name}  ({total} cümle)")
    print(f"  Çıktı  : {out_dir}")
    print("═" * 55)
    print(f"""
  ! Kayıt öncesi kontrol:
    - Klima / fan / buzdolabı kapalı mı?
    - Mikrofon ağzınızdan 20-30 cm uzakta mı?
    - Telefon sessiz modda mı?
    - Pencereler kapalı mı?
""")
    done_count = len(recorded)
    skip_count = len(skipped)
    left_count = total - done_count - skip_count
    print(f"  Durum  : {done_count} kayıt  |  {skip_count} atlanan  |  {left_count} kalan")
    print("\n  Hazırsanız ENTER'a basın...", end="", flush=True)
    input()

    i = 0
    while i < total:
        if i in recorded or i in skipped:
            i += 1
            continue

        sentence, cat = sentences[i]
        show_sentence_screen(i, total, cat, sentence)

        # SPACE / S / Q / R bekle
        while True:
            key = _get_key()
            if not key:
                continue
            if key == "q":
                save_progress({"recorded": sorted(recorded), "skipped": sorted(skipped)})
                clear()
                print(f"\n  Çıkılıyor — ilerleme kaydedildi. ({len(recorded)}/{total})\n")
                return
            elif key == "s":
                skipped.add(i)
                save_progress({"recorded": sorted(recorded), "skipped": sorted(skipped)})
                i += 1
                break
            elif key == " ":
                # Kayda başla
                audio, rec_rate = record_until_enter(device=device)

                if audio is None or len(audio) < rec_rate * 0.3:
                    print("  \033[93m⚠\033[0m  Çok kısa kayıt (< 0.3 sn), tekrar deneyin.")
                    print("  ENTER ile devam...", end="", flush=True)
                    _wait_for_enter()
                    show_sentence_screen(i, total, cat, sentence)
                    continue

                if rec_rate != SAMPLE_RATE:
                    audio = _resample(audio, rec_rate, SAMPLE_RATE)

                duration = len(audio) / SAMPLE_RATE
                filename = out_dir / f"{FILE_PREFIX}{i + 1:04d}.wav"
                save_wav(audio, filename)
                print(f"\n  \033[92m✓\033[0m  {filename.name}  —  {duration:.1f} sn")
                print("  [SPACE] Sonraki   [R] Tekrar kayıt\n", flush=True)

                key2 = _get_key()
                if key2 == "r":
                    # WAV sil, aynı cümleyi tekrar kaydet
                    filename.unlink(missing_ok=True)
                    show_sentence_screen(i, total, cat, sentence)
                    continue
                else:
                    recorded.add(i)
                    save_progress({"recorded": sorted(recorded), "skipped": sorted(skipped)})
                    i += 1
                    break


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="W-BOT TTS corpus kayıt aracı"
    )
    parser.add_argument(
        "--corpus", type=Path, default=CORPUS_FILE,
        help=f"Corpus dosyası (varsayılan: {CORPUS_FILE})"
    )
    parser.add_argument(
        "--out", type=Path, default=OUT_DIR,
        help=f"Çıktı dizini (varsayılan: {OUT_DIR})"
    )
    parser.add_argument(
        "--device", type=int, default=None,
        help="Ses giriş aygıtı numarası (--list-devices ile listele)"
    )
    parser.add_argument(
        "--list-devices", action="store_true",
        help="Mevcut ses aygıtlarını listele ve çık"
    )
    args = parser.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        return

    if not args.corpus.exists():
        print(f"Hata: corpus dosyası bulunamadı: {args.corpus}")
        sys.exit(1)

    run(corpus_path=args.corpus, out_dir=args.out, device=args.device)


if __name__ == "__main__":
    main()
