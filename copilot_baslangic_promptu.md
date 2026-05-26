# Garson-bot — Proje Durumu ve Geliştirme Bağlamı

Bu prompt, projeyi yeni baştan anlayarak kodlamaya devam etmeni sağlamak için hazırlanmıştır.
Aşağıdaki bilgileri referans alarak tüm geliştirme kararlarını buna göre ver.

---

## Proje Nedir?

Bir restoran için fiziksel servis robotuna (W-BOT) entegre edilecek Türkçe sesli yapay zeka asistanı.
Müşterilerle doğal konuşma, sipariş alma ve menü bilgisi sunma hedeflenmektedir.

---

## Mevcut Kod Tabanı — Özet

### Dosya Yapısı

```
Garson-bot/
├── requirements.txt              # PyYAML, pytest
├── requirements-llm.txt          # torch, transformers, peft, bitsandbytes, safetensors
├── robot_waiter_ai/
│   ├── app/
│   │   ├── main.py               # CLI demo entry point (run_cli)
│   │   └── config.py             # Dosya yolları (menu, restaurant_info)
│   ├── assistant/
│   │   ├── dialogue_manager.py   # Ana diyalog yöneticisi — intent detection, routing
│   │   ├── menu_knowledge.py     # Menü yükleme, normalizasyon, eşleştirme
│   │   ├── order_state.py        # In-memory sipariş durumu (ekle/çıkar/özet)
│   │   ├── persona.py            # Sistem promptu render
│   │   └── safety_rules.py       # Güvenlik yanıtları (allerjen, uydurma önleme)
│   ├── inference/
│   │   ├── qwen_lora_waiter.py   # Qwen + LoRA backend (model yükleme, generate)
│   │   ├── menu_context_builder.py  # YAML → LLM prompt metni
│   │   ├── grounded_demo.py      # Deterministic grounding entry
│   │   └── grounded_result_builder.py / grounded_response_formatter.py
│   ├── demo/
│   │   ├── voice_web_demo.py     # HTTP server + /chat endpoint
│   │   └── voice_web_demo.html   # Browser UI (Web Speech API)
│   └── data/
│       ├── menu.yaml             # Ürün id, name, category, price, allergens, aliases
│       └── restaurant_info.yaml  # Çalışma saatleri, ödeme, politikalar
```

### Şu An Çalışan

- **Deterministic assistant**: Heuristic intent detection → MenuKnowledge + OrderState → metin yanıtı. Birim testleri geçiyor.
- **CLI demo**: `python -m robot_waiter_ai.app.main` ile çalışıyor.
- **Browser demo**: `voice_web_demo.py` HTTP server'ı ayağa kaldırır; `/chat` endpoint'i alır.
- **LLM backend (opsiyonel)**: `--backend qwen` ile Qwen2.5-3B-Instruct + LoRA adapter yüklenip kullanılıyor. `menu_context_builder` menüyü sistem promptuna enjekte ediyor.
- **Veri katmanı**: `menu.yaml` ve `restaurant_info.yaml` eksiksiz; `build_menu_context()` bunları LLM'e uygun metne çeviriyor.

### Mevcut Pipeline

```
Tarayıcı mikrofonu
  → Web Speech API (client-side STT)  ← SADECE DEMO, production yetersiz
  → POST /chat (metin olarak server'a gelir)
  → DialogueManager (deterministic) VEYA QwenLoraWaiterBackend
  → JSON yanıt
  → window.speechSynthesis (client-side TTS)  ← SADECE DEMO
```

---

## Kritik Eksiklikler — Bunları Geliştireceğiz

### 1. Server-side STT yok
Web Speech API production için yetersiz: gürültüye duyarlı, offline çalışmıyor, Türkçe yiyecek adlarında hata oranı yüksek.

**Hedef:** `faster-whisper` entegrasyonu (medium model, int8, VAD ile tetiklenmiş).

### 2. Server-side TTS yok
Şu an tamamen tarayıcıya bağımlı. Robot bir tablet üzerinde çalışacak; tarayıcı TTS Türkçe için yetersiz.

**Hedef:** Coqui TTS veya muadili server-side Türkçe TTS.

### 3. ReSpeaker Mic Array v2.0 entegrasyonu yok
Donanım seçildi (6 mikrofon dizisi, DOA + AEC destekli) ama kod tabanında hiç entegrasyon yok.

**Hedef:** ReSpeaker USB bağlantısı, beamforming kanalı, AEC etkinleştirme.

### 4. Echo cancellation yok
Robot konuşurken mikrofon kendi sesini alıyor. `is_speaking` flag mekanizması yok.

### 5. Çoklu konuşmacı yönetimi yok
Masada birden fazla kişi konuştuğunda kim dinlenecek? DOA + UX stratejisi yok.

### 6. Latency optimizasyonu yok
STT → LLM → TTS zinciri şu an senkron; streaming generation uygulanmamış. Hedef: ≤ 2s toplam.

### 7. Wake word mekanizması yok
Sürekli Whisper çalışması kaynak tüketir; `openWakeWord` ile tetiklemeli dinleme gerekli.

### 8. Sipariş doğrulama eksik
Yanlış transkripsiyon koruması yok. Fuzzy matching ve özet-onay akışı yok.

### 9. Production deployment yok
`http.server` production için uygun değil. FastAPI + Uvicorn + Docker gerekli.

### 10. systemd / watchdog yok
Uzun çalışmada OOM / Exit 137 riski var. Otomatik yeniden başlatma mekanizması yok.

---

## Teknik Hedef Stack

| Katman | Mevcut | Hedef |
|---|---|---|
| STT | Web Speech API | faster-whisper (medium, int8) + silero-vad |
| LLM | Qwen2.5-3B + LoRA | Aynı + streaming generation |
| TTS | browser SpeechSynthesis | Coqui TTS (server-side, Türkçe) |
| Mikrofon | Tarayıcı | ReSpeaker v2.0 (USB, beamforming) |
| Echo | Yok | ReSpeaker AEC + is_speaking flag |
| Wake word | Yok | openWakeWord ("hey garson") |
| Backend | http.server | FastAPI + WebSocket |
| Deployment | Local script | Docker + systemd watchdog |

---

## Model Bilgileri

- **Base model:** `Qwen/Qwen2.5-3B-Instruct` (local: `robot_waiter_ai/models/Qwen2.5-3B-Instruct`)
- **LoRA adapter:** `qwen25_3b_waiter_v1_1_lora` (`adapter_config.json` + `adapter_model.safetensors`)
- **Quantization:** `BitsAndBytesConfig(load_in_4bit=True)` — CUDA varsa aktif, Windows'ta devre dışı
- **Max new tokens:** 120, `repetition_penalty=1.05`

---

## Hardcoded — Dışarı Çıkarılması Gerekenler

```python
# qwen_lora_waiter.py
DEFAULT_BASE_MODEL_PATH = "robot_waiter_ai/models/Qwen2.5-3B-Instruct"
SYSTEM_PROMPT = "Sen Türkçe konuşan kibar bir restoran garson asistanısın..."
CONTEXT_GUARDRAIL = "Yalnızca aşağıda verilen menü ve restoran bağlamını kullan..."

# voice_web_demo.py
DEFAULT_BACKEND = "deterministic"
# HTML'de: tr-TR dil kodu hardcoded
```

---

## Geliştirme Kuralları (Bu Projede Her Zaman Uygula)

1. **Mevcut deterministic pipeline'ı bozma** — tüm yeni özellikler mevcut `DialogueManager` + `MenuKnowledge` katmanlarının üstüne eklenmeli.
2. **Async-first** — tüm yeni I/O (mikrofon, STT, LLM, TTS) `asyncio` tabanlı olmalı.
3. **Her diyalog sonrası bellek temizle** — `gc.collect()` + `torch.cuda.empty_cache()`.
4. **Config dosyasına taşı** — hardcoded path, port, dil kodu, model adı kalmayacak; `config.yaml` veya `.env` kullan.
5. **Türkçe karakter güvenliği** — tüm dosya okuma/yazma işlemlerinde `encoding='utf-8'` zorunlu.
6. **Fuzzy matching** — menü eşleştirmelerinde her zaman `rapidfuzz` kullan, basit `in` karşılaştırması yeterli değil.
7. **Hata mesajları Türkçe olsun** — müşteriye dönük tüm fallback mesajları Türkçe.
8. **Test yaz** — her yeni modül için `tests/` altına en az bir smoke test ekle.

---

## Başarı Kriterleri

```
Müşteri: "Ayran ne kadar?"
Robot:   "Ayran 85 TL'dir, buyurun."              ✅ Menüden okuyarak, tereddütsüz

Müşteri: "Paket servis var mı?"
Robot:   "Menümüzde bu detay yok, personelimize sorabilirsiniz."  ✅ Kibarca yönlendirme

Müşteri: "Ayran ne kadar?"
Robot:   "Bu konuda güvenlik garantisi veremem."   ❌ Asla böyle olmamalı

Sistem 8 saat çalıştıktan sonra:
Robot:   Hâlâ cevap veriyor.                       ✅ OOM yok, watchdog çalışıyor
```

---

Bu bağlamı aklında tut. Bundan sonraki her isteği bu projenin parçası olarak değerlendir.
Yeni bir özellik ekleyeceğinde önce mevcut mimariye nereye oturduğunu açıkla, sonra kodu yaz.
