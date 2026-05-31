# Garson-bot — Proje Durumu ve Hedeflenen Hal
**Son güncelleme:** 31 Mayıs 2026 | **Sürüm:** 4.3

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
│   ├── demo_usb.py               ✅ Ana demo — wake word → VAD kayıt → STT → LLM → Piper TTS
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

## Aktif Pipeline (demo_usb.py — v4.3)

```
"hey garson" denir
    │  openWakeWord (hey_garson.onnx, threshold=0.7)
    │  USB mikrofon auto-detect (_find_input_device → "USB PnP" → device=24)
    ▼
VAD tabanlı kayıt (_record)
    │  webrtcvad (aggressiveness=3) veya enerji eşiği fallback
    │  Native rate (48kHz) → np.interp → 16kHz, 30ms chunk
    │  Pre-roll: konuşma başlamadan 150ms tutar
    │  1.5s sessizlik → durdur (max 12s güvenlik kapağı)
    ▼
faster-whisper small (CUDA varsa float16, yoksa CPU int8 — auto-detect)
    │  initial_prompt ile menü kelimeleri Whisper'a hint
    ▼
OrderTracker — kullanıcı metnini parse et, sipariş toplamını takip et
    │  Ekleme: "X alayım/istiyorum" → fiyat ekle
    │  İptal: "X iptal/istemiyorum" → fiyat çıkar (min 0)
    │  Takas: "X yerine Y" → X çıkar, Y ekle
    │  Per-item adet tespiti: alias önceki 1-2 kelimeye bakılır
    │  Türkçe İ fix: "İ".lower() → "i̇" birleştirme noktası temizlenir
    │  Hesap istenince LLM girdisine "[Gerçek toplam: X TL]" ekle
    ▼
LLM — otomatik seçim:
    │  llama_cpp_backend.py varsa → Qwen3-4B Q4_K_M GGUF (Jetson)
    │  yoksa → qwen3_backend.py → Qwen3-4B transformers (PC)
    │  Streaming: stream_reply() → token akışı → cümle sonu tespiti
    ▼
_speak_streaming pipeline (paralel):
    │  LLM thread → sentence_q → tts_worker → audio_q → play_worker
    │  İlk cümle hazır olunca TTS başlar, LLM arka planda devam eder
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
| n_ctx | **1536** |
| max_tokens | **80** (gerçek yanıt max ~53 tok, 1.5× emniyet marjı) |
| _MAX_HIST_CHARS | **1400** — aşılınca en eski user+assistant turu silinir |

### PC — qwen3_backend.py
| Parametre | Değer |
|-----------|-------|
| Model | Qwen/Qwen3-4B (HuggingFace) |
| Quantization | BitsAndBytesConfig 4-bit NF4 |
| Thinking | enable_thinking=False (apply_chat_template) |
| max_new_tokens | **80**, repetition_penalty=1.1 |
| _MAX_HIST_CHARS | **6000** |

### Sistem Prompt Token Bütçesi (Jetson)
| Öğe | Token |
|-----|-------|
| Sistem prompt (sabit metin) | ~944 |
| n_ctx | 1536 |
| max_tokens | 80 |
| Konuşmaya kalan | ~512 (~5-6 tur) |

**_trim_history():** Toplam geçmiş karakter sayısı _MAX_HIST_CHARS'ı aşınca en eski
user+assistant ikilisi silinir. Billing bu mekanizmadan etkilenmez — OrderTracker
Python tarafında bağımsız çalışır.

### KV Cache Ön Isıtma
Startup'ta `generate_reply("Merhaba.") + reset_history()` çağrısı yapılır.
Sistem promptunun (~944 tok) KV cache'e yazılmasını sağlar.
- Soğuk start TTFT: ~2.96s
- Sıcak start TTFT: ~0.25s (12× iyileşme)

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

### USB Mikrofon VAD Kaydı (v4.3)
Eski: `sd.rec` ile sabit 6 sn kayıt.
Yeni: `sd.InputStream` + webrtcvad ile değişken süreli kayıt.

```python
VAD_AGGRESSIVENESS = 3     # 0-3 (3 = gürültülü ortam)
VAD_CHUNK_MS       = 30    # webrtcvad için geçerli değer (10/20/30)
VAD_SILENCE_S      = 1.5   # sessizlik süresi → kayıt biter
VAD_PRE_ROLL       = 5     # konuşma öncesi 150ms ring buffer
VAD_MAX_S          = 12    # güvenlik kapağı
VAD_ENERGY_THRESH  = 300   # webrtcvad yoksa enerji eşiği fallback
```

Resample: USB PnP mikrofon native 48kHz, np.interp ile 16kHz'ye dönüştürülür.
webrtcvad yoksa enerji tabanlı fallback devreye girer.

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

## OrderTracker (demo_usb.py) — v4.3

Kullanıcı metnini Python tarafında parse ederek doğru sipariş toplamını hesaplar.
LLM'in çıktısına değil, kullanıcının söylediğine bakılır.

```python
_ORDER_VERBS  = {"istiyorum", "alayım", "alabilir", "getirir", "lütfen",
                 "tane", "adet", "istiyom", "alalım", "getir", "ver"}
_CANCEL_VERBS = {"istemiyorum", "istemiyom", "iptal", "çıkar", "çıkarın", "kaldır"}
_QUANTITIES   = {"iki": 2, "üç": 3, "dört": 4, "2": 2, "3": 3, "4": 4}
```

`detect_order()` üç dala ayrılır:
1. **"X yerine Y"** → X çıkar, Y ekle
2. **Cancel verb** → eşleşen ürünü çıkar (min 0, negatife düşmez)
3. **Order verb** → eşleşen ürünü ekle

Race condition fix: `detect_order()` her zaman bill check'ten ÖNCE çağrılır;
aynı cümlede "sütlaç alayım + hesap" varsa sütlaç toplamda yer alır.

**Manuel test sonuçları (v4.3):**
- "İki köfte bir mantar çorbası alayım." → 575 TL ✅ (2×240 + 95)
- "İki tane ayran alabilir miyim?" → 90 TL ✅ (2×45)
- "Köfteyi iptal et." → 0 TL ✅ (240 çıkarıldı)
- "Köfte yerine sütlaç istiyorum." → 100 TL ✅ (240 çıkar, 100 ekle)
- "Toplam tutar ne kadar?" → 575 TL ✅ (LLM'e [Gerçek toplam] enjekte edildi)

---

## LLM Eval Sonuçları

`python3 scripts/eval_llm.py --backend qwen -v` ile çalıştırılır.

| Versiyon | Pass | Fail | Ort. Süre | Min | Max |
|---------|------|------|-----------|-----|-----|
| Prompt v4.0 (önceki) | 14/16 (%87) | 2 | — | — | — |
| Prompt v4.1 | 16/16 (%100) | 0 | 1734 ms | — | — |
| **Prompt v4.1 (v4.3 kodu, 31 Mayıs 2026)** | **16/16 (%100)** | **0** | **1745 ms** | **1219 ms** | **2423 ms** |

---

## Bilinen LLM Zayıflıkları (Eval Dışı)

| # | Senaryo | Sorun | Kök Neden | Durum |
|---|---------|-------|-----------|-------|
| W1 | Vejetaryen sorusu | Ürün listesi vermiyor | Sistem promptunda tags + kural var | ✅ Düzeltildi |
| W2 | Alerji sorusu | Aşırı savunmacı | Sistem promptunda allergens + kural var | ✅ Düzeltildi |
| W3 | İptal/değişiklik | LLM iptali yok sayıyor | Prompt'ta kural eklendi + OrderTracker cancellation | ✅ Düzeltildi |
| W4 | Adet gösterimi | "iki Izgara Köfte" yerine "Izgara Köfte" | Prompt kuralı + örnek eklendi | ✅ Düzeltildi |

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
| ⚠️ Jetson | `openwakeword` paketi kurulu değil → ENTER tuşu modu aktif |

---

## demo_usb.py Yapılandırma Sabitleri

```python
WHISPER_MODEL      = "small"
SAMPLE_RATE        = 16_000
CHANNELS           = 1

# VAD kayıt
VAD_AGGRESSIVENESS = 3
VAD_CHUNK_MS       = 30
VAD_SILENCE_S      = 1.5
VAD_PRE_ROLL       = 5
VAD_MAX_S          = 12
VAD_ENERGY_THRESH  = 300

WAKEWORD_THRESHOLD = 0.7
ALSA_OUTPUT_DEVICE = None   # None=sistem default, "plughw:2,0"=Jetson APE
```

---

## Jetson Deployment Durumu

### Kurulu Bileşenler ✅
- JetPack R36.5.0, CUDA 12.6, Python 3.10
- faster-whisper + Whisper small modeli (~464MB)
- sounddevice, portaudio
- onnxruntime (GPU uyarısıyla çalışıyor)
- Piper TTS (piper_linux_aarch64)
- llama-cpp-python 0.3.23 (CUDA SM87 ile derlendi)
- Qwen3-4B-Q4_K_M.gguf (/home/emk/llama.cpp/)
- webrtcvad ✅ (VAD için, aarch64 uyumlu)
- Proje: /home/emk/Desktop/Garson-bot/Garson-bot/ (iç içe dizin)

### Ses Donanımı Durumu
| Cihaz | Durum | Açıklama |
|-------|-------|----------|
| USB Mikrofon (USB PnP Sound Device) | ✅ card 2, device 24 | Native 48kHz → 16kHz resample |
| USB Hoparlör | ❌ Playback yok | USB sadece güç, ses için 3.5mm gerekiyor |
| Jetson APE (card 2) | ❌ Analog codec yok | Dijital DSP, doğrudan 3.5mm çıkış yok |
| HDMI (card 1) | ❌ Monitörde hoparlör yok | |

**Çözüm:** USB ses adaptörü (USB → 3.5mm) gerekiyor — ~100 TL

### Performans Ölçümleri (Jetson, Sıcak Start)
| Ölçüm | Sonuç |
|-------|-------|
| llama-bench pp512 | 492 tok/s |
| llama-bench tg128 | 14.97 tok/s |
| TTFT (soğuk — KV cache boş) | ~2.96 sn |
| TTFT (sıcak — KV cache dolu) | ~0.25 sn |
| STT (Whisper small, GPU) | ~0.70 sn |
| Piper TTS (CPU) | ~0.60 sn |
| **İlk ses çıkana kadar (sıcak)** | **~1.4-2.3 sn** |

---

## Kısa Vadede Yapılacaklar

| # | Görev | Öncelik | Durum |
|---|-------|---------|-------|
| 1 | USB ses adaptörü temin et (~100 TL, USB→3.5mm) | 🔴 Kritik | Donanım yok — tüm ses testleri buna bağlı |
| 2 | ALSA_OUTPUT_DEVICE ayarla (`aplay -l` ile USB adaptörünü bul) | 🔴 Kritik | Adaptör geldikten sonra |
| 3 | Tam uçtan uca demo (wake word→STT→LLM→TTS→hoparlör) | 🔴 Kritik | Adaptöre bağlı |
| 4 | openwakeword Jetson'a kur | 🟠 Yüksek | ENTER modundan wake word moduna geç |
| 5 | Wake word gerçek ortam testi (restoran gürültüsü) | 🟡 Orta | Adaptör + openwakeword sonrası |
| 6 | Whisper small kalite doğrulaması (Türkçe restoran kelimeleri) | 🟡 Orta | Adaptöre bağlı |

## Uzun Vade / Ertelenmiş

| # | Görev | Açıklama |
|---|-------|----------|
| 7 | Piper GPU (onnxruntime-gpu) | JetPack R36 aarch64 için pip'te yok — ertelenmiş |
| 8 | systemd servis (otomatik başlatma) | Stabil olduktan sonra |

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

Müşteri: "İki köfte bir mantar çorbası alayım."
Robot:   "...Izgara Köfte... Kremalı Mantar Çorbası... Başka bir şey alır mısınız?"
Toplam:  575 TL  (OrderTracker: 2×240 + 1×95)                                   ✅

Müşteri: "Aslında köfteyi istemiyorum."
Robot:   "Anladım, Izgara Köfte siparişinizden çıkarıldı."
Toplam:  95 TL  (OrderTracker: 575 - 240×2)                                     ✅

LLM kalite (eval_llm.py):  16/16 PASS (%100)                                    ✅
İlk ses (Jetson, sıcak):   ~1.4-2.3 sn                                          ✅
```

---

## Geliştirme Kuralları

1. **Async-first** — tüm I/O `asyncio.to_thread` ile
2. **aplay ile ses çal** — sounddevice playback değil (USB cihaz çakışmasını önler)
3. **USB mikrofon auto-detect** — `_find_input_device()` ile, hardcoded index değil
4. **Native rate resample** — `sd.query_devices(device)["default_samplerate"]` → `np.interp` → 16kHz
5. **LLM backend otomatik seçim** — llama_cpp_backend önce, qwen3_backend fallback
6. **Thinking modu kapalı** — Qwen3 `<think>` bloklarını hem strip et hem baştan engelle
7. **ALSA_OUTPUT_DEVICE** — Jetson'da ses cihazı değişirse bu sabiti güncelle
8. **UTF-8 zorunlu** — tüm dosya okuma/yazma `encoding='utf-8'`
9. **OrderTracker kullanıcı metnini parse eder** — LLM çıktısını değil
10. **Türkçe İ fix** — `user_text.lower().replace('̇', '')` (U+0307 birleştirme noktası)
11. **scipy kullanma** — NumPy 2.x uyumsuz, np.interp yeterli
12. **KV cache ön ısıtma** — startup'ta `generate_reply("Merhaba.") + reset_history()`
