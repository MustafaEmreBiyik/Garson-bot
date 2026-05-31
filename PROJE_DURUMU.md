# Garson-bot — Proje Durumu ve Hedeflenen Hal
**Son güncelleme:** 31 Mayıs 2026 | **Sürüm:** 4.1

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
| Jetson Orin NX 16GB | Orin GPU (SM87) | llama_cpp_backend.py (GGUF, llama-cpp-python) | ⚠️ Ses adaptörü eksik |

---

## Klasör Yapısı (Aktif Dosyalar)

```
Garson-bot/
├── scripts/
│   ├── demo_usb.py               ✅ Ana demo — wake word → STT → LLM → Piper TTS
│   ├── eval_llm.py               ✅ LLM kalite + performans eval (10 senaryo, 16 turn)
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
        ├── menu.yaml             ✅ Menü tanımları (name, category, price, description, aliases)
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
faster-whisper small (CUDA varsa float16, yoksa CPU int8 — auto-detect)
    │  initial_prompt ile menü kelimeleri Whisper'a hint
    ▼
OrderTracker — kullanıcı metnini parse et, sipariş toplamını takip et
    │  menu.yaml aliases ile eşleştir, Python-tarafında toplam hesapla
    │  Hesap istenince LLM girdisine "[Gerçek toplam: X TL]" ekle
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
| n_ctx | **1536** (2048'den düşürüldü — sistem prompt 706 tok, ~25 tur kapasitesi) |
| max_tokens | **80** (gerçek yanıt max ~53 tok, 1.5× emniyet marjı) |

### PC — qwen3_backend.py
| Parametre | Değer |
|-----------|-------|
| Model | Qwen/Qwen3-4B (HuggingFace) |
| Quantization | BitsAndBytesConfig 4-bit NF4 |
| Thinking | enable_thinking=False (apply_chat_template) |
| max_new_tokens | **80**, repetition_penalty=1.1 |

### Sistem Prompt Token Bütçesi
| Öğe | Token |
|-----|-------|
| Sistem prompt (sabit metin) | ~706 |
| n_ctx | 1536 |
| Konuşmaya kalan | ~830 (~25 tur) |

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
| Device | CUDA varsa float16, yoksa CPU int8 (otomatik algılama) |
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

**Piper GPU (onnxruntime-gpu):** Jetson JetPack R36 için pip'te mevcut değil — ertelenmiş.

---

## OrderTracker (demo_usb.py)

Kullanıcı metnini Python tarafında parse ederek doğru sipariş toplamını hesaplar.
LLM'in çıktısına değil, kullanıcının söylediğine bakılır — LLM format uyumsuzluklarına karşı dayanıklı.

```python
# Tetikleyici fiiller
_ORDER_VERBS = {"istiyorum", "alayım", "alabilir", "getirir", "lütfen",
                "tane", "adet", "istiyom", "alalım", "getir", "ver"}

# Hesap istenince LLM girdisine eklenir:
llm_input = f"{user_text} [Gerçek toplam: {order_tracker.total} TL]"
```

Menüdeki `aliases` alanı eşleştirme için kullanılır. Çoklu ürün desteği var (break yok).

---

## LLM Eval Sonuçları (eval_llm.py)

`python3 scripts/eval_llm.py --backend qwen -v` ile çalıştırılır.

| Versiyon | Pass | Fail | Notlar |
|---------|------|------|--------|
| Prompt v4.0 (önceki) | 14/16 (%87) | 2 | S03 ürün açıklaması yok, S05 çoklu sipariş eksik |
| **Prompt v4.1 (güncel)** | **16/16 (%100)** | **0** | — |

**Düzeltilen sorunlar (v4.0 → v4.1):**
- S03: "Künefe nedir?" → artık açıklama + "Getireyim mi?" geliyor
- S05: "Köfte ve ayran" → her ürün ayrı ayrı onaylanıyor
- S01: "Turkish restoranında misin" → temiz Türkçe karşılama

**Ortalama yanıt süresi (Qwen PC):** 1734 ms | Min: 1249 ms | Max: 2234 ms

---

## Jetson Deployment Durumu

### Kurulu Bileşenler ✅
- JetPack R36.5.0, CUDA 12.6, Python 3.10
- faster-whisper + Whisper small modeli (~464MB, `~/.cache/huggingface/hub/`)
- sounddevice, portaudio
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
| Python API ortalama yanıt süresi | 2.40 sn |
| STT (Whisper small, GPU) tahmini | ~0.70 sn |
| Piper TTS (CPU) | ~0.60 sn |
| **Toplam tahmini boru hattı** | **~3.70 sn** (hedef < 5 sn ✅) |

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

## Kısa Vadede Yapılacaklar (Bloker)

| # | Görev | Öncelik | Durum |
|---|-------|---------|-------|
| 1 | USB ses adaptörü temin et (~100 TL, USB→3.5mm) | 🔴 Kritik | Donanım yok — tüm ses testleri buna bağlı |
| 2 | ALSA_OUTPUT_DEVICE ayarla (`aplay -l` ile USB adaptörünü bul) | 🔴 Kritik | Adaptör geldikten sonra |
| 3 | Tam uçtan uca demo (wake word→STT→LLM→TTS→hoparlör) | 🔴 Kritik | Adaptöre bağlı |
| 4 | Wake word gerçek ortam testi (restoran gürültüsü) | 🟠 Yüksek | Adaptöre bağlı |
| 5 | Whisper small kalite doğrulaması (Türkçe restoran kelimeleri) | 🟠 Yüksek | Adaptöre bağlı |

## Uzun Vadede / Beklemede

| # | Görev | Açıklama |
|---|-------|----------|
| 6 | Piper GPU (onnxruntime-gpu) | JetPack R36 aarch64 için pip'te yok — ertelenmiş |
| 7 | systemd servis (otomatik başlatma) | Stabil olduktan sonra |
| 8 | Wake word yeniden eğitimi (gerçek seslerle) | Sentetik eğitim yetersiz kalırsa |

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

LLM kalite (eval_llm.py):  16/16 PASS (%100)                                    ✅
Yanıt süresi:              < 5 sn (tahmini ~3.70 sn Jetson'da)                  ✅
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
8. **STT device auto-detect** — CUDA varsa float16, yoksa CPU int8 (hardcode etme)
9. **OrderTracker kullanıcı metnini parse eder** — LLM çıktısını değil
