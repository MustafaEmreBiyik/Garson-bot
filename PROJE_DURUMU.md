# Garson-bot — Proje Durumu ve Hedeflenen Hal
**Son güncelleme:** 31 Mayıs 2026 | **Sürüm:** 4.2

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
    │  USB mikrofon auto-detect (_find_input_device → "USB PnP" → device=24)
    ▼
6 sn kayıt (sd.rec, device=native_sr → np.interp ile 16kHz'ye resample)
    ▼
faster-whisper small (CUDA varsa float16, yoksa CPU int8 — auto-detect)
    │  initial_prompt ile menü kelimeleri Whisper'a hint
    ▼
OrderTracker — kullanıcı metnini parse et, sipariş toplamını takip et
    │  Per-item adet tespiti: alias önceki 1-2 kelimeye bakılır
    │  Türkçe İ fix: "İ".lower() → "i̇" birleştirme noktası temizlenir
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

### USB Mikrofon Resample (v4.2'de eklendi)
USB PnP mikrofon native 48kHz destekliyor, 16kHz'de `paInvalidSampleRate` veriyordu.
Çözüm: `sd.query_devices(device)["default_samplerate"]` ile native rate'te kayıt,
`np.interp` ile 16kHz'ye lineer interpolasyon. scipy kaldırıldı (NumPy 2.x uyumsuz).

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

## OrderTracker (demo_usb.py) — v4.2

Kullanıcı metnini Python tarafında parse ederek doğru sipariş toplamını hesaplar.
LLM'in çıktısına değil, kullanıcının söylediğine bakılır.

```python
# Tetikleyici fiiller
_ORDER_VERBS = {"istiyorum", "alayım", "alabilir", "getirir", "lütfen",
                "tane", "adet", "istiyom", "alalım", "getir", "ver"}

# Per-item adet tespiti — alias'dan önce 1-2 kelimeye bak
# "iki köfte" → qty=2  |  "iki tane köfte" → qty=2  |  "bir köfte" → qty=1
m1 = re.search(r'(\w+)\s+' + re.escape(alias), t)
m2 = re.search(r'(\w+)\s+\w+\s+' + re.escape(alias), t)
qty = _QUANTITIES.get(m1.group(1), 1) if m1 else 1
if qty == 1 and m2: qty = _QUANTITIES.get(m2.group(1), 1)

# Türkçe İ fix: "İ".lower() → "i̇" (U+0307), regex \w+ bunu kesiyor
t = user_text.lower().replace('̇', '')

# Hesap istenince LLM girdisine eklenir:
_BILL_KEYWORDS = ["hesab", "ödeyeyim", "ödüyorum", "parayı öde", "hesap lütfen",
                  "toplam", "tutar", "ne kadar tut", "kaç tl", "kaç lira"]
```

**Manuel test sonuçları (v4.2):**
- "İki köfte bir mantar çorbası alayım." → 575 TL ✅ (2×240 + 95)
- "İki tane ayran alabilir miyim?" → 90 TL ✅ (2×45)
- "2 köfte 3 ayran istiyorum." → 615 TL ✅
- "Toplam tutar ne kadar?" → 575 TL ✅ (LLM'e [Gerçek toplam] enjekte edildi)

---

## LLM Eval Sonuçları

`python3 scripts/eval_llm.py --backend qwen -v` ile çalıştırılır.

| Versiyon | Pass | Fail | Ort. Süre | Min | Max |
|---------|------|------|-----------|-----|-----|
| Prompt v4.0 (önceki) | 14/16 (%87) | 2 | — | — | — |
| Prompt v4.1 | 16/16 (%100) | 0 | 1734 ms | — | — |
| **Prompt v4.1 (v4.2 kodu, 31 Mayıs 2026)** | **16/16 (%100)** | **0** | **1745 ms** | **1219 ms** | **2423 ms** |

Eval kapsamı dışında tespit edilen sorunlar (aşağıda detay).

---

## Bilinen LLM Zayıflıkları (Eval Dışı Testler — 31 Mayıs 2026)

| # | Senaryo | Kullanıcı | Bot Yanıtı | Sorun | Kök Neden |
|---|---------|-----------|------------|-------|-----------|
| W1 | Vejetaryen sorusu | "Vejetaryen ne var?" | "Çorbalar, ana yemekler... Ne istersiniz?" | Spesifik ürün listesi yok | Sistem promptunda `tags` bilgisi yok |
| W2 | Alerji sorusu | "Süt alerjim var, ne yiyebilirim?" | "Bu konuda bilgim yok, personelimize sorabilirsiniz." | Aşırı savunmacı — allergen bilgisi verilebilir | Sistem promptunda `allergens` bilgisi yok |
| W3 | İptal / değişiklik | "Köfte ve ayran istiyorum." → "Aslında köfte istemiyorum, döner alayım." | Erken "Afiyet olsun" + iptali yok | Köfte silinmedi, ikinci sıraya da erken bitti | Prompt'ta iptal/değişiklik senaryosu yok |
| W4 | LLM adet gösterimi | "İki köfte bir mantar çorbası alayım." | "Izgara Köfte 240 TL eklendi." | Miktarı göstermedi (1 gibi davrandı) | LLM'in kendi bağlamında adet takibi yok (OrderTracker hallediyor ama LLM mesajı yanlış) |

**Not:** W4 için OrderTracker doğru çalışıyor (575 TL hesaplandı), sadece LLM'in onay mesajı "iki" adeti yansıtmıyor. Gerçek toplam her zaman OrderTracker'dan alınıyor.

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
WHISPER_MODEL      = "small"           # medium → small (31 Mayıs 2026)
SAMPLE_RATE        = 16_000            # Hedef rate — kayıt native rate'te yapılır
RECORD_SECONDS     = 6
WAKEWORD_THRESHOLD = 0.7
ALSA_OUTPUT_DEVICE = None              # None=sistem default, "plughw:2,0"=Jetson APE
```

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

### Ses Donanımı Durumu
| Cihaz | Durum | Açıklama |
|-------|-------|----------|
| USB Mikrofon (USB PnP Sound Device) | ✅ card 2, device 24 | Native 48kHz → 16kHz resample |
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

## Kısa Vadede Yapılacaklar (Bloker)

| # | Görev | Öncelik | Durum |
|---|-------|---------|-------|
| 1 | USB ses adaptörü temin et (~100 TL, USB→3.5mm) | 🔴 Kritik | Donanım yok — tüm ses testleri buna bağlı |
| 2 | ALSA_OUTPUT_DEVICE ayarla (`aplay -l` ile USB adaptörünü bul) | 🔴 Kritik | Adaptör geldikten sonra |
| 3 | Tam uçtan uca demo (wake word→STT→LLM→TTS→hoparlör) | 🔴 Kritik | Adaptöre bağlı |
| 4 | openwakeword Jetson'a kur | 🟠 Yüksek | ENTER modundan wake word moduna geç |
| 5 | W1/W2: Sistem promptuna allergens + tags ekle (vejetaryen/alerji yanıtları) | 🟠 Yüksek | Prompt düzenlemesi |
| 6 | W3: Sipariş iptali/değişikliği prompt'a ekle | 🟡 Orta | |
| 7 | W4: LLM onay mesajında adeti göster ("İki Izgara Köfte") | 🟡 Orta | Prompt düzenlemesi |

## Uzun Vadede / Beklemede

| # | Görev | Açıklama |
|---|-------|----------|
| 8 | Wake word gerçek ortam testi (restoran gürültüsü) | Sentetik eğitim yetersiz kalırsa yeniden eğit |
| 9 | Whisper small kalite doğrulaması (Türkçe restoran kelimeleri) | Adaptöre bağlı |
| 10 | Piper GPU (onnxruntime-gpu) | JetPack R36 aarch64 için pip'te yok — ertelenmiş |
| 11 | systemd servis (otomatik başlatma) | Stabil olduktan sonra |

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

LLM kalite (eval_llm.py):  16/16 PASS (%100)                                    ✅
Yanıt süresi PC:            1745 ms ort. (min 1219, max 2423)                   ✅
Yanıt süresi Jetson (est.): ~3.70 sn toplam boru hattı                          ✅
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
