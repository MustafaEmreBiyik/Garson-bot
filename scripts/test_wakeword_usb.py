"""
USB mikrofon ile "hey garson" wake word testi.

Kullanım:
    source venv_wakeword/bin/activate
    python scripts/test_wakeword_usb.py

Çıkmak için Ctrl+C.
"""

import sys
import signal
import numpy as np
import sounddevice as sd
import onnxruntime as ort
from collections import deque
from pathlib import Path

from openwakeword.utils import AudioFeatures

# ── Sabitler ──────────────────────────────────────────────────────────────────
PROJECT_ROOT  = Path(__file__).resolve().parent.parent
MODEL_PATH    = PROJECT_ROOT / "robot_waiter_ai" / "models" / "hey_garson.onnx"

SAMPLE_RATE    = 16000
CHUNK_MS       = 80
CHUNK_SAMPLES  = int(CHUNK_MS * SAMPLE_RATE / 1000)   # 1280 sample
# embed_clips en az 76 mel frame (~0.96s) istiyor → 2s buffer kullan
AUDIO_BUF_SEC  = 2
AUDIO_BUF_SAMP = SAMPLE_RATE * AUDIO_BUF_SEC          # 32000 sample
N_FRAMES       = 16
FEAT_DIM       = 96
FLAT_DIM       = N_FRAMES * FEAT_DIM                   # 1536
THRESHOLD      = 0.5

# ── Model yükleme ─────────────────────────────────────────────────────────────
print(f"Model yükleniyor: {MODEL_PATH}")
sess    = ort.InferenceSession(str(MODEL_PATH))
in_name = sess.get_inputs()[0].name
feat_ex = AudioFeatures(inference_framework="onnx")

# Ham ses ring buffer (2 saniyelik)
audio_buffer: deque = deque(maxlen=AUDIO_BUF_SAMP)
# Başta sıfırlarla doldur
audio_buffer.extend(np.zeros(AUDIO_BUF_SAMP, dtype=np.int16))

cooldown_chunks = 0   # algılama sonrası bekleme sayacı

print(f"\nDinleniyor... 'hey garson' deyin. (Çıkmak için Ctrl+C)\n")
print(f"{'─'*50}")


def process_chunk(indata: np.ndarray, frames: int, time_info, status) -> None:
    """Her 80ms chunk için çağrılır."""
    global cooldown_chunks
    if status:
        return

    # Yeni sesi buffer'a ekle
    new_samples = indata[:, 0].astype(np.int16)
    audio_buffer.extend(new_samples)

    if cooldown_chunks > 0:
        cooldown_chunks -= 1
        return

    # 2 saniyelik tamponu (1, 32000) olarak al
    clip = np.array(audio_buffer, dtype=np.int16).reshape(1, -1)

    # Mel-spec + embedding → (1, n_mel_frames, 96)
    features = feat_ex.embed_clips(clip, batch_size=1)
    if features is None or len(features[0]) < N_FRAMES:
        return

    # Son N_FRAMES embedding frame'ini al → (1, 1536)
    window = features[0][-N_FRAMES:].flatten().reshape(1, FLAT_DIM).astype(np.float32)
    score  = float(sess.run(None, {in_name: window})[0][0, 0])

    if score > 0.3:
        bar = "█" * int(score * 20)
        print(f"  Skor: {score:.3f}  {bar}    ", end="\r")

    if score >= THRESHOLD:
        print(f"\n✅ HEY GARSON ALGILANDI! (skor: {score:.3f})\n{'─'*50}")
        cooldown_chunks = 25   # ~2 saniye bekleme (25 × 80ms)


def main() -> None:
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        device="default",
        blocksize=CHUNK_SAMPLES,
        callback=process_chunk,
    ):
        while True:
            sd.sleep(100)


if __name__ == "__main__":
    main()
