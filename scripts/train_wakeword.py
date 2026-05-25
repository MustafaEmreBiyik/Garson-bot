"""
Hey Garson — Wake Word Training Script
--------------------------------------
openWakeWord + Meta MMS-TTS (Türkçe, offline) ile hey_garson.onnx üretir.

Kullanım:
    python scripts/train_wakeword.py

Çıktı:
    robot_waiter_ai/models/hey_garson.onnx

Gereksinimler (venv_wakeword içinde):
    pip install -e "openWakeWord[train]"
    pip install transformers>=4.40 scipy audiomentations soundfile librosa

Süre: RTX 4050 ile ~30-45 dk
"""

from __future__ import annotations

import os
import sys
import time
import json
import shutil
import random
import subprocess
import numpy as np
from pathlib import Path

# ── Proje kökü (bu script scripts/ altında, proje kökü bir üst) ──────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR   = PROJECT_ROOT / "robot_waiter_ai" / "models"
OUTPUT_DIR   = PROJECT_ROOT / "scripts" / "wakeword_training_output"
POSITIVE_DIR = OUTPUT_DIR / "positive_clips"
NEGATIVE_DIR = OUTPUT_DIR / "negative_clips"

MODELS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
POSITIVE_DIR.mkdir(parents=True, exist_ok=True)
NEGATIVE_DIR.mkdir(parents=True, exist_ok=True)

# ── Konfigürasyon ─────────────────────────────────────────────────────────────
TARGET_PHRASE = "hey garson"
MODEL_NAME    = "hey_garson"

PHRASE_VARIATIONS = [
    "hey garson",
    "heyy garson",
    "hey garsoon",
    "hay garson",
    "hey garsan",
    "hey garsın",
]

MMS_MODEL_ID        = "facebook/mms-tts-tur"
N_POSITIVE_SAMPLES  = 500   # her varyasyon için
N_NEGATIVE_SAMPLES  = 5000
EPOCHS              = 100
BATCH_SIZE          = 32
LEARNING_RATE       = 1e-3


# ─────────────────────────────────────────────────────────────────────────────
# A. Ortam Kontrolü
# ─────────────────────────────────────────────────────────────────────────────

def check_environment() -> None:
    print("=" * 60)
    print("A. Ortam Kontrolü")
    print("=" * 60)

    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("⚠️  GPU bulunamadı — eğitim CPU'da çalışacak (çok yavaş!)")
        print("   CUDA driver kurulu mu? `nvidia-smi` çalışıyor mu?")
    else:
        print(f"✅ GPU: {result.stdout.strip()}")

    import torch
    print(f"✅ PyTorch: {torch.__version__} | CUDA: {torch.cuda.is_available()}")
    print(f"   Python: {sys.version.split()[0]}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# B. Pozitif Örnekler Üret (MMS-TTS)
# ─────────────────────────────────────────────────────────────────────────────

def generate_positive_samples() -> int:
    print("=" * 60)
    print("B. Pozitif Örnekler Üretiliyor (MMS-TTS)")
    print("=" * 60)

    existing = list(POSITIVE_DIR.rglob("*.wav"))
    if len(existing) >= N_POSITIVE_SAMPLES * len(PHRASE_VARIATIONS) * 0.8:
        print(f"✅ Zaten mevcut: {len(existing)} pozitif örnek — atlanıyor")
        return len(existing)

    import torch
    import scipy.io.wavfile
    from transformers import VitsModel, AutoTokenizer
    from audiomentations import Compose, TimeStretch, PitchShift, AddGaussianNoise

    print(f"MMS-TTS yükleniyor: {MMS_MODEL_ID}  (~200 MB, ilk seferinde indirilir)")
    tokenizer = AutoTokenizer.from_pretrained(MMS_MODEL_ID)
    model     = VitsModel.from_pretrained(MMS_MODEL_ID)
    model.eval()

    if torch.cuda.is_available():
        model = model.cuda()

    augment = Compose([
        TimeStretch(min_rate=0.85, max_rate=1.15, p=0.7),
        PitchShift(min_semitones=-2, max_semitones=2, p=0.6),
        AddGaussianNoise(min_amplitude=0.001, max_amplitude=0.015, p=0.5),
    ])

    count = 0
    for phrase in PHRASE_VARIATIONS:
        phrase_dir = POSITIVE_DIR / phrase.replace(" ", "_")
        phrase_dir.mkdir(exist_ok=True)

        for i in range(N_POSITIVE_SAMPLES):
            inputs = tokenizer(phrase, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}

            with torch.no_grad():
                output = model(**inputs).waveform

            audio = output.squeeze().cpu().numpy().astype(np.float32)

            # Augmentasyon uygula
            augmented = augment(samples=audio, sample_rate=16000)

            out_path = phrase_dir / f"{phrase.replace(' ', '_')}_{i:04d}.wav"
            scipy.io.wavfile.write(
                str(out_path),
                rate=16000,
                data=(augmented * 32767).astype(np.int16),
            )
            count += 1

        print(f"  ✅ {phrase!r}: {N_POSITIVE_SAMPLES} örnek")

    print(f"\nToplam pozitif örnek: {count}")
    return count


# ─────────────────────────────────────────────────────────────────────────────
# C. Negatif Örnekler İndir
# ─────────────────────────────────────────────────────────────────────────────

def download_negative_samples() -> int:
    print("=" * 60)
    print("C. Negatif Örnekler İndiriliyor")
    print("=" * 60)

    existing = list(NEGATIVE_DIR.rglob("*.wav"))
    if len(existing) >= N_NEGATIVE_SAMPLES * 0.8:
        print(f"✅ Zaten mevcut: {len(existing)} negatif örnek — atlanıyor")
        return len(existing)

    from openwakeword.data import download_background_noise

    print("MUSAN + FMA arka plan gürültüsü indiriliyor (~5-10 dk)…")
    download_background_noise(
        output_dir=str(NEGATIVE_DIR),
        n_samples=N_NEGATIVE_SAMPLES,
    )

    count = len(list(NEGATIVE_DIR.rglob("*.wav")))
    print(f"✅ Toplam negatif örnek: {count}")
    return count


# ─────────────────────────────────────────────────────────────────────────────
# D. Veri Doğrulama
# ─────────────────────────────────────────────────────────────────────────────

def verify_data() -> None:
    print("=" * 60)
    print("D. Veri Seti Doğrulanıyor")
    print("=" * 60)

    import soundfile as sf

    for label, directory in [("Pozitif", POSITIVE_DIR), ("Negatif", NEGATIVE_DIR)]:
        files = list(directory.rglob("*.wav"))
        if not files:
            raise RuntimeError(f"{label} örnekler bulunamadı: {directory}")

        durations = []
        for f in files[:200]:
            info = sf.info(str(f))
            durations.append(info.frames / info.samplerate)

        print(f"  {label}: {len(files):,} dosya | "
              f"ort. süre: {np.mean(durations):.2f}s | "
              f"sr: {sf.info(str(files[0])).samplerate} Hz")

    print()


# ─────────────────────────────────────────────────────────────────────────────
# E. Model Eğitimi
# ─────────────────────────────────────────────────────────────────────────────

def train() -> Path:
    print("=" * 60)
    print("E. Model Eğitimi")
    print("=" * 60)

    import torch
    from openwakeword.train import train_model

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Cihaz: {device}")
    if device == "cpu":
        print("⚠️  GPU yok — eğitim ~2-3 saat sürebilir")

    pos_count = len(list(POSITIVE_DIR.rglob("*.wav")))
    neg_count = len(list(NEGATIVE_DIR.rglob("*.wav")))
    print(f"Pozitif: {pos_count:,}  |  Negatif: {neg_count:,}")
    print(f"Epoch: {EPOCHS}  |  Batch: {BATCH_SIZE}  |  LR: {LEARNING_RATE}")
    print("-" * 60)

    t_start = time.time()

    train_model(
        model_name=MODEL_NAME,
        positive_dir=str(POSITIVE_DIR),
        negative_dir=str(NEGATIVE_DIR),
        output_dir=str(OUTPUT_DIR),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        target_phrase=TARGET_PHRASE,
    )

    elapsed = time.time() - t_start
    print(f"\n✅ Eğitim tamamlandı: {elapsed/60:.1f} dk")

    onnx_files = list(OUTPUT_DIR.rglob("*.onnx"))
    if not onnx_files:
        raise FileNotFoundError(f"ONNX çıktısı bulunamadı: {OUTPUT_DIR}")

    return onnx_files[0]


# ─────────────────────────────────────────────────────────────────────────────
# F. Doğrulama + Modeli Kopyala
# ─────────────────────────────────────────────────────────────────────────────

def validate_and_export(onnx_src: Path) -> Path:
    print("=" * 60)
    print("F. Doğrulama ve Export")
    print("=" * 60)

    import onnxruntime as ort

    sess = ort.InferenceSession(str(onnx_src))
    dummy = np.zeros((1, 16000), dtype=np.float32)
    input_name = sess.get_inputs()[0].name
    out = sess.run(None, {input_name: dummy})
    print(f"✅ ONNX runtime testi geçti | çıktı shape: {out[0].shape}")

    dest = MODELS_DIR / "hey_garson.onnx"
    shutil.copy2(onnx_src, dest)
    size_kb = dest.stat().st_size / 1024
    print(f"✅ Model kopyalandı: {dest}")
    print(f"   Boyut: {size_kb:.1f} KB")
    return dest


# ─────────────────────────────────────────────────────────────────────────────
# G. Smoke Test
# ─────────────────────────────────────────────────────────────────────────────

def smoke_test(model_path: Path) -> None:
    print("=" * 60)
    print("G. Smoke Test")
    print("=" * 60)

    import soundfile as sf
    from openwakeword.model import Model

    oww = Model(wakeword_models=[str(model_path)], inference_framework="onnx")
    model_key = list(oww.models.keys())[0]

    pos_files = list(POSITIVE_DIR.rglob("*.wav"))[:50]
    neg_files = list(NEGATIVE_DIR.rglob("*.wav"))[:50]

    def score_files(files: list, label: str) -> float:
        scores = []
        for f in files:
            audio, sr = sf.read(str(f), dtype="float32")
            chunk = (audio * 32768).astype(np.int16)
            oww.predict(chunk)
            score = oww.prediction_buffer[model_key][-1]
            scores.append(score)
        mean = float(np.mean(scores))
        print(f"  {label}: ort. skor = {mean:.3f}  (n={len(files)})")
        return mean

    pos_score = score_files(pos_files, "Pozitif (hey garson)")
    neg_score = score_files(neg_files, "Negatif (arka plan)  ")

    if pos_score > 0.5 and neg_score < 0.3:
        print("\n✅ Smoke test geçti — model kullanıma hazır")
    else:
        print("\n⚠️  Smoke test zayıf — daha fazla epoch veya veri gerekebilir")
        print(f"   Pozitif skor > 0.5 bekleniyor, alınan: {pos_score:.3f}")
        print(f"   Negatif skor < 0.3 bekleniyor, alınan: {neg_score:.3f}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🎙️  Hey Garson — Wake Word Training\n")

    check_environment()
    generate_positive_samples()
    download_negative_samples()
    verify_data()
    onnx_src  = train()
    model_path = validate_and_export(onnx_src)
    smoke_test(model_path)

    print("\n" + "=" * 60)
    print("✅ Tamamlandı!")
    print(f"   Model: {model_path}")
    print("   Sonraki adım: python -m robot_waiter_ai.speech.mic")
    print("=" * 60)
