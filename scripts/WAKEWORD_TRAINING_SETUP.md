# Hey Garson — Wake Word Training Setup

## Görev
`robot_waiter_ai/models/hey_garson.onnx` dosyasını üretmek için yerel Ubuntu ortamında
openWakeWord eğitim pipeline'ını kurup çalıştır.

Tüm komutlar Ubuntu terminalinde, proje kökünde (`~/Garson-bot` veya neredeyse) çalıştırılacak.

---

## Ön Koşul Kontrolü

```bash
nvidia-smi                  # GPU görünüyor mu?
python3 --version           # 3.10+ olmalı
git --version
```

---

## Adım 1 — Sanal Ortam

```bash
python3 -m venv venv_wakeword
source venv_wakeword/bin/activate
```

---

## Adım 2 — openWakeWord Reposunu Klonla

```bash
git clone --depth 1 https://github.com/dscripka/openWakeWord.git
pip install -e "openWakeWord[train]"
```

---

## Adım 3 — Bağımlılıkları Kur

CUDA versiyonunu kontrol et:

```bash
nvidia-smi | grep "CUDA Version"
```

Çıkan versiyona göre doğru komutu seç:

```bash
# CUDA 12.1 için:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# CUDA 11.8 için:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

Sonra:

```bash
pip install transformers>=4.40 scipy audiomentations soundfile librosa onnxruntime-gpu
```

---

## Adım 4 — Eğitimi Çalıştır

```bash
python scripts/train_wakeword.py
```

Script şunları otomatik yapar:
- GPU kontrolü
- Meta MMS-TTS ile Türkçe "hey garson" ses örnekleri üretir (3000 pozitif)
- MUSAN + FMA'dan arka plan gürültüsü indirir (5000 negatif)
- openWakeWord modelini eğitir (~30–45 dk, RTX 4050)
- `robot_waiter_ai/models/hey_garson.onnx` dosyasını üretir
- Smoke test çalıştırır

---

## Adım 5 — Sonucu Doğrula

```bash
ls -lh robot_waiter_ai/models/hey_garson.onnx
# Beklenen: ~200–500 KB
```

---

## Adım 6 — Ana Ortamda Smoke Test

```bash
deactivate
source .venv/bin/activate
python -m robot_waiter_ai.speech.mic
```

---

## Hata Durumları

| Hata | Çözüm |
|---|---|
| `nvidia-smi: command not found` | CUDA driver kurulu değil — `sudo apt install nvidia-driver-535` |
| `No module named openwakeword.train` | `pip install -e "openWakeWord[train]"` tekrar çalıştır |
| `CUDA out of memory` | `scripts/train_wakeword.py` içinde `BATCH_SIZE = 16` yap |
| `download_background_noise` takılı kalır | İnternet bağlantısını kontrol et, VPN varsa kapat |
| Smoke test skoru düşük (pozitif < 0.5) | `EPOCHS = 150` ve `N_POSITIVE_SAMPLES = 800` yap, tekrar çalıştır |

---

## Çıktı Dosyaları

| Yol | Açıklama |
|---|---|
| `robot_waiter_ai/models/hey_garson.onnx` | **Kullanılacak model** |
| `scripts/wakeword_training_output/` | Ara çıktılar (silinebilir) |
| `openWakeWord/` | Klonlanan repo (silinebilir) |
