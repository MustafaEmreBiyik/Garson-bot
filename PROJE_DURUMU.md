# Garson-bot — Proje Durumu ve Hedeflenen Hal
**Son güncelleme:** Mayıs 2026 | **Sürüm:** 2.7

Yeni bir sohbet başladığında bu dosyayı okuyarak projeyi baştan anlat.
Kod tabanını tekrar incelemene gerek yok — her şey burada.

---

## Proje Nedir?

Bir restoran için fiziksel servis robotuna (W-BOT) entegre edilecek Türkçe sesli yapay zeka asistanı.
Müşterilerle doğal konuşma, sipariş alma ve menü bilgisi sunma hedeflenmektedir.

**Donanım:** W-BOT robotu, üzerinde tablet ekran, ReSpeaker Mic Array v2.0 / USB 4-Mic Array XVF3000.
> ⚠️ Not: Bu cihaz **4 mikrofonludur**. 6 mikrofonlu ReSpeaker ayrı bir üründür (v1.0 = 7 mic, v2.0 = 4 mic).

**Ortam:** Gürültülü restoran — müzik, kalabalık, birden fazla konuşmacı.

---

## Klasör Yapısı

```
Garson-bot/
├── requirements.txt              # PyYAML, pytest, edge-tts, sounddevice, pyusb, numpy,
│                                 # fastapi, uvicorn[standard], python-multipart, httpx
├── requirements-llm.txt          # torch, transformers, peft, bitsandbytes, safetensors
├── pytest.ini                    # markers: unit, integration
├── scripts/
│   ├── benchmark_stt.py          # ✅ STT latency & RAM benchmark (Jetson Orin NX)
│   ├── benchmark_tts.py          # ✅ TTS latency & TTFA benchmark (edge-tts vs Piper)
│   └── benchmark_audio/          # ✅ silence_2s.wav, tone_440hz_4s.wav, tone_mix_6s.wav
└── robot_waiter_ai/
    ├── app/
    │   ├── main.py               # CLI entry point (run_cli) — Türkçe REPL
    │   └── config.py             # AppConfig dataclass, dosya yolları
    ├── assistant/
    │   ├── dialogue_manager.py   # Ana diyalog yöneticisi — intent routing, Türkçe yanıt
    │   ├── menu_knowledge.py     # Menü yükleme, normalizasyon, eşleştirme
    │   ├── order_state.py        # In-memory sipariş durumu (ekle/çıkar/özet)
    │   ├── persona.py            # Persona dataclass, default_persona()
    │   └── safety_rules.py       # Halüsinasyon önleme, allerjen uyarıları
    ├── inference/
    │   ├── qwen_lora_waiter.py   # Qwen2.5-3B + LoRA backend (4-bit, bitsandbytes)
    │   ├── menu_context_builder.py  # YAML → LLM prompt + _extract_menu_item_names()
    │   ├── hybrid_orchestrator.py   # NLU → safety → DialogueManager zinciri
    │   ├── deterministic_adapter.py # Kural tabanlı NLU (regex + keyword)
    │   ├── grounded_result_builder.py
    │   └── grounded_response_formatter.py
    ├── speech/
    │   ├── stt.py                # ✅ async faster-whisper STT wrapper
    │   ├── tts.py                # ✅ async edge-tts TTS wrapper
    │   ├── mic.py                # ✅ async ReSpeaker Mic Array v2.0 wrapper
    │   └── tuning.py             # ✅ Seeed-studio Tuning lib (AEC, DOA, AGC)
    ├── demo/
    │   ├── voice_web_demo.py     # ✅ FastAPI server: /chat /transcribe /tts /health /listen /ws/tts
    │   └── voice_web_demo.html   # ✅ Browser UI: MediaRecorder → /transcribe → /tts
    └── data/
        ├── menu.yaml             # Ürün id, name, category, price, allergens, aliases
        └── restaurant_info.yaml  # Çalışma saatleri, ödeme, politikalar
    tests/
        ├── test_stt.py                              # ✅  6/6  unit
        ├── test_tts.py                              # ✅ 16/16  unit
        ├── test_wakeword.py                         # ✅  9/9   unit
        ├── test_benchmark_stt.py                    # ✅ 17/17  unit
        ├── test_benchmark_tts.py                    # ✅ 27/27  unit
        ├── test_voice_web_demo.py                   # ✅  5/5   (unit markers yok)
        ├── test_voice_web_demo_backend_selection.py # ✅  6/6   (unit markers yok)
        ├── test_transcribe_route.py                 # ✅  7/7   integration
        └── test_listen_route.py                     # ✅  2/2   integration
```

---

## Tamamlanan Modüller

### `speech/stt.py` — Server-side STT
- **Motor:** faster-whisper
- **Default model:** `small` int8 (düşük RAM, hızlı)
- **Opsiyonel:** `medium` int8 (daha doğru, daha fazla RAM)
- **Dil:** Türkçe (`language="tr"` hardcoded)
- **VAD:** `vad_filter=True`, `min_silence_duration_ms=500`
- **Thread-safe:** `threading.Lock` double-checked locking
- **initial_prompt:** `build_initial_prompt(names)` → menü kelimelerini Whisper'a hint olarak verir
- **Async:** `asyncio.to_thread(_run_transcribe)` — generator thread içinde tüketilir
- **Dönüş:** `{"text", "language", "language_probability", "segments", "low_confidence"}`
- **Testler:** 6/6 unit test ✅

### `speech/tts.py` — Server-side TTS
- **Motor:** edge-tts (demo ve geliştirme için)
- **Ses:** `tr-TR-EmelNeural` veya `tr-TR-AhmetNeural`
- **Metot:** `async synthesize(text) → bytes` ve `async synthesize_streaming()`
- **Latency:** ~200-400ms ilk chunk
- **Production notu:** edge-tts internet bağımlı. Offline production için **Piper TTS** ayrıca benchmark edilecek.
- **Testler:** 16/16 unit test ✅ (test_tts.py — edge_tts.Communicate mock'lu, network gerekmez)

### `speech/mic.py` — ReSpeaker Mic Array v2.0
- **Donanım:** USB (idVendor=0x2886, idProduct=0x0018), **4 mikrofon**
- **Kanal:** Kanal 0 (beamformed + AEC uygulanmış, `channels=1`)
- **AEC/AGC/CNI:** `tuning.py` üzerinden USB control pipe ile etkinleştiriliyor
- **Kayıt:** `sd.rec()` pull-based, `asyncio.to_thread` ile async
- **DOA:** `async get_doa() → int` (0-359 derece)
- **Flag:** `is_capturing: bool` — eş zamanlı kayıt önleme
- **Çıktı:** 16-bit PCM WAV bytes (16kHz, mono) — stt.py ile doğrudan uyumlu
- **Yeni metodlar (v2.3):**
  - `listen_for_wakeword(model_path, threshold, timeout)` — 80 ms frame'lerle akış, openWakeWord inference
  - `listen_and_capture(model_path, seconds, threshold, timeout)` — wake word → capture zinciri
- **Wake word sabitleri:**
  - `DEFAULT_WAKEWORD_MODEL_PATH = "robot_waiter_ai/models/hey_garson.onnx"`
  - `DEFAULT_WAKEWORD_THRESHOLD = 0.5`
  - `WAKEWORD_CHUNK_SAMPLES = 1280` (80 ms @ 16 kHz)
- **Testler:** Smoke test (donanım gerektirir) ⚠️ — 9/9 mock unit test ✅ (test_wakeword.py)

### `demo/voice_web_demo.py` — FastAPI HTTP Server ✅ v2.5'te yeniden yazıldı

**Framework:** FastAPI + uvicorn (ThreadingHTTPServer kaldırıldı)

**Mimari değişiklikler (v2.5):**
- `create_app()` factory pattern: her test kendi izole app instance'ını alır
- Tüm route handler'lar `async def` — `asyncio.run()` yok
- Mic eş zamanlılık kontrolü: `threading.Lock` → `asyncio.Lock`
- `from fastapi import FastAPI, Request, WebSocket` **module seviyesinde** import edilmeli
  - ⚠️ `from __future__ import annotations` + FastAPI: annotation'lar string olur; `Request`
    module namespace'de değilse FastAPI query param sanır → **import'lar her zaman module düzeyinde olmalı**

**Routes:**
- `GET  /`           → `voice_web_demo.html`
- `GET  /health`     → JSON runtime bilgisi
- `GET  /tts?text=`  → MP3 bytes (audio/mpeg)
- `POST /chat`       → `handle_chat_request()` → JSON
- `POST /transcribe` → audio bytes → STT → JSON (Content-Length gerekli, >10MB → 413)
- `POST /listen`     → ReSpeaker capture → STT → JSON
- `WS   /ws/tts`     → streaming TTS: text mesaj gönder, MP3 chunk'ları al

**Pure helpers (framework'süz, doğrudan test edilebilir):**
- `build_chat_response(message, backend, qwen_backend, menu_context) → dict`
- `handle_chat_request(raw_body, backend, ...) → (status_code, payload)`
- `handle_transcribe_request(audio_bytes, *, stt, use_vad, initial_prompt) → (status_code, payload)`

**CLI flags:**
- `--backend`, `--stt-model`, `--stt-device`, `--stt-compute-type`, `--no-vad`, `--tts-voice`
- `--enable-mic` (default: kapalı), `--mic-seconds` (default: 4, max: 30)
- `--no-4bit`, `--qwen-base-model-path`, `--qwen-adapter-path`

**Port handling:** `uvicorn.run()` PermissionError/OSError yakalanır, `"Port X is unavailable"` mesajı yazdırılır.

**Test altyapısı:** FastAPI `TestClient` (httpx-backed) — gerçek sunucu gerekmez.

---

## Pipeline Durumu — Mevcut vs Hedef

### ✅ Şu An Çalışan Pipeline (Browser Tabanlı)

```
Kullanıcı konuşur
    │
    ▼
Browser MediaRecorder (audio/webm)
    │  POST /transcribe
    ▼
voice_web_demo.py → SpeechToText.transcribe()
    │  faster-whisper, VAD, tr, menü prompt
    ▼
{"text": "bir döner istiyorum", ...}
    │  POST /chat
    ▼
HybridOrchestrator → DialogueManager
    │  menü grounding, sipariş yönetimi
    ▼
{"response": "Döner 120 TL, onaylıyor musunuz?"}
    │  GET /tts?text=...
    ▼
TextToSpeech.synthesize() → MP3 bytes
    │
    ▼
Browser Audio() → Hoparlör
(TTS çalarken speakBtn disabled — audio.onended ile tekrar enable)
```

### ✅ Server-side Pipeline (ReSpeaker Bağlı, --enable-mic ile)

```
Kullanıcı konuşur
    │
    ▼
ReSpeaker Mic Array v2.0 (4 mic, beamformed, AEC)
    │  mic.py: await mic.capture(seconds=4)
    │  WAV bytes, 16kHz, 16-bit, mono
    │  POST /listen
    ▼
voice_web_demo.py → SpeechToText.transcribe()
    │  faster-whisper small/medium, VAD, tr
    ▼
{"text": "bir döner istiyorum", ...}
    │  POST /chat
    ▼
HybridOrchestrator → DialogueManager
    ▼
{"response": "Döner 120 TL, onaylıyor musunuz?"}
    │  GET /tts?text=...
    ▼
TextToSpeech.synthesize() → MP3 bytes → Browser Audio() → Hoparlör
```

> **Donanım smoke-test komutu:**
> ```powershell
> .\.venv\Scripts\python.exe -m robot_waiter_ai.demo.voice_web_demo --enable-mic --mic-seconds 4
> ```

---

## Eksik / Henüz Yapılmamış (Öncelik Sırasıyla)

| # | Eksik | Öncelik | Not |
|---|---|---|---|
| 1 | ~~`POST /listen` route~~ | ~~🔴 Kritik~~ | ✅ **Tamamlandı v2.2** |
| 2 | ~~`--enable-mic` CLI flag~~ | ~~🔴 Kritik~~ | ✅ **Tamamlandı v2.2** |
| 3 | ~~Frontend audio lock~~ | ~~🔴 Kritik~~ | ✅ **Tamamlandı v2.2** |
| 4 | ~~`mic.py` mock unit testleri~~ | ~~🟠 Yüksek~~ | ✅ **Tamamlandı v2.2** |
| 5 | ~~`tts.py` pytest testleri~~ | ~~🟠 Yüksek~~ | ✅ **Tamamlandı v2.3** |
| 6 | ~~Wake word — openWakeWord~~ | ~~🟡 Orta~~ | ✅ **Tamamlandı v2.3** |
| 7 | ~~Jetson STT benchmark~~ | ~~🟠 Yüksek~~ | ✅ **Tamamlandı v2.4** |
| 8 | ~~FastAPI'ye geçiş~~ | ~~🟡 Orta~~ | ✅ **Tamamlandı v2.5** — create_app() + uvicorn + TestClient |
| 9 | ~~Wake word Colab notebook~~ | ~~🟠 Yüksek~~ | ✅ **Tamamlandı v2.7** — colab_hey_garson_wakeword_training.ipynb |
| 10 | ~~Offline TTS — Piper benchmark~~ | ~~🟡 Orta~~ | ✅ **Tamamlandı v2.6** — benchmark_tts.py yazıldı |
| 11 | Çoklu konuşmacı — DOA + UX | 🟡 Orta | mic.get_doa() hazır |
| 12 | systemd watchdog + Docker | 🟢 Düşük | Production deployment |

---

## Model Bilgileri

| Parametre | Değer |
|---|---|
| Base model | `Qwen/Qwen2.5-3B-Instruct` |
| Local path | `robot_waiter_ai/models/Qwen2.5-3B-Instruct` |
| LoRA adapter | `qwen25_3b_waiter_v1_1_lora` |
| Adapter dosyaları | `adapter_config.json` + `adapter_model.safetensors` |
| Quantization | `BitsAndBytesConfig(load_in_4bit=True)` — CUDA varsa aktif |
| Max new tokens | 120, repetition_penalty=1.05 |

---

## STT Model Seçim Rehberi

| Model | RAM | Türkçe Kalite | Latency | Kullanım |
|---|---|---|---|---|
| `small` int8 | ~1 GB | İyi | ~400ms | ✅ Default |
| `medium` int8 | ~3 GB | Çok iyi | ~800ms | Opsiyonel |
| `large-v3` int8 | ~6 GB | Mükemmel | ~1.5s | Yüksek RAM'li GPU |

> Jetson Orin NX'te Qwen + STT + TTS aynı anda çalışacak.
> `small` ile başla, benchmark sonrası `medium`'a geç.

---

## TTS Seçim Notu

| Motor | Kalite | Offline | Durum |
|---|---|---|---|
| edge-tts | ⭐⭐⭐⭐⭐ | ❌ | Demo ve geliştirme |
| Piper TTS | ⭐⭐⭐⭐ | ✅ | Production adayı — benchmark_tts.py ile ölç |
| Coqui XTTS v2 | ⭐⭐⭐⭐ | ✅ | GPU gerektirir |

---

## Geliştirme Kuralları (Her Zaman Uygula)

1. **Mevcut browser pipeline'ı bozma** — `/transcribe`, `/chat`, `/tts` route'ları çalışmaya devam etmeli
2. **Async-first** — tüm I/O `asyncio.to_thread` ile, blocking call event loop'ta yok
3. **Lazy import** — ağır bağımlılıklar fonksiyon içinde import edilmeli (FastAPI/uvicorn hariç — bunlar module seviyesinde olmalı)
4. **Her diyalog sonrası bellek temizle** — `gc.collect()` + `torch.cuda.empty_cache()`
5. **UTF-8 zorunlu** — tüm dosya okuma/yazma `encoding='utf-8'`
6. **Fuzzy matching** — menü eşleştirme `rapidfuzz` ile
7. **Türkçe hata mesajları** — müşteriye dönük mesajlar Türkçe
8. **Test yaz** — her yeni modül için en az bir pytest
9. **voice_web_demo.py bash ile yaz** — Windows→Linux mtime sync sorunu var; Edit/Write tool değil, bash heredoc (veya Python ile in-place write) kullan
10. **--enable-mic flag** — donanım bağımlı özellikler varsayılan kapalı olmalı
11. **FastAPI + `from __future__ import annotations`** — `Request`, `WebSocket` gibi FastAPI tipleri module seviyesinde import edilmeli; fonksiyon içi import + annotations=True → FastAPI query param sanır

---

## Test Durumu

```
pytest -m unit        →  75/75  ✅  (stt×6, tts×16, wakeword×9, benchmark_stt×17, benchmark_tts×27)
pytest -m integration →   9/9  ✅  (test_transcribe_route×7, test_listen_route×2)
pytest (tümü)         →  84 marked test geçiyor ✅
```

---

## Benchmark Kullanım Notu (v2.4)

Jetson Orin NX'te çalıştırmak için:

```powershell
# Tüm varsayılanlarla (small + medium, 10 run, CPU int8):
python scripts/benchmark_stt.py

# Sadece small, CUDA float16, 5 run:
python scripts/benchmark_stt.py --models small --device cuda --compute-type float16 --runs 5

# Sonuçlar:  benchmarks/stt_<TIMESTAMP>.json  +  .csv
```

Test ses dosyaları: `scripts/benchmark_audio/` (silence_2s, tone_440hz_4s, tone_mix_6s)
Gerçek Türkçe ses eklemek için aynı dizine 16kHz mono WAV dosyası koy.
---

## TTS Benchmark Kullanım Notu (v2.6)

```powershell
# edge-tts (internet bağlı, varsayılan — 5 run, 2 ses, 5 cümle):
python scripts/benchmark_tts.py

# Sadece EmelNeural, 10 run:
python scripts/benchmark_tts.py --runs 10 --edge-voices tr-TR-EmelNeural

# Piper ile karşılaştırma (model indirilmişse):
python scripts/benchmark_tts.py --engines edge-tts piper \
    --piper-binary piper/piper.exe \
    --piper-model robot_waiter_ai/models/tr_TR-fahrettin-medium.onnx

# Sonuçlar:  benchmarks/tts_<TIMESTAMP>.json  +  .csv
```

Piper modeli indirmek için:
  https://huggingface.co/rhasspy/piper-voices/tree/main/tr/tr_TR/fahrettin/medium
Modeli `robot_waiter_ai/models/tr_TR-fahrettin-medium.onnx` olarak kaydet.

**Üretim kararı:** Piper medyan latency < 300 ms ise offline'a geç; aksi hâlde edge-tts koru.


---

## Bir Sonraki Görev

Öncelik sırasıyla:

```
1. Hey Garson model eğitimini Colab'da çalıştır (🟠 Yüksek):
   - Notebook: robot_waiter_ai/notebooks/colab_hey_garson_wakeword_training.ipynb
   - Colab'da aç → Çalışma Zamanı → T4 GPU → Tümünü Çalıştır
   - K hücresinde hey_garson.onnx indirilecek
   - İndir → robot_waiter_ai/models/hey_garson.onnx kaydet
   - Smoke test: python -m robot_waiter_ai.speech.mic

2. Piper TTS modeli indir + çalıştır (🟡 Orta):
   - benchmark_tts.py hazır — sadece Piper binary + model gerekli
   - İndir: https://huggingface.co/rhasspy/piper-voices (tr_TR-fahrettin-medium)
   - Koştur: python scripts/benchmark_tts.py --engines edge-tts piper
   - Hedef: medyan latency < 300 ms → production'da edge-tts yerine geç

3. systemd watchdog + Docker (🟢 Düşük):
   - Production deployment için robot süreç yönetimi
```

---

## Başarı Kriterleri

```
Müşteri: "Ayran ne kadar?"
Robot:   "Ayran 35 TL'dir, buyurun."              ✅

Müşteri: "Paket servis var mı?"
Robot:   "Menümüzde bu detay yok, personelimize sorabilirsiniz."  ✅

Müşteri: "Ayran ne kadar?"
Robot:   "Güvenlik garantisi veremem."             ❌ Asla

8 saat çalışma sonrası:
Robot:   Hâlâ yanıt veriyor, OOM yok              ✅
```
