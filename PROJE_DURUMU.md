# Garson-bot — Proje Durumu ve Hedeflenen Hal
**Son güncelleme:** 3 Haziran 2026 | **Sürüm:** 5.1

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

## Aktif Pipeline (demo_usb.py — v4.7)

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
faster-whisper small (CUDA varsa float16, yoksa CPU float32 — auto-detect)
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
10s konuşma penceresi (CONVO_HOLD_S) — wake word'süz dinle
    │  konuşma gelirse → tur devam (LLM history korunur)
    │  10s sessizlikte → wake word moduna dön (varsa farewell → yeni müşteri reset)
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
| max_tokens | **50** (v4.8 — yanıtlar daha özlü; 1 cümle / 20 kelime hedefi) |
| Decoding | temperature=0.55, top_p=0.9, top_k=40, repeat_penalty=1.2 (v4.8) |
| _MAX_HIST_CHARS | **1400** — aşılınca en eski user+assistant turu silinir |

### PC — qwen3_backend.py
| Parametre | Değer |
|-----------|-------|
| Model | Qwen/Qwen3-4B (HuggingFace) |
| Quantization | BitsAndBytesConfig 4-bit NF4 |
| Thinking | enable_thinking=False (apply_chat_template) |
| max_new_tokens | **50** (v4.8) |
| Decoding | do_sample=True, temperature=0.55, top_p=0.9, top_k=40, repetition_penalty=1.2 (v4.8) |
| _MAX_HIST_CHARS | **12000** (v4.5'te 6000'den artırıldı) |
| local_files_only | İlk indirmeden sonra HF Hub'a istek atılmaz |
| VRAM izleme | Yükleme sonrası kullanılan/toplam VRAM ekrana basılır |

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
| Model (PC) | **small** (v4.6 — host VRAM 5.64 GB; Qwen3-4B + Whisper medium birlikte OOM oluyordu) |
| Model (Jetson hedefi) | **medium** (16 GB VRAM ile birlikte sığar; entegrasyonda açılacak) |
| Device seçimi | Toplam VRAM ≥ 8 GB → CUDA float16; aksi halde CPU int8. `W_BOT_STT_DEVICE` env'i ile override edilebilir. |
| Latency (PC CPU int8, small) | ~130-300ms |
| Latency (Jetson CUDA float16, medium hedefi) | ~1500-2000ms |
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
| Prompt v4.1 (v4.3 kodu, 31 Mayıs 2026) | 16/16 (%100) | 0 | 1745 ms | 1219 ms | 2423 ms |
| Prompt v4.6 (sampling açık — T=0.55, top_p=0.9, rep_pen=1.15) | 16/16 (%100) | 0 | 2330 ms | 1726 ms | 3050 ms |
| Prompt v4.8 (max_tok=50, top_k=40, rep_pen=1.2 — kısa yanıt) | 16/16 (%100) | 0 | 2195 ms | — | — |
| Prompt v4.9 (sıcak ton + W11 fix + max_tok=65 — 18 turn) | 18/18 (%100) | 0 | 2290 ms | 1871 ms | 3189 ms |
| **Prompt v5.0 (W13 kategori fiyat yasağı + W14 öneri kural — 20 turn)** | **20/20 (%100)** | **0** | — | — | — |

---

## Bilinen LLM Zayıflıkları (Eval Dışı)

| # | Senaryo | Sorun | Kök Neden | Durum |
|---|---------|-------|-----------|-------|
| W1 | Vejetaryen sorusu | Ürün listesi vermiyor | Sistem promptunda tags + kural var | ✅ Düzeltildi |
| W2 | Alerji sorusu | Aşırı savunmacı | Sistem promptunda allergens + kural var | ✅ Düzeltildi |
| W3 | İptal/değişiklik | LLM iptali yok sayıyor | Prompt'ta kural eklendi + OrderTracker cancellation | ✅ Düzeltildi |
| W4 | Adet gösterimi | "iki Izgara Köfte" yerine "Izgara Köfte" | Prompt kuralı + örnek eklendi | ✅ Düzeltildi |
| W5 | Öneri/tavsiye sorusu | Her soruya jenerik kategori özeti veriyordu | "Karşılamada" kuralı çok geneldi | ✅ Düzeltildi (v4.5) |
| W6 | Kalıplaşmış yanıtlar | Her turda kelimesi kelimesine aynı cümle | Greedy decoding (`do_sample=False`/`T=0`) + prompt'ta birebir şablon cümleleri | ✅ Düzeltildi (v4.6 — sampling + hedefli prompt gevşetme) |
| W7 | STT CUDA OOM (PC, 6 GB) | Qwen3-4B + Whisper CUDA peak workspace 5.64 GB'a sığmıyor | LLM ile STT aynı GPU'da çakışıyordu, ısıtma sonrası ~2 GB serbest kalıyordu | ✅ Düzeltildi (v4.6 — Toplam VRAM < 8 GB → STT CPU int8; latency ~130-300ms) |
| W8 | Her turda "hey garson" gerekliydi | Wake word algılandıktan sonra tek bir tur dinleyip wake word'e dönüyordu | Ana döngü tek-tur tasarlı | ✅ Düzeltildi (v4.7 — `CONVO_HOLD_S=10s` pencere; yanıt sonrası sessizlikte wake word'e dön) |
| W9 | Öneri sorularında fiyat söyleniyordu | Müşteri "ne önerirsin" deyince robot fiyat dahil cevap veriyordu | Prompt'ta "isim ve fiyatıyla öner" kuralı vardı | ✅ Düzeltildi (v4.8 — TL kelimesi öneri/karşılama/açıklamada YASAK; sadece fiyat sorusu/sipariş onayı/hesapta geçer) |
| W10 | Yanıt çok uzun (80 token aşımı) ve kalıplaşmış | Karşılamada ürün listesi sayıyordu, "Buyurun, menümüzde..." kalıbı | max_tokens=80 + prompt "1-2 cümle" + örnek cümleler ezberleniyordu | ✅ Düzeltildi (v4.8 — max_tokens=50, "1 cümle/20 kelime" zorunluluğu, karşılama örnekleri kaldırıldı, top_k=40 + rep_pen=1.2) |
| W11 | Hesap sorulmadan toplam söylendi | Kullanıcı "Başka bir şey istemiyorum galiba" deyince bot "Toplam 85 TL" verdi | "Başka istemiyorum" + sipariş kapanışı tetikleyicisi yanlışlıkla hesap döngüsünü tetikliyor | ✅ Düzeltildi (v4.9 — "BU DURUMDA TOPLAM SÖYLEME" + ara toplam ayrı kural olarak eklendi) |
| W12 | Robotik ve soğuk ton | Teknik doğru ama doğal, samimi Türkçe akışı yok; gerçek bir garsonla konuşulduğu hissi vermiyor | Sistem promptu kural listesi gibi yazılmış; kişilik/ton yönergesi eksik | ✅ Düzeltildi (v4.9 — persona paragrafı + "Harika seçim!" örnekleri + 2 cümle/25 kelime + max_tokens 50→65) |
| W13 | Kategori listesi sorusunda fiyat söylüyordu | "Çorba ne var?" sorusuna ürün adlarıyla birlikte "TL" fiyat da veriyordu | Kategori listesi için ayrı kural yoktu; genel fiyat yasağı bu durumu kapsamamıştı | ✅ Düzeltildi (v5.0 — kategori içeriği sorusuna özel kural: yalnızca ürün adı say, TL söyleme) |
| W14 | Öneri sorusunda kategori dışına çıkıyordu | "Tavuk yesem ne yesem?" sorusuna tatlı ve çorba da öneriyordu | Öneri kuralı kategoriyi kısıtlamıyordu | ✅ Düzeltildi (v5.0 — öneri sorusunda kategori belirtildiyse YALNIZCA o kategoriden 1-2 ürün; başka kategori ekleme) |

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
| ✅ Jetson | `openwakeword` kuruldu — wake word modu aktif |

---

## demo_usb.py Yapılandırma Sabitleri

```python
WHISPER_MODEL      = "small"   # PC için (v4.6); Jetson 16 GB'da "medium"a geri dönülebilir
SAMPLE_RATE        = 16_000
CHANNELS           = 1

# VAD kayıt
VAD_AGGRESSIVENESS = 3
VAD_CHUNK_MS       = 30
VAD_SILENCE_S      = 1.5
VAD_PRE_ROLL       = 5
VAD_MAX_S          = 12
VAD_ENERGY_THRESH  = 300
CONVO_HOLD_S       = 10   # v4.7 — yanıttan sonra wake word'süz dinleme penceresi

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
- openwakeword ✅ (pip + model indirildi, numpy<2.0 ile uyumlu)
- ctranslate2 4.7.2 ✅ CUDA SM87 ile kaynaktan derlendi (`-DWITH_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=87 -DOPENMP_RUNTIME=COMP -DWITH_MKL=OFF`)
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
| STT (Whisper small, CPU ARM) | ~1.9 sn (ölçüldü) |
| STT (Whisper small, CUDA) | ~0.85-1.1 sn (ölçüldü) |
| Piper TTS (CPU) | ~0.60 sn |
| **İlk ses çıkana kadar (sıcak, CUDA STT)** | **~2.2-2.7 sn** |

---

## Fine-Tuning Altyapısı (v5.0)

### Dataset
| Parametre | Değer |
|-----------|-------|
| Dosya | `robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl` |
| Kayıt sayısı | 970 (873 train / 97 valid, seed=42) |
| Senaryo türleri | A–H: karşılama, sipariş, iptal, fiyat, öneri, alerji, konu dışı, hesap |
| Format | `messages` (system/user/assistant), chat template uyumlu |

### Eğitim Scripti (`robot_waiter_ai/training/train_wbot_v1.py`)
| Parametre | Değer |
|-----------|-------|
| Base model | Qwen/Qwen3-4B |
| Yöntem | QLoRA — NF4 4-bit + LoRA (r=32, α=64) |
| Hedef modüller | q/k/v/o_proj + gate/up/down_proj (7 modül) |
| Eğitim türü | Completion-only SFT (system+user tokenları -100 maskelenir) |
| Sistem promptu (eğitim) | Kısa (~546 tok) — `--full-prompt` ile orijinal 2092 tok kullanılabilir |
| Optimizer | paged_adamw_8bit (CPU RAM'de) |
| Ortam | Google Colab T4 (16 GB) |

### wbot_v1 Eğitim Sonuçları (3 Haziran 2026)
| Parametre | Değer |
|-----------|-------|
| Komut | `--batch-size 2 --epochs 1 --no-grad-checkpointing` |
| Toplam adım | 55 |
| Süre | ~2.6 saat (Colab T4) |
| Train loss (son) | 0.116 |
| Eval loss | 0.1275 |
| Durum | ✅ Tamamlandı |
| Adapter | `/content/drive/MyDrive/garsonbot_runs/wbot_v1_qlora/adapter` |

### wbot_v1 Eval Sonuçları (scripts/eval_adapter.py)
| Prompt | Skor | Notlar |
|--------|------|--------|
| KISA (~546 tok) | 12/14 (%85) | E02 ve E09 dataset boşluğu |
| TAM (baseline) | 20/20 (%100) | Hedef: kısa promptla da %100 |

**E02 başarısızlığı:** "Ne yiyebilirim?" genel menü sorusu varyantları dataset'te eksik → model öneri sorusu gibi davranıyor.
**E09 başarısızlığı:** "Hamburger var mı?" menü dışı ürün tutarsız → sampling'e bağlı (smoke test'te doğru, eval'da "Anlayamadım").
**E05/diğer:** "Getireyim mi?" yasağı hâlâ ihlal ediliyor (fiyat ve öneri sorularında).

### Sonraki Eğitim: wbot_v2 Planı
- Dataset: 970 → ~1500-2000 kayıt (tüm senaryolar kapsanacak)
- Tüm veriyle sıfırdan eğitim (incremental değil)
- 2 epoch
- Hedef: kısa promptla 14/14 (%100)

---

## Kısa Vadede Yapılacaklar

| # | Görev | Öncelik | Durum |
|---|-------|---------|-------|
| 1 | USB ses adaptörü temin et (~100 TL, USB→3.5mm) | 🔴 Kritik | Donanım yok — tüm ses testleri buna bağlı |
| 2 | ALSA_OUTPUT_DEVICE ayarla (`aplay -l` ile USB adaptörünü bul) | 🔴 Kritik | Adaptör geldikten sonra |
| 3 | Tam uçtan uca demo (wake word→STT→LLM→TTS→hoparlör) | 🔴 Kritik | Adaptöre bağlı |
| 4 | wbot_v2 dataset genişletme (Codex ile senaryo üretimi) | 🟡 Orta | Planlama tamamlandı — üretim aşamasında |
| 5 | wbot_v2 eğitimi (~1500-2000 kayıt, 2 epoch) | 🟡 Orta | Dataset hazır olunca |
| 6 | Adapter → GGUF dönüşümü (Jetson deploy için) | 🟡 Orta | wbot_v2 eval geçtikten sonra |
| 6 | Gürültülü ortamda uçtan uca test (restoran müziği + kalabalık) | 🟡 Orta | Ubuntu PC'de yapılacak (adaptör bekleniyor) |
| 7 | Whisper medium kalite doğrulaması | 🟡 Orta | Jetson 16 GB entegrasyonunda yapılacak |

## Uzun Vade / Ertelenmiş

| # | Görev | Açıklama |
|---|-------|----------|
| 6 | Piper GPU (onnxruntime-gpu) | JetPack R36 aarch64 için pip'te yok — ertelenmiş |
| 7 | systemd servis (otomatik başlatma) | Stabil olduktan sonra |

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
13. **Sampling (v4.6)** — `temperature=0.55, top_p=0.9, repetition_penalty=1.15` her iki backend'de. Greedy decoding kalıplaşmaya yol açıyordu; sampling ile yanıtlar tur-tur farklılaşıyor. Eval %100 korunuyor (sıkı zorunluluk kelimeleri prompt'ta vurgulu).
