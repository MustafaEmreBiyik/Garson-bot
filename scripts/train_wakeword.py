"""
Hey Garson — Wake Word Training Script v2
------------------------------------------
openWakeWord gerçek API kullanımı:
  - AudioFeatures.embed_clips() ile özellik çıkarımı
  - PyTorch FCN ile manuel eğitim
  - torch.onnx.export() ile ONNX export
  - Negatif örnekler: MMS-TTS (diğer ifadeler) + sentetik gürültü

Kullanım:
    source venv_wakeword/bin/activate
    python scripts/train_wakeword.py

Çıktı:
    robot_waiter_ai/models/hey_garson.onnx

Gereksinimler (venv_wakeword içinde):
    pip install -e "openWakeWord[train]"
    pip install transformers>=4.40 scipy audiomentations soundfile librosa onnxruntime-gpu
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

Süre: RTX 4050 ile ~45-60 dk (TTS üretimi ağır basan kısım)
"""

from __future__ import annotations

import os
import sys
import time
import shutil
import random
import subprocess
import numpy as np
from pathlib import Path

# ── Proje yolları ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR   = PROJECT_ROOT / "robot_waiter_ai" / "models"
OUTPUT_DIR   = PROJECT_ROOT / "scripts" / "wakeword_training_output"
POSITIVE_DIR = OUTPUT_DIR / "positive_clips"
NEGATIVE_DIR = OUTPUT_DIR / "negative_clips"

for _d in [MODELS_DIR, OUTPUT_DIR, POSITIVE_DIR, NEGATIVE_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ── Konfigürasyon ──────────────────────────────────────────────────────────────
TARGET_PHRASE = "hey garson"
MODEL_NAME    = "hey_garson"
MMS_MODEL_ID  = "facebook/mms-tts-tur"

PHRASE_VARIATIONS = [
    "hey garson",
    "heyy garson",
    "hey garsoon",
    "hay garson",
    "hey garsan",
    "hey garsın",
]

# Negatif MMS-TTS: wake word'e benzemeyen çeşitli Türkçe ifadeler
NEGATIVE_PHRASES = [
    # "hey" ile başlayan ifadeler — en kritik negatifler
    "hey dostum",
    "hey arkadaş",
    "hey nasılsın",
    "hey bekle",
    "hey dur",
    "hey seni",
    "hey orada",
    "hey bak",
    # Diğer Türkçe ifadeler
    "merhaba dünya",
    "iyi akşamlar",
    "teşekkür ederim",
    "nasılsınız bugün",
    "bir kahve lütfen",
    "hesap getirir misiniz",
    "menüyü görebilir miyim",
    "su getirir misiniz",
    "bugün hava çok güzel",
    "görüşürüz yarın",
    "tamam anlaştık",
    "biraz bekler misiniz",
    "servis ne zaman gelir",
    "tuvaleti gösterir misiniz",
    "sipariş vermek istiyorum",
]

N_POSITIVE_SAMPLES = 500    # her varyasyon için
N_NEGATIVE_MMS     = 80     # her negatif ifade için
N_NEGATIVE_NOISE   = 3000   # sentetik gürültü klip sayısı

EPOCHS        = 120
BATCH_SIZE    = 256
LEARNING_RATE = 1e-3

# openWakeWord özellik boyutları (16 kare × 96 dim = 1536)
N_FRAMES   = 16
FEAT_DIM   = 96
FLAT_DIM   = N_FRAMES * FEAT_DIM   # 1536
CLIP_SECS  = 2.0                   # özellik çıkarımı için klip uzunluğu
CLIP_SAMP  = int(CLIP_SECS * 16000)


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
    else:
        print(f"✅ GPU: {result.stdout.strip()}")

    import torch
    print(f"✅ PyTorch: {torch.__version__} | CUDA: {torch.cuda.is_available()}")
    print(f"   Python: {sys.version.split()[0]}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# B. Pozitif Örnekler (MMS-TTS, Türkçe)
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
                audio = model(**inputs).waveform.squeeze().cpu().numpy().astype(np.float32)

            audio = augment(samples=audio, sample_rate=16000)
            out_path = phrase_dir / f"{phrase.replace(' ', '_')}_{i:04d}.wav"
            scipy.io.wavfile.write(str(out_path), 16000, (audio * 32767).astype(np.int16))
            count += 1

        print(f"  ✅ {phrase!r}: {N_POSITIVE_SAMPLES} örnek")

    print(f"\nToplam pozitif örnek: {count}")
    return count


# ─────────────────────────────────────────────────────────────────────────────
# C. Negatif Örnekler (MMS-TTS diğer ifadeler + sentetik gürültü)
# ─────────────────────────────────────────────────────────────────────────────

def generate_negative_samples() -> int:
    print("=" * 60)
    print("C. Negatif Örnekler Üretiliyor")
    print("=" * 60)

    total_needed = N_NEGATIVE_MMS * len(NEGATIVE_PHRASES) + N_NEGATIVE_NOISE
    existing = list(NEGATIVE_DIR.rglob("*.wav"))
    if len(existing) >= total_needed * 0.8:
        print(f"✅ Zaten mevcut: {len(existing)} negatif örnek — atlanıyor")
        return len(existing)

    import scipy.io.wavfile

    # C.1 — MMS-TTS: wake word olmayan Türkçe ifadeler (gerçekçi yanlış tetikleme)
    speech_dir = NEGATIVE_DIR / "speech"
    speech_dir.mkdir(exist_ok=True)

    mms_existing = list(speech_dir.glob("*.wav"))
    if len(mms_existing) < N_NEGATIVE_MMS * len(NEGATIVE_PHRASES) * 0.8:
        import torch
        from transformers import VitsModel, AutoTokenizer
        from audiomentations import Compose, TimeStretch, AddGaussianNoise

        print("MMS-TTS negatif ifadeler üretiliyor...")
        tokenizer = AutoTokenizer.from_pretrained(MMS_MODEL_ID)
        model     = VitsModel.from_pretrained(MMS_MODEL_ID)
        model.eval()
        if torch.cuda.is_available():
            model = model.cuda()

        augment = Compose([
            TimeStretch(min_rate=0.8, max_rate=1.2, p=0.5),
            AddGaussianNoise(min_amplitude=0.001, max_amplitude=0.02, p=0.6),
        ])

        for phrase in NEGATIVE_PHRASES:
            for i in range(N_NEGATIVE_MMS):
                inputs = tokenizer(phrase, return_tensors="pt")
                if torch.cuda.is_available():
                    inputs = {k: v.cuda() for k, v in inputs.items()}
                with torch.no_grad():
                    audio = model(**inputs).waveform.squeeze().cpu().numpy().astype(np.float32)
                audio = augment(samples=audio, sample_rate=16000)
                tag = phrase[:10].replace(" ", "_")
                out_path = speech_dir / f"neg_{tag}_{i:03d}.wav"
                scipy.io.wavfile.write(str(out_path), 16000, (audio * 32767).astype(np.int16))

        print(f"  ✅ MMS-TTS negatif: {N_NEGATIVE_MMS * len(NEGATIVE_PHRASES)} örnek")
    else:
        print(f"  ✅ MMS-TTS negatif: zaten mevcut ({len(mms_existing)}) — atlanıyor")

    # C.2 — Sentetik gürültü (beyaz, pembe, ton, sessizlik)
    noise_dir = NEGATIVE_DIR / "noise"
    noise_dir.mkdir(exist_ok=True)

    noise_existing = list(noise_dir.glob("*.wav"))
    if len(noise_existing) < N_NEGATIVE_NOISE * 0.8:
        from scipy.signal import lfilter
        print(f"Sentetik gürültü üretiliyor ({N_NEGATIVE_NOISE} klip)...")
        rng = np.random.default_rng(42)

        # Pembe gürültü için IIR filtre katsayıları
        _pink_b = np.array([0.049922035, -0.095993537, 0.050612699, -0.004408786])
        _pink_a = np.array([1.0, -2.494956002, 2.017265875, -0.522189400])

        for i in range(N_NEGATIVE_NOISE):
            duration = rng.uniform(1.0, 2.5)
            n_samp   = int(duration * 16000)
            kind     = i % 4

            if kind == 0:   # Beyaz gürültü
                audio = rng.standard_normal(n_samp).astype(np.float32) * 0.12
            elif kind == 1: # Pembe gürültü (doğal ortam)
                white = rng.standard_normal(n_samp).astype(np.float32)
                audio = lfilter(_pink_b, _pink_a, white).astype(np.float32) * 0.35
            elif kind == 2: # Ton + gürültü (müzik/TV benzeri)
                t    = np.linspace(0, duration, n_samp, dtype=np.float32)
                freq = rng.uniform(80, 4000)
                audio = (np.sin(2 * np.pi * freq * t) * 0.06 +
                         rng.standard_normal(n_samp).astype(np.float32) * 0.02)
            else:           # Neredeyse sessizlik
                audio = rng.standard_normal(n_samp).astype(np.float32) * 0.005

            audio = np.clip(audio, -1.0, 1.0)
            scipy.io.wavfile.write(
                str(noise_dir / f"noise_{i:04d}.wav"),
                16000, (audio * 32767).astype(np.int16),
            )

        print(f"  ✅ Sentetik gürültü: {N_NEGATIVE_NOISE} örnek")
    else:
        print(f"  ✅ Sentetik gürültü: zaten mevcut ({len(noise_existing)}) — atlanıyor")

    count = len(list(NEGATIVE_DIR.rglob("*.wav")))
    print(f"\nToplam negatif örnek: {count}")
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
            try:
                info = sf.info(str(f))
                durations.append(info.frames / info.samplerate)
            except Exception:
                pass

        print(f"  {label}: {len(files):,} dosya | "
              f"ort. süre: {np.mean(durations):.2f}s | "
              f"sr: {sf.info(str(files[0])).samplerate} Hz")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# E. Özellik Çıkarımı + Model Eğitimi
# ─────────────────────────────────────────────────────────────────────────────

def _load_clips_as_array(wav_files: list, align_end: bool = False) -> np.ndarray:
    """WAV dosyalarını yükle, CLIP_SAMP uzunluğuna getir."""
    import soundfile as sf

    clips = []
    for f in wav_files:
        try:
            audio, sr = sf.read(str(f), dtype="float32")
            if audio.ndim > 1:
                audio = audio[:, 0]
            # Pad veya kes
            if len(audio) < CLIP_SAMP:
                padded = np.zeros(CLIP_SAMP, dtype=np.float32)
                if align_end:
                    # Konuşmayı pencerenin SONUNA hizala (tetikleme anını simüle et)
                    padded[-len(audio):] = audio
                else:
                    padded[:len(audio)] = audio
                clips.append(padded)
            else:
                clips.append(audio[:CLIP_SAMP])
        except Exception:
            continue
    return np.array(clips, dtype=np.float32)   # (N, CLIP_SAMP)


def _embed_to_windows(clips: np.ndarray) -> np.ndarray:
    """
    AudioFeatures.embed_clips() → (N, frames, 96)
    Son N_FRAMES kareyi al → (N, FLAT_DIM)
    """
    from openwakeword.utils import AudioFeatures

    F = AudioFeatures(inference_framework="onnx")
    # embed_clips 16-bit PCM int16 bekliyor
    clips_int16 = (clips * 32768).clip(-32768, 32767).astype(np.int16)
    features = F.embed_clips(clips_int16, batch_size=64)   # (N, frames, 96)

    windows = []
    for feat in features:           # feat: (frames, 96)
        n = len(feat)
        if n >= N_FRAMES:
            window = feat[-N_FRAMES:].flatten()
        else:
            # Yeterli kare yoksa sıfır ile pad et (başa)
            window = np.zeros(FLAT_DIM, dtype=np.float32)
            window[-(n * FEAT_DIM):] = feat.flatten()
        windows.append(window)

    return np.array(windows, dtype=np.float32)   # (N, FLAT_DIM)


def train() -> Path:
    print("=" * 60)
    print("E. Özellik Çıkarımı + Model Eğitimi")
    print("=" * 60)

    import torch
    import torch.nn as nn
    from torch.utils.data import TensorDataset, DataLoader

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Cihaz: {device}")
    if device == "cpu":
        print("⚠️  GPU yok — eğitim yavaş olacak")

    # Pozitif özellikler
    print("\nPozitif klipler yükleniyor + özellik çıkarılıyor...")
    pos_files = list(POSITIVE_DIR.rglob("*.wav"))
    random.shuffle(pos_files)
    pos_clips = _load_clips_as_array(pos_files, align_end=True)
    X_pos = _embed_to_windows(pos_clips)
    print(f"  Pozitif pencere sayısı: {len(X_pos)}")

    # Negatif özellikler
    print("Negatif klipler yükleniyor + özellik çıkarılıyor...")
    neg_files = list(NEGATIVE_DIR.rglob("*.wav"))
    random.shuffle(neg_files)
    neg_clips = _load_clips_as_array(neg_files, align_end=False)
    X_neg = _embed_to_windows(neg_clips)
    print(f"  Negatif pencere sayısı: {len(X_neg)}")

    X = np.vstack([X_pos, X_neg])
    y = np.array([1.0] * len(X_pos) + [0.0] * len(X_neg), dtype=np.float32)

    print(f"\nToplam: {len(X)} örnek ({len(X_pos)} pos, {len(X_neg)} neg)")
    print(f"Özellik boyutu: {X.shape[1]}  (N_FRAMES={N_FRAMES} × FEAT_DIM={FEAT_DIM})")

    # Karıştır + train/val böl
    idx = np.random.permutation(len(X))
    X, y = X[idx], y[idx]
    split = int(0.85 * len(X))
    X_tr, X_vl = X[:split], X[split:]
    y_tr, y_vl = y[:split], y[split:]

    X_t = torch.tensor(X_tr).to(device)
    y_t = torch.tensor(y_tr).unsqueeze(1).to(device)
    X_v = torch.tensor(X_vl).to(device)
    y_v = torch.tensor(y_vl).unsqueeze(1).to(device)

    loader = DataLoader(
        TensorDataset(X_t, y_t), batch_size=BATCH_SIZE, shuffle=True
    )

    # FCN modeli
    class WakeWordFCN(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(FLAT_DIM, 128),
                nn.LayerNorm(128),
                nn.ReLU(),
                nn.Linear(128, 32),
                nn.LayerNorm(32),
                nn.ReLU(),
                nn.Linear(32, 1),
                nn.Sigmoid(),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # openWakeWord (1, n_frames, 96) rank-3 gönderir → düzleştir
            if x.dim() == 3:
                x = x.reshape(x.shape[0], -1)
            return self.net(x)

    model = WakeWordFCN().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    criterion = nn.BCELoss()

    best_val = float("inf")
    best_state = None
    t_start = time.time()

    print(f"\nEğitim: {EPOCHS} epoch, batch={BATCH_SIZE}, lr={LEARNING_RATE}")
    print("-" * 60)

    for epoch in range(EPOCHS):
        model.train()
        tr_loss = 0.0
        for xb, yb in loader:
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
            tr_loss += loss.item()

        if (epoch + 1) % 10 == 0:
            model.eval()
            with torch.no_grad():
                vl_loss = criterion(model(X_v), y_v).item()
                preds   = (model(X_v) > 0.5).float()
                acc     = (preds == y_v).float().mean().item()

            if vl_loss < best_val:
                best_val   = vl_loss
                best_state = {k: v.clone() for k, v in model.state_dict().items()}

            elapsed = (time.time() - t_start) / 60
            print(
                f"  Epoch {epoch+1:3d}/{EPOCHS} | "
                f"tr_loss={tr_loss/len(loader):.4f} | "
                f"vl_loss={vl_loss:.4f} | "
                f"vl_acc={acc:.3f} | "
                f"{elapsed:.1f}dk"
            )

    if best_state:
        model.load_state_dict(best_state)
    print(f"\n✅ Eğitim tamamlandı: {(time.time()-t_start)/60:.1f} dk")

    # ONNX export — input: (batch, N_FRAMES, FEAT_DIM) rank-3
    # openWakeWord get_features() her zaman (1, n_frames, 96) gönderir
    onnx_path   = OUTPUT_DIR / "hey_garson_raw.onnx"
    dummy_input = torch.zeros(1, N_FRAMES, FEAT_DIM)

    torch.onnx.export(
        model.cpu(),
        dummy_input,
        str(onnx_path),
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={
            "input":  {0: "batch_size"},
            "output": {0: "batch_size"},
        },
        opset_version=12,
    )
    print(f"✅ ONNX kaydedildi: {onnx_path}")
    return onnx_path


# ─────────────────────────────────────────────────────────────────────────────
# F. Doğrulama + Kopyalama
# ─────────────────────────────────────────────────────────────────────────────

def validate_and_export(onnx_src: Path) -> Path:
    print("=" * 60)
    print("F. Doğrulama ve Export")
    print("=" * 60)

    import onnxruntime as ort

    sess       = ort.InferenceSession(str(onnx_src))
    in_name    = sess.get_inputs()[0].name
    in_shape   = sess.get_inputs()[0].shape
    dummy      = np.zeros((1, N_FRAMES, FEAT_DIM), dtype=np.float32)
    out        = sess.run(None, {in_name: dummy})
    print(f"✅ ONNX runtime testi geçti | giriş shape: {in_shape} | çıktı: {out[0].shape}")

    dest    = MODELS_DIR / "hey_garson.onnx"
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
    import onnxruntime as ort
    from openwakeword.utils import AudioFeatures

    sess    = ort.InferenceSession(str(model_path))
    in_name = sess.get_inputs()[0].name
    feat_ex = AudioFeatures(inference_framework="onnx")

    pos_files = list(POSITIVE_DIR.rglob("*.wav"))[:50]
    neg_files = list(NEGATIVE_DIR.rglob("*.wav"))[:50]

    def score_files(files: list, label: str) -> float:
        scores = []
        clips = _load_clips_as_array(files, align_end=(label.startswith("Pozitif")))
        clips_int16 = (clips * 32768).clip(-32768, 32767).astype(np.int16)
        features = feat_ex.embed_clips(clips_int16, batch_size=64)  # (N, frames, 96)
        for feat in features:
            n = len(feat)
            if n >= N_FRAMES:
                window = feat[-N_FRAMES:].flatten()
            else:
                window = np.zeros(FLAT_DIM, dtype=np.float32)
                window[-(n * FEAT_DIM):] = feat.flatten()
            x = window.reshape(1, N_FRAMES, FEAT_DIM)
            score = float(sess.run(None, {in_name: x})[0][0, 0])
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
        print("   Öneri: EPOCHS=150, N_POSITIVE_SAMPLES=800 ayarla, tekrar çalıştır")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🎙️  Hey Garson — Wake Word Training v2\n")

    check_environment()
    generate_positive_samples()
    generate_negative_samples()
    verify_data()
    onnx_src   = train()
    model_path = validate_and_export(onnx_src)
    smoke_test(model_path)

    print("\n" + "=" * 60)
    print("✅ Tamamlandı!")
    print(f"   Model: {model_path}")
    print("   Sonraki adım: python -m robot_waiter_ai.speech.mic")
    print("=" * 60)
