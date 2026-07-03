# Garson-bot — Proje Durumu ve Hedeflenen Hal
**Son güncelleme:** 3 Temmuz 2026 | **Sürüm:** 5.12

Yeni bir sohbet başladığında bu dosyayı okuyarak projeyi baştan anlat.
Kod tabanını tekrar incelemene gerek yok — her şey burada.

---

## Bir Sonraki Oturum — Hızlı Özet

**Neredeyiz:** Jetson'da uçtan uca demo çalışıyor (7 Haziran 2026). Whisper medium aktif (1.7s). Geliştirme ortamı Windows 11 WSL2'ye taşındı (Ubuntu dual-boot kaldırıldı). WSL2 kurulumu tamamlandı — PyTorch CUDA, faster-whisper, llama-cpp-python (GPU), Piper TTS model (24 Haziran 2026). Jetson SSH: 192.168.1.65. Yeni eval: 31/32 (%96). wbot_v4_train.jsonl hazır (3605 kayıt, 0 audit ihlali — 3 Temmuz 2026). Tüm yedekler GitHub + Drive'da.

**Sıradaki görevler (öncelik sırasıyla):**

1. **E19 post-processing fix** — "nasıl bir şey?" yanıtı `?` ile bitmiyorsa `demo_usb.py`'de `"Getireyim mi?"` ekle (kod değişikliği, eğitim gerekmez)
2. **Gürültülü ortam testi** — restoran müziği + kalabalık ortamda Jetson'da wake word + STT kalitesi
3. **wbot_v4 eğitimi** — `wbot_v4_train.jsonl` hazır (3605 kayıt, Drive'a yüklendi), notebook hazır (`robot_waiter_ai/training/wbot_v4_colab_training.ipynb`)
4. **wbot_v4 Jetson deploy + eval** → GGUF → Jetson → `eval_gguf.py` (%95+ hedef) + `--v4-targets` (V01-V06)

> 📐 **Senaryo kararları (3 Temmuz 2026):** S19 alerji+öneri → filtrele+uyarı (Seçenek B),
> S12 onay öncesi → her zaman özet+toplam (W11/E24 revizyonu gerekir), S29 küfür ve
> S03 sessizlik politikaları netleşti. Yeni eval hedefleri `eval_gguf.py --v4-targets`
> (V01-V06). Tamamı: [SENARYO_PLANI_FAZ1.md](SENARYO_PLANI_FAZ1.md)

> 🔍 **Senaryo danışması (3 Temmuz 2026) — Codex 5.5, Gemini 2.5 Pro, Claude Fable:**
> Üç model bağımsız olarak S01-S32 listesini değerlendirdi. Konsensüs: W16
> hibrit yaklaşım, S12 koşulsuz özet, ~1100 örnek yeterli. Sonuç: S33-S41
> eklendi, SENARYO_PLANI_FAZ1.md oluşturuldu.

> 📋 **Yeni — toplanti.md (26 Haziran 2026) ses/AI görevleri:** fast-path intent
> yönlendirme, açılış cümlesi standardizasyonu, menü-dışı/düşük-güven girdi guard'ları,
> sipariş-ekran yapısal verisi, AI↔ROS sinyal arayüzü tasarımı. Detay: aşağıdaki
> "Faz 1 / Faz 2 — Ses/AI Görev Planı" bölümü.
>
> 🗺️ **Konsolide yol haritası (toplanti + acil + persona/lisans):** [YOL_HARITASI.md](YOL_HARITASI.md)
> — 3 dalgalı sıralı plan + yeni sohbet başlangıç promptu. İlgili: PERSONA_TON_FIZIBILITE.md,
> TTS_LISANS_ARASTIRMASI.md.

**Sistem durumu (18 Haziran 2026):**
- Jetson: ✅ tam çalışıyor — wake word → Whisper medium CUDA → LLM GGUF → Piper TTS → USB hoparlör
- GGUF: `/home/emk/models/Qwen3-4B-wbot_v3-Q4_K_M.gguf` (2.38 GB) — Drive'da da yedek var
- Eval: `scripts/eval_gguf.py` — 32 senaryo, %96 (31/32), çok-turlu destekli
- Geliştirme: Windows 11 WSL2 — kurulum kılavuzu: `WSL2_KURULUM.md`

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
| Windows 11 WSL2 (geliştirme) | RTX 4050 | qwen3_backend.py (transformers, 4-bit NF4) | ✅ Çalışıyor — Ubuntu dual-boot kaldırıldı (18 Haziran 2026) |
| Jetson Orin NX 16GB | Orin GPU (SM87) | llama_cpp_backend.py (GGUF, llama-cpp-python) | ✅ Tam çalışıyor (7 Haziran 2026) |

---

## Klasör Yapısı (Aktif Dosyalar)

```
Garson-bot/
├── PROJE_DURUMU.md               ✅ Bu dosya — yeni sohbette ilk oku
├── METODOLOJI.md                 ✅ Mimari ve teknik kararlar
├── scripts/
│   ├── demo_usb.py               ✅ Ana demo — wake word → VAD → STT → LLM → Piper TTS
│   ├── eval_llm.py               ✅ LLM kalite + performans eval (prompt bazlı, 20 turn)
│   ├── eval_adapter.py           ✅ Fine-tune adapter eval (14 formal + 7 smoke; --full-prompt desteği)
│   ├── eval_gguf.py              ✅ Jetson GGUF eval — 32 senaryo, çok-turlu (seeded history) destekli
│   ├── audit_dataset.py          ✅ Dataset ihlal denetimi — 10 kural (8 içerik + 2 sistem promptu; 3 Temmuz 2026)
│   ├── gen_karsilama.py          ✅ wbot_v3 dataset üretim — karşılama (200 kayıt)
│   ├── gen_siparis_baska.py      ✅ wbot_v3 dataset üretim — sipariş+başka (150 kayıt)
│   ├── gen_hesap.py              ✅ wbot_v3 dataset üretim — hesap varyasyonları (100 kayıt, kanonik sistem promptu — 3 Temmuz 2026 fix)
│   ├── gen_cotturlu.py           ✅ wbot_v3 dataset üretim — çok turlu (150 kayıt, kanonik sistem promptu — 3 Temmuz 2026 fix)
│   ├── gen_iptal.py              ✅ wbot_v3 dataset üretim — iptal/değişiklik (100 kayıt, kanonik sistem promptu + menü adı fix — 3 Temmuz 2026)
│   ├── gen_oneri.py              ✅ wbot_v3 dataset üretim — öneri+TL yasağı (105 kayıt, kanonik sistem promptu + menü adı fix — 3 Temmuz 2026)
│   ├── compare_models.py         ✅ Model karşılaştırma scripti (4B vs 1.7B)
│   ├── train_wakeword.py         ✅ openWakeWord eğitim (MMS-TTS + gürültü)
│   └── test_wakeword_usb.py      ✅ USB mikrofon ile gerçek zamanlı wake word testi
└── robot_waiter_ai/
    ├── inference/
    │   ├── qwen3_backend.py      ✅ PC için — Qwen3-4B transformers 4-bit NF4
    │   │                            _build_system_prompt() export'u var (eval_adapter.py kullanır)
    │   └── llama_cpp_backend.py  ✅ Jetson için — Qwen3-4B GGUF Q4_K_M + CUDA
    ├── speech/
    │   ├── stt.py                ✅ faster-whisper STT wrapper (model: small)
    │   ├── tts.py                ✅ edge-tts + PiperTTS (Piper birincil, edge-tts fallback)
    │   └── mic.py                ✅ ReSpeaker Mic Array wrapper
    ├── data/
    │   ├── menu.yaml             ✅ Menü tanımları (name, category, price, description, aliases)
    │   └── restaurant_info.yaml
    ├── models/
    │   ├── hey_garson.onnx       ✅ Wake word modeli (openWakeWord, 789 KB)
    │   └── tr_TR-fahrettin-medium.onnx  ✅ Piper TTS Türkçe sesi
    ├── training/
    │   ├── train_wbot_v2.py      ✅ QLoRA fine-tune scripti (wbot_v3 destekli, varsayılan dataset: wbot_v3_train.jsonl)
    │   ├── requirements_train.txt ✅ Colab bağımlılıkları (transformers>=4.43.0 zorunlu — Qwen3 chat template)
    │   └── artifacts/
    │       └── wbot_v3_qlora/
    │           └── adapter/      ⚠️ lokal — git'te değil (264 MB); Drive: garsonbot_runs/wbot_v3/adapter/
    └── datasets/
        └── processed/
            ├── wbot_v3_train.jsonl          ✅ 3000 kayıt, 0 audit ihlali (10 kural — 3 Temmuz 2026 itibariyle)
            ├── wbot_v3_train_backup.jsonl   ⚠️ Sistem promptu fix öncesi yedek (diskte duruyor, git'te değil)
            └── wbot_finetune_v1_violations.jsonl  ✅ 21 ihlalli kayıt (wbot_v2'den ayrıldı)
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
    │  Hesap istenince: non-streaming generate_reply + regex override
    │  (LLM çıktısındaki toplam order_tracker.total ile değiştirilir)
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
| Model | Qwen3-4B-wbot_v3-Q4_K_M.gguf |
| Konum | /home/emk/models/Qwen3-4B-wbot_v3-Q4_K_M.gguf |
| Backend | llama-cpp-python 0.3.23 (CUDA SM87) |
| GPU offload | 37/37 katman (tam GPU) |
| VRAM | ~2.38 GB / 15.6 GB |
| Hız | ~12-15 tok/s |
| Thinking | Kapalı — _format_prompt() `<think>\n\n</think>` prefix ekler |
| n_ctx | **4096** (sistem prompt ~2100 tok olduğundan 1536 yetersizdi) |
| max_tokens | **65** |
| Decoding | temperature=0.55, top_p=0.9, top_k=40, repeat_penalty=1.2 |
| _MAX_HIST_CHARS | **4000** — aşılınca en eski user+assistant turu silinir |

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
| Sistem prompt (sabit metin) | ~2100 |
| n_ctx | 4096 |
| max_tokens | 65 |
| Konuşmaya kalan | ~1931 (~10-12 tur) |

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
| Model (PC) | **small** (host VRAM 5.64 GB; Qwen3-4B + Whisper medium birlikte OOM oluyordu) |
| Model (Jetson) | **medium** ✅ — 16GB CUDA, 1.7s latency (7 Haziran 2026 doğrulandı) |
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
| **GGUF eval — eval_gguf.py (32 senaryo, Jetson, 22 Haziran 2026)** | **31/32 (%96)** | **1** | — | — | — |

*GGUF eval başarısızları: E19 (açıklama sonrası soru yok — gerçek model hatası). E21 düzeltildi — artık geçiyor.*

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
| W15 | Ürün açıklaması sonrası soru yok | "Kremalı mantar çorbası nasıl?" → açıklama yapıyor ama "Getireyim mi?" demiyor | wbot_v3 dataseti açıklama+soru örneklerini yeterince içermiyor | ⏳ wbot_v4 |
| W16 | Alerji yanıtı anlamsız | "Süt alerjim var, ne yiyebilirim?" → "Süt ürünü içermeyen menüümüz var mı?" (model kendine soruyor) | Yetersiz alerji+öneri kombinasyon örneği | ⏳ wbot_v4 |

> 📌 **S12 kararı — Sipariş Özeti (onaylandı, 3 Temmuz 2026):** Koşulsuz
> toplu özet. Ürün sayısından bağımsız, onay öncesi her zaman:
> "Siparişiniz: [ürünler]. Toplam [X] TL. Onaylıyor musunuz?"
> Afiyet olsun cümlesi toplamsız kalır (W11 kuralı burada geçerli).
> E24 eval'i wbot_v4'te bu akışa göre revize edilecek.

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
WHISPER_MODEL      = "medium"  # Jetson — 1.7s CUDA (7 Haziran 2026); PC'de "small" kullan (VRAM)
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
| STT (Whisper medium, CUDA) | ~1.7 sn (7 Haziran 2026 ölçüldü) |
| Piper TTS (CPU) | ~0.60 sn |
| **İlk ses çıkana kadar (sıcak, CUDA STT)** | **~2.2-2.7 sn** |

---

## Fine-Tuning Altyapısı (v5.3)

### Eğitim Scripti (`robot_waiter_ai/training/train_wbot_v2.py`)
| Parametre | Değer |
|-----------|-------|
| Base model | Qwen/Qwen3-4B |
| Yöntem | QLoRA — NF4 4-bit + LoRA (r=32, α=64) |
| Hedef modüller | q/k/v/o_proj + gate/up/down_proj (7 modül) |
| Eğitim türü | Completion-only SFT (system+user tokenları -100 maskelenir) |
| Sistem promptu (eğitim) | Kısa (~250 tok) — `--full-prompt` ile orijinal 2092 tok kullanılabilir |
| Optimizer | paged_adamw_8bit (CPU RAM'de) |
| Ortam | Google Colab A100-SXM4-40GB |

---

### wbot_v1 Eğitim Sonuçları (3 Haziran 2026)
| Parametre | Değer |
|-----------|-------|
| Dataset | `wbot_finetune_v1.jsonl` — 970 kayıt |
| Komut | `--batch-size 2 --epochs 1 --no-grad-checkpointing` |
| Toplam adım | 55 |
| Süre | ~2.6 saat (Colab T4) |
| Train loss (son) | 0.116 |
| Eval loss | 0.1275 |
| Formal eval (kısa prompt) | 12/14 (%85) |
| Formal eval (tam prompt) | 20/20 (%100) |
| Adapter | `Drive: garsonbot_runs/wbot_v1_qlora/adapter` |

---

### wbot_v2 Eğitim Sonuçları (3 Haziran 2026) ✅
| Parametre | Değer |
|-----------|-------|
| Dataset | `wbot_finetune_v1.jsonl` — 2216 kayıt (1994 train / 222 valid) |
| Komut | `--epochs 2 --run-eval` |
| Toplam adım | 500 (250/epoch × 2 epoch, early stop tetiklenmedi) |
| Süre | ~1.5-2 saat (Colab A100-SXM4-40GB) |
| Formal eval (14 senaryo) | 12/14 (%85) |
| Kapsamlı eval (48 senaryo) | 34/48 (%70) — düzeltilmiş: 38/45 (%84) |
| Adapter | `Drive: garsonbot_runs/wbot_v2/adapter` (252 MB) |
| Checkpoint | checkpoint-400, checkpoint-450, checkpoint-500 |

**wbot_v2 Formal Eval Başarısızlıkları:**
- **E01:** Karşılama yanıtı 4 kategori içermiyor (dataset boşluğu)
- **E08:** Hesap yanıtında "Toplam X TL." formatı yok

**wbot_v2 Kapsamlı Eval Başarısızlıkları (48 senaryo):**
- A01-A04: Karşılama/genel menü — 4 kategori kuralı öğrenilmemiş
- D01-D03, E02: Sipariş onayında "başka" yerine "Ekleyeceğimiz" kullanılıyor
- F03: Tam sipariş iptali senaryosu eksik
- H01-H03: Hesap bağlamı yok (sistem tasarımı — OrderTracker enjeksiyonu gereken)
- L03: Fiyat yasağı ihlali ("en ucuz" sorusunda TL söylüyor)
- G02, G04: "Getireyim mi?" gizli ihlali (PASS geçti ama kural çiğneniyor)

---

### wbot_v2 Dataset Denetimi (scripts/audit_dataset.py)

`python scripts/audit_dataset.py` ile 2216 kayıt otomatik denetlendi.

**Audit scripti revision geçmişi (3 Haziran 2026):**

| Kural | Ham Sayı | Gerçek İhlal | Yanlış Pozitif Kaynağı |
|-------|----------|--------------|------------------------|
| TL yanlış bağlam | 618 | **0** ✅ | Bütçe/takas/adet bağlamları hariç tutulmadı |
| Sipariş onayında "başka" | 353 | **7** ✅ | `_is_specific_order_turn` dar tanım + eşdeğerler eklendi |
| Hesap yanıtında "toplam" | 78 | **0** ✅ | Deferral/redirect/hesaplı false match |
| Karşılamada 4 kategori | 97 | **13** ✅ | Diyet/bütçe/veda/acele sorguları hariç tutulmadı |
| "Getireyim mi?" | 4 | **4** | Gerçek ihlal |

**Düzeltme sonrası final audit:**

| Kural | İhlal |
|-------|-------|
| Karşılama-4kategori | 13 |
| Sipariş-başka | 7 |
| Getireyim-mi yasağı | 4 |
| TL-yanlış bağlam | 0 |
| Yasak ifade | 0 |
| Markdown | 0 |
| Sen formu | 0 |
| Hesap-toplam | 0 |
| **İhlalli kayıt** | **21 / 2216 (1%)** |
| **Temiz kayıt** | **2195 / 2216 (99%)** |

İhlalli 21 kayıt: `wbot_finetune_v1_violations.jsonl` olarak ayrıldı.

---

### wbot_v3 Dataset Üretimi (4 Haziran 2026) ✅

**Üretim scriptleri** (`scripts/`):

| Script | Kategori | Kayıt | Audit |
|--------|---------|-------|-------|
| gen_karsilama.py | Karşılama 4-kategori | 200 | 0 ihlal |
| gen_siparis_baska.py | Sipariş-başka | 150 | 0 ihlal |
| gen_hesap.py | Hesap varyasyonları | 100 | 0 ihlal |
| gen_cotturlu.py | Çok turlu | 150 | 0 ihlal |
| gen_iptal.py | Sipariş iptali/değişiklik | 100 | 0 ihlal |
| gen_oneri.py | Öneri + TL yasağı | 105 | 0 ihlal |

Birleştirme: `python -c "..."` ile 2195 temiz base + 805 yeni → shuffle → `wbot_v3_train.jsonl`

---

### Sonraki Eğitim: wbot_v3 Planı

**Strateji:** İhlalli 21 kaydı çıkar → **2195 temiz base** + ~805 yeni kural-uyumlu örnek = 3000 kayıt.

> Audit script düzeltmesi sayesinde base **1333 → 2195** oldu (+862 kayıt kurtarıldı).
> Artık 1667 değil yalnızca ~805 yeni örnek üretmek yeterli.

| # | Kategori | Dosya | Adet | Durum |
|---|----------|-------|------|-------|
| 1 | Karşılama — 4 kategori zorunlu | wbot_v3_karsilama.jsonl | 200 | ✅ |
| 2 | Sipariş onayı — "başka" pekiştirme | wbot_v3_siparis_baska.jsonl | 150 | ✅ |
| 3 | Hesap varyasyonları (toplam formatı) | wbot_v3_hesap.jsonl | 100 | ✅ |
| 4 | Çok turlu konuşmalar | wbot_v3_cotturlu.jsonl | 150 | ✅ |
| 5 | Sipariş iptali / değişiklik | wbot_v3_iptal.jsonl | 100 | ✅ |
| 6 | Öneri + kategori sorgusu (TL yasağı) | wbot_v3_oneri.jsonl | 105 | ✅ |
| **TOPLAM** | | | **805** | **✅** |

**Final dataset:** `wbot_v3_train.jsonl` — 3000 kayıt, **0 audit ihlali** (4 Haziran 2026)

```
2195 temiz base + 805 yeni = 3000 kayıt → wbot_v3_train.jsonl
Konum: robot_waiter_ai/datasets/processed/wbot_v3_train.jsonl
Hedef: 48 senaryoda %95+ PASS
```

**Üretim yöntemi:** Her kategori için gen_*.py scripti yazıldı, `audit_dataset.py` ile doğrulandı. Tüm 805 örnek ilk çalıştırmada temiz.
**Eğitim parametreleri:** Sıfırdan eğitim (incremental değil), 2 epoch, Colab A100.

---

### wbot_v3 Eğitim Sonuçları (4 Haziran 2026) ✅

| Parametre | Değer |
|-----------|-------|
| Dataset | `wbot_v3_train.jsonl` — 3000 kayıt (2195 temiz base + 805 yeni) |
| Komut | `--epochs 2 --run-eval` |
| Toplam adım | 676 (ceil(2700/8) × 2 epoch) |
| Süre | ~1.5-2 saat (Colab A100-SXM4-40GB) |
| Train loss (son) | 0.2304 |
| Eval loss | 0.1993 |
| Formal eval (kısa prompt) | 11/14 (%78) — E03, E08, E11 başarısız |
| Formal eval (tam prompt) | 13/14 (%92) — yalnızca E08 (eval tasarım sorunu, model doğru) |
| Adapter (Drive) | `garsonbot_runs/wbot_v3/adapter` — 252 MB safetensors |
| Adapter (lokal) | `robot_waiter_ai/training/artifacts/wbot_v3_qlora/adapter/` |
| Checkpoint | checkpoint-600, checkpoint-650, checkpoint-676 |

**wbot_v3 Formal Eval Başarısızlıkları:**
- **E08 (her iki prompt):** "Toplam" kelimesi yok — eval tasarım sorunu. Gerçek sistemde OrderTracker `[Gerçek toplam: X TL]` enjekte eder; eval bunu simüle etmiyor. Deployment'ta model doğru çalışıyor.
- **E03, E11 (yalnızca kısa prompt):** Kısa promptta kapsam eksik. Tam prompt ile ikisi de geçiyor (%100 çözüldü).

---

### wbot_v3 Sistem Promptu Tutarsızlığı Fix (3 Temmuz 2026) ✅

**Sorun:** `wbot_v3_train.jsonl`'deki 3000 kayıttan 455'i (`gen_hesap.py`,
`gen_cotturlu.py`, `gen_iptal.py`, `gen_oneri.py` çıktıları) persona/kural
içermeyen kısa hardcode sistem promptlarıyla (284 veya 60 karakter)
üretilmişti — METODOLOJI.md'nin "tüm kayıtlarda aynı uzun sistem promptu"
kuralına aykırı. `audit_dataset.py`'nin o zamanki 8 kuralı bunu hiç
yakalamıyordu çünkü yalnızca `assistant` mesajlarını denetliyordu.

**Düzeltme:**
- `scripts/audit_dataset.py`'ye 2 yeni kural eklendi:
  `check_system_prompt_length` (sistem promptu < 1000 karakter → ihlal) ve
  `check_system_prompt_short_variant` (1000-4000 karakter → ihlal SAYILMAZ,
  yalnızca bilgi amaçlı ayrı raporlanır).
- 4 script (`gen_hesap.py`, `gen_cotturlu.py`, `gen_iptal.py`, `gen_oneri.py`)
  hardcode sistem promptunu kaldırıp `gen_karsilama.py`/`gen_siparis_baska.py`
  ile aynı yöntemle (`wbot_finetune_v1.jsonl`'in ilk kaydından oku) kanonik
  5460 karakterlik prompta geçti.
- Ek olarak `gen_iptal.py`/`gen_oneri.py`'de menü adı uyuşmazlığı düzeltildi:
  "Izgara Tavuk Salatası" → "Izgara Tavuk Salata", "Ayran" → "Yayık Ayran"
  (kanonik sistem promptunun menü bölümüyle eşleşecek şekilde).
- 4 script yeniden çalıştırılıp tekil çıktı dosyaları yeniden üretildi,
  `wbot_v3_train.jsonl` 2195 temiz base + düzeltilmiş 805 yeni kayıtla
  yeniden birleştirildi (kayıt sayısı 3000 korundu). Önceki hâli
  `wbot_v3_train_backup.jsonl` olarak yedeklendi.

**Sonuç (audit_dataset.py, öncesi → sonrası):**

| Kural | Öncesi | Sonrası |
|---|---|---|
| Sistem-promptu-uzunluk | 455 | **0** |
| Mevcut 8 içerik kuralı | 0 | 0 (değişmedi) |
| Toplam kayıt | 3000 | 3000 (değişmedi) |

**Sistem promptu dağılımı (wbot_v3_train.jsonl, sonrası):**

| Uzunluk | Kayıt | Durum |
|---|---|---|
| 5460 karakter (tam persona + kurallar + menü) | 1769 | ✅ Sağlam |
| 1773 karakter (kısa ama kurallı, wbot_v2 §1-12 varyantı) | 1231 | ⚠️ Bilinen teknik borç (aşağıya bkz.) |
| 284 / 60 karakter (bozuk) | 0 | ✅ Düzeltildi |

#### Bilinen Teknik Borç — Kısa Varyant Sistem Promptu (Düşük Öncelik)

`wbot_v3_train.jsonl` içinde 1231 kayıt (wbot_v2 §1-12 dönemi) 1773
karakterlik kısa bir sistem promptuyla üretilmiş. Bu kayıtlar kural içeriyor
(persona/format kuralları var) — bu yüzden `audit_dataset.py` bunları ihlal
saymıyor, yalnızca bilgi amaçlı ayrı raporluyor. Eval sonuçlarını bugüne kadar
bozmadı (32 senaryo %96 baz alındı). Ancak inference'ta kullanılan 5460
karakterlik tam promptla eğitim zamanı tutarsızlığı hâlâ mevcut — wbot_v4 veya
sonraki bir dataset döngüsünde bu 1231 kayıt da kanonik prompta geçirilerek
yeniden üretilebilir.

---

### Sonraki Eğitim: wbot_v4 Planı

**Önkoşul:** ✅ Jetson deploy tamamlandı. 32-senaryo eval (%93) yapıldı. Gerçek boşluklar tespit edildi.

> Başlıca eksikler: W15 (açıklama+soru), W16 (alerji+öneri), hallüsinasyon (E34). Gürültülü ortam testinden ek boşluklar çıkabilir.

**Tahmini ihtiyaç:** ~1100 yeni örnek (wbot_v3 3000 base üzerine)

| # | Kategori | Tahmini Adet | Gerekçe |
|---|----------|-------------|---------|
| 1 | Ürün açıklaması + "Getireyim mi?" soru | 150 | W15 — E19 başarısızlığının kök nedeni |
| 2 | Alerji + öneri kombinasyonları | 150 | W16 — "süt alerjim var, ne yiyebilirim?" → somut yanıt |
| 3 | Anti-hallüsinasyon (menüde olmayan detay) | 100 | E34 — "elma dilim patates" gibi uydurma açıklamalar |
| 4 | Karmaşık sipariş (3+ ürün, değiştir+ekle+hesap) | 150 | Gerçek restoran davranışı |
| 5 | Uzun çok turlu sohbet (6+ tur) | 100 | Bağlam koruması, konu değişikliği |
| 6 | Gürültülü ortam testinden çıkan edge case'ler | ~100 | Gerçek test sonrası eklenecek |
| 7 | Faz 1 danışma sonucu yeni senaryolar (S33-S41) | ~115 | Codex/Gemini/Claude konsensüsü — modifikasyon, alerjen çakışması, küfür, stok-yok, eskalasyon (bkz. SENARYO_PLANI_FAZ1.md) |
| **TOPLAM** | | **~1100** | |

**wbot_v4 hedef dataset:** ~4100 kayıt (3000 base + 1100 yeni)
**Başarı hedefi:** 48 senaryo %95+ PASS + gerçek restoran ortamında doğal sohbet kalitesi

---

### wbot_v4 Dataset Üretimi (3 Temmuz 2026) ✅

**A Paketi (490 kayıt, gen_*.py ile üretildi):**

| Script | Çıktı | Kayıt | Senaryo |
|--------|-------|-------|---------|
| gen_aciklama.py     | wbot_v4_aciklama.jsonl     | 150 | E19/W15 fix — açıklama + "Getireyim mi?" |
| gen_karmasik.py     | wbot_v4_karmasik.jsonl     | 150 | S12 koşulsuz özet — karmaşık/adetli sipariş |
| gen_cokturlu_v4.py  | wbot_v4_cokturlu.jsonl     | 100 | Uzun çok turlu konuşma |
| gen_kisa_onay.py    | wbot_v4_kisa_onay.jsonl    |  60 | S13 kısa onay senaryosu |
| gen_duzeltme.py     | wbot_v4_duzeltme.jsonl     |  30 | S26 yanlış anlama → düzeltme |

**B Paketi (115 kayıt, gen_*.py ile üretildi):**

| Script | Çıktı | Kayıt | Senaryo |
|--------|-------|-------|---------|
| gen_belirsiz.py        | wbot_v4_belirsiz.jsonl        | 20 | S25/S27 — belirsiz/eksik girdi |
| gen_kotu_niyet.py      | wbot_v4_kotu_niyet.jsonl      | 15 | S29/S30/S32 — küfür/kandırma/görev dışı |
| gen_modifikasyon.py    | wbot_v4_modifikasyon.jsonl    | 20 | S33/V01 — sipariş anı modifikasyon |
| gen_alerjen_cakisma.py | wbot_v4_alerjen_cakisma.jsonl | 15 | S35/V03 — sipariş+alerjen çakışması |
| gen_pratik_soru.py     | wbot_v4_pratik_soru.jsonl     | 10 | S37/V05 — tuvalet/wifi vb. |
| gen_alerji_oneri.py    | wbot_v4_alerji_oneri.jsonl    | 20 | S38/V06 — W16, S19-B kanonik kalıp |
| gen_siparis_durumu.py  | wbot_v4_siparis_durumu.jsonl  | 15 | S40 — "ne zaman gelir" |

**Birleştirme:** `scripts/rebuild_wbot_v4_train.py` — `wbot_v3_train.jsonl` (3000 temiz base) + A paketi (490) + B paketi (115) = 3605 kayıt, `random.Random(2027).shuffle()`.

**`wbot_v4_train.jsonl` — 3605 kayıt, audit 0 ihlal (10 kural temiz):**

| Bileşen | Kayıt |
|---|---|
| wbot_v3_train.jsonl (temiz base) | 3000 |
| A paketi | 490 |
| B paketi | 115 |
| **Toplam** | **3605** |

**Sistem promptu dağılımı:**

| Uzunluk | Kayıt | Not |
|---|---|---|
| 5460 karakter (tam kanonik) | 2374 | base'deki 1769 + A/B paketindeki tüm 605 yeni kayıt |
| 1773 karakter (kısa varyant) | 1231 | bilinen teknik borç, base'den değişmeden geldi — ihlal sayılmıyor |

**Yedek:** `wbot_v4_base_backup.jsonl` (`wbot_v3_train.jsonl` birebir kopyası, birleştirmeden önce alındı)

> **Not — C paketi kapsam dışı:** ~495 kayıt (Gemini/Claude API ile üretilecek) bu turda üretilmedi, farklı bir ortamda ayrıca ele alınacak. wbot_v4 eval sonuçlarına göre wbot_v5 için değerlendirilecek.

---

## Kısa Vadede Yapılacaklar

| # | Görev | Öncelik | Durum |
|---|-------|---------|-------|
| 1 | USB ses adaptörü temin et | 🔴 Kritik | ✅ Tamamlandı — card 3 USB Audio Device |
| 2 | Jetson uçtan uca demo | 🔴 Kritik | ✅ Tamamlandı — 7 Haziran 2026 |
| 3 | wbot_v3 GGUF Jetson deploy | 🔴 Kritik | ✅ Tamamlandı — /home/emk/models/ |
| 4 | 3 bug fix (hesap toplam, karşılama soru, kapanış çeşitliliği) | 🔴 Kritik | ✅ Tamamlandı — commit 933a362 |
| 5 | 32-senaryo GGUF eval | 🟡 Orta | ✅ Tamamlandı — 31/32 (%96), eval_gguf.py (22 Haziran 2026) |
| 6 | Whisper medium testi (Jetson'da) | 🟡 Orta | ✅ Tamamlandı — 1.7s CUDA, demo_usb.py güncellendi |
| 7 | E19 post-processing fix — açıklama yanıtı "?" ile bitmiyorsa "Getireyim mi?" ekle | 🟡 Orta | ⏳ Bekliyor |
| 8 | Gürültülü ortam testi (restoran müziği + kalabalık) | 🟡 Orta | ⏳ Bekliyor |
| 9 | wbot_v4 dataset üretimi — A paketi (490) + B paketi (115) = 605 yeni kayıt | 🟢 Düşük | ✅ Tamamlandı — 3 Temmuz 2026 |
| 10 | wbot_v4 eğitimi — Dataset: `wbot_v4_train.jsonl` (3605 kayıt, Drive'a yüklendi), Notebook: `wbot_v4_colab_training.ipynb`, Script: `train_wbot_v2.py`, Çıktı: `Qwen3-4B-wbot_v4-Q4_K_M.gguf` (Colab A100, 3 epoch) | 🟡 Orta | ⏳ Bekliyor |
| 11 | Sistem promptu tutarsızlığı fix (audit_dataset.py 2 yeni kural + 4 gen script + 455 kayıt) | 🔴 Kritik | ✅ Tamamlandı — 3 Temmuz 2026 |
| 12 | Loglama sistemi — demo_usb.py'e oturum loglama (ses + metin + sipariş geçmişi); amaç: hukuki koruma (müşteri itirazları) + gelecekteki yeniden eğitim verisi; kapsam: session JSON (masa no, timestamp, konuşma, sipariş snapshot) + WAV kaydı | 🟡 Orta | ⏳ Tasarım aşamasında, henüz kod yok |
| 13 | Senaryo planlaması tamamlandı (S01-S41, SENARYO_PLANI_FAZ1.md) | 🔴 Kritik | ✅ Tamamlandı — 3 Temmuz 2026 |
| 14 | eval_gguf.py — V01-V06 hedef senaryoları eklendi (--v4-targets) | 🔴 Kritik | ✅ Tamamlandı — 3 Temmuz 2026 |
| 15 | W16 ve S12 davranış kararları verildi | 🟡 Orta | ✅ Tamamlandı — 3 Temmuz 2026 |
| 16 | E24 eval revizyonu (S12 koşulsuz özet akışına göre) | 🟡 Orta | ⏳ Bekliyor |
| 17 | Eval: V01-V06 hedeflerini ana listeye taşı (wbot_v4 sonrası) | 🟢 Düşük | ⏳ Bekliyor |
| 18 | Jetson deploy + eval (wbot_v4 sonrası) — `eval_gguf.py` hedef 32/32, `--v4-targets` ile V01-V06 ölçümü | 🟢 Düşük | ⏳ Bekliyor |
| 19 | wbot_v4_train.jsonl birleştirme (3605 kayıt, 0 ihlal, seed=2027) | 🔴 Kritik | ✅ Tamamlandı — 3 Temmuz 2026 |

---

## Faz 1 / Faz 2 — Ses/AI Görev Planı (toplanti.md, 26 Haziran 2026)

26 Haziran 2026 ekip toplantısı kararlarının **yalnızca ses/AI tarafını** etkileyen
maddeleri, mevcut kod tabanına eşlenerek aşağıya çıkarıldı. ROS/donanım maddeleri
(QR/2D masa haritalama, depth kamera, hareketli engel kaçınma, ROS 2 Humble geçişi,
anten/USB 3.0 kamera) **kapsam dışıdır**. Her görev bir toplanti.md maddesine bağlıdır.

> Faz tanımı: **Faz 1** = tek kişi, tek dil (Türkçe), wake word + QR çağırma, temel
> sesli sipariş. **Faz 2** = çoklu kişi/masa ayrımı, çoklu dil, 360° ses kaynağı,
> gelişmiş senaryolar.

### FAZ 1

| Görev | Tip | Dosya(lar) | Kaynak | Bağımlılık |
|-------|-----|-----------|--------|-----------|
| **Yanıt hızı segmentasyonu (intent fast-path)** — rutin intent'lerde (selam, net tek-ürün onay, kapanış, hesap) template/kısa yol; açık uçlu sorular LLM'e. Hesap zaten fast-path benzeri, desen genelleştirilir. | YENİ | `demo_usb.py` (yönlendirme), ops. `llama_cpp_backend.py` | madde 2 | Yok — `detect_order` template onayda da çağrılmalı |
| **Açılış cümlesi standardizasyonu** — `GREETING` sabitini tek `_greet()` giriş noktasına topla; wake-word ve (ileride) ROS "geldim" aynı yeri çağırsın. | DEĞİŞTİR | `demo_usb.py` (`GREETING`, satır ~687, 743-749) | madde 2+3 | ROS "geldim" sinyali (şimdilik yalnız wake-word) |
| **Kötü niyetli / anlamsız / menü-dışı girdi davranışı** — (1) menü-dışı sipariş guard (`_ORDER_VERBS` var + `_match_items` boş → "bilgim yok"), (2) düşük-güven guard (≤2 kelime / düşük `language_probability` → "tekrar eder misiniz?"), (3) eval kategorisi. acil.md reçeteleri. | DEĞİŞTİR | `demo_usb.py` (guard'lar), `eval_gguf.py` (senaryo), `*_backend.py` (prompt) | madde 2 + 10.1 | Yok; wbot_v4 pekiştirir |
| **Sipariş-ekran senkronizasyonu** — OrderTracker'a yapısal sipariş listesi (`[{name, category, qty, price}]`) + JSON/event emisyonu; `_total` bundan türetilir (geriye uyumlu). Ekran render ROS/UI tarafında. | DEĞİŞTİR | `demo_usb.py` (`OrderTracker`) | madde 5 | Ekran render = ROS/UI iş paketi (kapsam dışı) |
| **AI ↔ ROS sinyal arayüzü (tasarım/stub)** — `arrived` (→ `_greet()`), `moving`/`stopped` (→ dinleme + wake word duraklat). Mevcut `tts_active`/`conversation_active` deseni; yeni `robot_moving` Event. En az karmaşık transport (flag dosyası / yerel socket). | YENİ | `demo_usb.py`, ops. `robot_waiter_ai/integration/ros_signals.py` | madde 3 + 6 | ⚠️ **ROS'tan beklenir** — mesaj formatı/transport ortak karar; sinyali ROS üretir |
| **Persona/ses tonu örnek onayı** — *kod değil*. Metin/persona W12 (v4.9) ile çözüldü; kalan iş 2-3 örnek TTS sesi üretip ekibe onaylatma. | İNSAN | (ses üretimi) | madde 2 | Ekip onayı |

### FAZ 2

| Görev | Tip | Durum | Kaynak |
|-------|-----|-------|--------|
| **Çoklu dil desteği** — model switch / bekletme mesajı / çeviri-yönlendirme; hiçbiri seçilmedi. Şimdilik kod yok, METODOLOJI.md notu. | YENİ | Karar bekliyor | madde 4 + 8 |
| **Restoran tipine göre ses/persona paketleri** — kebapçı ↔ a la carte farklı ton; `_SYSTEM_TEMPLATE` + TTS sesi konfig parametresi. Tasarım notu. | YENİ | Faz 2 | madde 1 + 2 |
| **Sürekli öğrenme / saha logu toplama** — log → sunucuda periyodik güncelleme (internet bağlı). Kod yok, METODOLOJI.md vizyon notu. | YENİ | Faz 2+ | madde 7 |
| **360° ses kaynağı + masa ayrımı + çoklu kişi** — mic array donanımı gerektirir (büyük ölçüde ROS/donanım); AI tarafı ileride çoklu-konuşmacı diyalog mantığı. | NOT | Faz 2 | madde 3 + 8 |

### acil.md Kaynaklı — Toplantı Dışı Acil Düzeltmeler (ayrı izlenir)

> toplanti.md maddesi değil; saf altyapı/kalite hotfix'leri. (Kötü-niyetli-girdi
> guard'ları yukarıdaki Faz 1 maddesine taşındı.)

- **🔴 P0 ALSA çıkış oto-tespiti** — `_find_output_device()` ile `demo_usb.py:82`
  sabit `plughw:0,0` yerine isimle oto-tespit; replug/boot'a dayanıklı.
- **🟠 P1 STT kalite/gecikme** — faster-whisper `beam_size=5`, `temperature=0.0`,
  `condition_on_previous_text=False` + erken-eleme eşikleri (`stt.py`);
  `STT_INITIAL_PROMPT` zenginleştirme; `VAD_SILENCE_S` 1.5→1.8-2.0.
- **🟢 P3 log gürültüsü** — torch CUDA / onnxruntime uyarıları (zararsız, opsiyonel).

## GGUF Dönüşümü — Colab Hücreleri

wbot_v3 adapter'ı Jetson'a deploy edebilmek için base model ile merge edilip GGUF'a dönüştürülmesi gerekiyor.

```python
# Hücre 1 — Kurulum
!pip install -q transformers peft accelerate
!apt-get install -q -y build-essential cmake
!git clone https://github.com/ggml-org/llama.cpp /content/llama.cpp
!cd /content/llama.cpp && cmake -B build -DGGML_CUDA=ON && cmake --build build --config Release -j4

# Hücre 2 — Drive mount + adapter yükle
from google.colab import drive
drive.mount('/content/drive')
ADAPTER_DIR = "/content/drive/MyDrive/garsonbot_runs/wbot_v3/adapter"
MERGED_DIR  = "/content/wbot_v3_merged"
GGUF_PATH   = "/content/drive/MyDrive/garsonbot_runs/wbot_v3/Qwen3-4B-wbot_v3-Q4_K_M.gguf"

# Hücre 3 — Merge (adapter + base model)
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

print("Base model yükleniyor...")
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen3-4B", torch_dtype=torch.float16, device_map="cpu"
)
model = PeftModel.from_pretrained(model, ADAPTER_DIR)
print("Merge ediliyor...")
model = model.merge_and_unload()
model.save_pretrained(MERGED_DIR)
AutoTokenizer.from_pretrained(ADAPTER_DIR).save_pretrained(MERGED_DIR)
print("Merge tamam:", MERGED_DIR)

# Hücre 4 — GGUF dönüşümü
!python /content/llama.cpp/convert_hf_to_gguf.py {MERGED_DIR} \
    --outtype q4_k_m \
    --outfile {GGUF_PATH}
print("GGUF kaydedildi:", GGUF_PATH)
```

**Jetson'a kopyalamak için:**
```bash
# Jetson'da (Drive'dan doğrudan veya scp ile):
scp user@ubuntu_pc:/path/to/Qwen3-4B-wbot_v3-Q4_K_M.gguf /home/emk/llama.cpp/
# llama_cpp_backend.py'deki MODEL_PATH'i güncelle:
# MODEL_PATH = "/home/emk/llama.cpp/Qwen3-4B-wbot_v3-Q4_K_M.gguf"
```

---

## Gelecek Yol Haritası

```
[ŞU AN] Jetson demo çalışıyor (wbot_v3, %93 eval)
    ↓
Whisper medium testi + E19 post-processing fix
    ↓
Gürültülü ortam testi (restoran müziği, çoklu konuşmacı)
    ↓
wbot_v4 dataset (~1100 yeni örnek: açıklama+soru, alerji+öneri, anti-hallüsinasyon)
    ↓
Colab A100 — wbot_v4 eğitimi (3 epoch, ~2 saat)
    ↓
GGUF dönüşüm → Jetson deploy → 32+ senaryo eval (%95+ hedef)
    ↓
ReSpeaker Mic Array entegrasyonu (daha iyi gürültü bastırma)
    ↓
Fiziksel robot (W-BOT) entegrasyonu
```

---

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
11. **scipy kullanma** — NumP