# Garson-bot — Proje Durumu ve Hedeflenen Hal
**Son güncelleme:** 31 Mayıs 2026 | **Sürüm:** 4.0

Yeni bir sohbet başladığında bu dosyayı okuyarak projeyi baştan anlat.
Kod tabanını tekrar incelemene gerek yok — her şey burada.

---

## Proje Nedir?

Bir restoran için fiziksel servis robotuna (W-BOT) entegre edilecek Türkçe sesli yapay zeka asistanı.
Müşterilerle doğal konuşma, sipariş alma ve menü bilgisi sunma hedeflenmektedir.

**Hedef donanım:** Jetson Orin NX 16GB + USB mikrofon + USB hoparlör (3.5mm AUX bağlantılı)
**Ortam:** Gürültülü restoran — müzik, kalabalık, birden fazla konuşmacı.

---

## Güncel Çalışma Ortamları

| Ortam | İşlemci | LLM Backend | Durum |
|-------|---------|-------------|-------|
| Ubuntu PC (geliştirme) | RTX 4050 | qwen3_backend.py (transformers, 4-bit NF4) | ✅ Çalışıyor |
| Jetson Orin NX 16GB | Orin GPU (SM87) | llama_cpp_backend.py (GGUF, llama-cpp-python) | ⚠️ Ses sorunu var |

---

## Klasör Yapısı (Aktif Dosyalar)

```
Garson-bot/
├── scripts/
│   ├── demo_usb.py               ✅ Ana demo — wake word → STT → LLM → Piper TTS
│   ├── compare_models.py         ✅ Model karşılaştırma scripti (4B vs 1.7B)
│   ├── train_wakeword.py         ✅ openWakeWord eğitim (MMS-TTS + gürültü)
│   └── test_wakeword_usb.py      ✅ USB mikrofon ile gerçek zamanlı wake word testi
└── robot_waiter_ai/
    ├── inference/
    │   ├── qwen3_backend.py      ✅ PC için — Qwen3-4B transformers 4-bit NF4
    │   └── llama_cpp_backend.py  ✅ Jetson için — Qwen3-4B GGUF Q4_K_M + CUDA
    ├── speech/
    │   ├── stt.py                ✅ faster-whisper STT wrapper (model: small)
    │   ├── tts.py                ✅ edge-tts + PiperTTS (Piper birincil, edge-tts fallback)
    │   └── mic.py                ✅ ReSpeaker Mic Array wrapper
    └── data/
        ├── menu.yaml             ✅ Menü tanımları (name, category, price, description)
        └── restaurant_info.yaml
    models/
        ├── hey_garson.onnx       ✅ Wake word modeli (openWakeWord, 789 KB)
        └── tr_TR-fahrettin-medium.onnx  ✅ Piper TTS Türkçe sesi
```

---

## Aktif Pipeline (demo_usb.py)

```
"hey garson" denir
    │  openWakeWord (hey_garson.onnx, threshold=0.7)
    │  USB mikrofon auto-detect (_find_input_device → "USB PnP" → device=0)
    ▼
6 sn kayıt (sd.rec, device=USB mic)
    ▼
faster-whisper small (CUDA, float16)
    │  initial_prompt ile menü kelimeleri Whisper'a hint
    ▼
LLM — otomatik seçim:
    │  llama_cpp_backend.py varsa → Qwen3-4B Q4_K_M GGUF (Jetson)
    │  yoksa → qwen3_backend.py → Qwen3-4B transformers (PC)
    ▼
Piper TTS → WAV → aplay subprocess (ALSA_OUTPUT_DEVICE ile)
    ▼
Tekrar "hey garson" bekle
```

---

## LLM Model Bilgileri

### Jetson — llama_cpp_backend.py
| Parametre | Değer |
|-----------|-------|
| Model | Qwen3-4B-Q4_K_M.gguf |
| Konum | /home/emk/llama.cpp/Qwen3-4B-Q4_K_M.gguf |
| Backend | llama-cpp-python 0.3.23 (CUDA SM87) |
| GPU offload | 37/37 katman (tam GPU) |
| VRAM | ~2.37 GB / 15.6 GB |
| Hız | ~12-15 tok/s |
| Thinking | Kapalı — _format_prompt() `<think>\n\n</think>` prefix ekler |
| n_ctx | 2048 |

### PC — qwen3_backend.py
| Parametre | Değer |
|-----------|-------|
| Model | Qwen/Qwen3-4B (HuggingFace) |
| Quantization | BitsAndBytesConfig 4-bit NF4 |
| Thinking | enable_thinking=False (apply_chat_template) |
| Max new tokens | 150, repetition_penalty=1.1 |

### Qwen3-1.7B Testi (31 Mayıs 2026 — REDDEDİLDİ)
- Hız: 23.4 tok/s (1.9x daha hızlı)
- Kalite: Yetersiz — pizza sorusunu anlayamadı, sipariş yerine soru sordu, "güle güle"ye yanlış yanıt
- Karar: 4B kalıcı olarak seçildi

---

## STT Bilgileri

| Parametre | Değer |
|-----------|-------|
| Motor | faster-whisper |
| Model | **small** (medium → small değiştirildi, 31 Mayıs 2026) |
| Device | CUDA, float16 |
| Latency | ~0.5-1 sn (small, GPU) |
| initial_prompt | Türkçe restoran + menü kelimeleri |

---

## TTS Bilgileri

| Motor | Durum |
|-------|-------|
| Piper (tr_TR-fahrettin-medium) | ✅ Birincil, offline |
| edge-tts | Fallback (internet gerekli) |

Piper benchmark (Jetson, CPU): 494-779ms
Playback: `aplay` subprocess (ALSA_OUTPUT_DEVICE ile yapılandırılabilir)

---

## Jetson Deployment Durumu

### Kurulu Bileşenler ✅
- JetPack R36.5.0, CUDA 12.6, Python 3.10
- faster-whisper, sounddevice, portaudio
- onnxruntime (GPU uyarısıyla çalışıyor)
- Piper TTS (piper_linux_aarch64, /home/emk/Desktop/Garson-bot/Garson-bot/piper/)
- llama-cpp-python 0.3.23 (CUDA SM87 ile derlendi)
- Qwen3-4B-Q4_K_M.gguf (/home/emk/llama.cpp/)
- Qwen3-1.7B-Q8_0.gguf (/home/emk/llama.cpp/ — test edildi, kullanılmıyor)
- Proje: /home/emk/Desktop/Garson-bot/Garson-bot/ (iç içe dizin)

### Ses Donanımı Durumu ⚠️
| Cihaz | Durum | Açıklama |
|-------|-------|----------|
| USB Mikrofon (USB PnP Sound Device) | ✅ card 0, device 0 | Auto-detect çalışıyor |
| USB Hoparlör | ❌ Playback yok | USB sadece güç, ses için 3.5mm gerekiyor |
| Jetson APE (card 2) | ❌ Analog codec yok | Dijital DSP, doğrudan 3.5mm çıkış yok |
| HDMI (card 1) | ❌ Monitörde hoparlör yok | |

**Çözüm:** USB ses adaptörü (USB → 3.5mm) gerekiyor — ~100 TL

### Performans Ölçümleri
| Ölçüm | Sonuç |
|-------|-------|
| llama-bench pp512 | 492 tok/s |
| llama-bench tg128 | 14.97 tok/s |
| Python API (llama-cpp-python) | 12.54 tok/s |
| Toplam yanıt süresi (tahmini, ses olmadan) | ~4-5 sn |

---

## Wake Word Modeli

| Parametre | Değer |
|-----------|-------|
| Dosya | robot_waiter_ai/models/hey_garson.onnx |
| Motor | openWakeWord (FCN head, 789 KB) |
| Threshold | 0.7 (0.5 çok hassastı) |
| Chunk | 1280 sample (80ms @ 16kHz) |
| Eğitim | 3000 pozitif (MMS-TTS), 4840 negatif |
| Smoke test | pozitif=0.999, negatif=0.001 ✅ |
| ⚠️ Uyarı | Sentetik sesle eğitildi — gerçek gürültülü ortamda test edilmedi |

---

## demo_usb.py Yapılandırma Sabitleri

```python
WHISPER_MODEL      = "small"           # medium → small (31 Mayıs 2026)
SAMPLE_RATE        = 16_000
RECORD_SECONDS     = 6
WAKEWORD_THRESHOLD = 0.7
ALSA_OUTPUT_DEVICE = None              # None=sistem default, "plughw:2,0"=Jetson APE
```

---

## Eksik / Yapılacaklar (Öncelik Sırasıyla)

| # | Görev | Öncelik | Durum |
|---|-------|---------|-------|
| 1 | Ses çıkışı — USB ses adaptörü temin et | 🔴 Kritik | Bloke: donanım yok |
| 2 | Tam demo testi Jetson'da (STT→LLM→TTS) | 🔴 Kritik | Ses sorununa bağlı |
| 3 | Wake word gerçek ortam testi | 🟠 Yüksek | Ses sorununa bağlı |
| 4 | Sistem prompt ince ayar (4B hataları) | 🟠 Yüksek | Sipariş anında yanlış toplam söylüyor |
| 5 | Whisper small kalite doğrulaması | 🟠 Yüksek | Ses olunca yapılacak |
| 6 | systemd servis (otomatik başlatma) | 🟢 Düşük | Stabil olduktan sonra |

---

## Başarı Kriterleri

```
Müşteri: "Mercimek çorbası istiyorum."
Robot:   "Elbette, mercimek çorbası 85 TL eklendi. Başka bir şey alır mısınız?"  ✅

Müşteri: "Pizza var mı?"
Robot:   "Bu konuda bilgim yok, personelimize sorabilirsiniz."                   ✅

Müşteri: "Güle güle."
Robot:   "Güle güle, tekrar bekleriz!"                                            ✅

Müşteri: "Hesabı alabilir miyim?"
Robot:   "Toplam 325 TL."  (toplam doğru, önceden söylememiş)                   ✅

Yanıt süresi: < 5 sn (hedef < 4 sn)                                             ⚠️ ~4.5 sn tahmini
```

---

## Geliştirme Kuralları

1. **Async-first** — tüm I/O `asyncio.to_thread` ile
2. **aplay ile ses çal** — sounddevice playback değil (USB cihaz çakışmasını önler)
3. **USB mikrofon auto-detect** — `_find_input_device()` ile, hardcoded index değil
4. **LLM backend otomatik seçim** — llama_cpp_backend önce, qwen3_backend fallback
5. **Thinking modu kapalı** — Qwen3 `<think>` bloklarını hem strip et hem baştan engelle
6. **ALSA_OUTPUT_DEVICE** — Jetson'da ses cihazı değişirse bu sabiti güncelle
7. **UTF-8 zorunlu** — tüm dosya okuma/yazma `encoding='utf-8'`
