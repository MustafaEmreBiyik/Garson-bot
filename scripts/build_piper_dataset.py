#!/usr/bin/env python3
"""
Piper eğitimi için LJSpeech formatında dataset hazırlar.

Kaynak : <recordings>/corpus_XXXX.wav
Çıktı  : <out>/wavs/  +  <out>/metadata.csv

LJSpeech format: file_id|text|normalized_text  (header yok, pipe ayraç)

Kullanım:
    python scripts/build_piper_dataset.py                         # v1 (varsayılan)
    python scripts/build_piper_dataset.py --corpus scripts/tts_corpus_v2.txt \
        --recordings data/recordings_v2 --out data/piper_dataset_v2
"""

import argparse
import shutil
from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent


def load_corpus(path: Path) -> dict[int, str]:
    """0-tabanlı indeks → cümle eşlemesi döner."""
    sentences: dict[int, str] = {}
    idx = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            sentences[idx] = line
            idx += 1
    return sentences


def main():
    parser = argparse.ArgumentParser(description="Piper LJSpeech dataset üretici")
    parser.add_argument("--corpus", type=Path, default=SCRIPT_DIR / "tts_corpus.txt",
                        help="Kaynak corpus dosyası")
    parser.add_argument("--recordings", type=Path, default=PROJECT_ROOT / "data" / "recordings",
                        help="Kayıt WAV'larının bulunduğu dizin")
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "data" / "piper_dataset",
                        help="Çıktı dizini")
    parser.add_argument("--prefix", type=str, default="",
                        help="file_id/WAV adına eklenecek önek (birden fazla kayıt "
                             "setini aynı dizinde birleştirirken corpus_0001.wav "
                             "çakışmasını önlemek için, örn. 'ek_')")
    parser.add_argument("--append", action="store_true",
                        help="metadata.csv'yi üzerine yazmak yerine sonuna ekle "
                             "(--out zaten dolu bir dataset dizini gösteriyorsa)")
    args = parser.parse_args()

    recordings = args.recordings
    out_dir    = args.out
    wavs_dir   = out_dir / "wavs"
    metadata   = out_dir / "metadata.csv"

    if not recordings.exists():
        print(f"Hata: {recordings} bulunamadı.")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    wavs_dir.mkdir(parents=True, exist_ok=True)

    sentences = load_corpus(args.corpus)
    print(f"Corpus: {len(sentences)} cümle")

    wav_files = sorted(recordings.glob("corpus_*.wav"))
    if not wav_files:
        print(f"Hata: {recordings} içinde WAV dosyası bulunamadı.")
        return

    entries   = []
    skipped   = []

    for wav in wav_files:
        try:
            num = int(wav.stem.replace("corpus_", "")) - 1  # 1-tabanlı → 0-tabanlı
        except ValueError:
            continue

        if num not in sentences:
            skipped.append(wav.name)
            continue

        text     = sentences[num]
        file_id  = f"{args.prefix}{wav.stem}"     # örn. ek_corpus_0001
        dst_name = f"{args.prefix}{wav.name}"
        dst      = wavs_dir / dst_name

        shutil.copy2(wav, dst)
        entries.append((file_id, text, text))

    # metadata.csv yaz (--append: sonuna ekle, yoksa üzerine yaz)
    mode = "a" if args.append else "w"
    with open(metadata, mode, encoding="utf-8") as f:
        for file_id, text, norm_text in entries:
            f.write(f"{file_id}|{text}|{norm_text}\n")

    print(f"\nDataset hazır  : {out_dir}")
    print(f"Kayıt sayısı   : {len(entries)}")
    print(f"metadata.csv   : {metadata}")
    if skipped:
        print(f"Atlanacak WAV  : {skipped}")

    print("\nİlk 5 satır (metadata.csv):")
    for fid, txt, _ in entries[:5]:
        print(f"  {fid} | {txt}")


if __name__ == "__main__":
    main()
