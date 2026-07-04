# W-BOT Metodoloji Belgesi

**Proje:** Türkçe Konuşan Restoran Garson Robotu (W-BOT)
**Tarih:** 24 Haziran 2026 (v5.9)
**Hedef:** Fiziksel servis robotuna entegre edilecek, gerçek zamanlı Türkçe sesli yapay zeka asistanı

---

## 1. Proje Genel Bakış

### Ne Yapıyor?
W-BOT, bir restoranın masasına gelen müşterilerle doğal Türkçe konuşabilen, sipariş alabilen ve menü hakkında bilgi verebilen bir yapay zeka asistanıdır. Kullanıcı "hey garson" dediğinde uyanır, soruyu anlar, yanıt üretir ve sesli olarak cevap verir.

### Hedef Donanım
**NVIDIA Jetson Orin NX 16GB** — küçük form faktörlü, güçlü GPU'ya sahip gömülü sistem bilgisayarı. Bir robota monte edilecek şekilde tasarlanmıştır. Restoran gibi gürültülü ve gerçek zamanlı tepki gerektiren bir ortamda çalışacaktır.

### Neden Jetson Orin NX?
- Masaüstü GPU kartı gerektirmeyen, kompakt boyutlu yapay zeka bilgisayarı
- 16GB birleşik bellek (CPU + GPU paylaşır) — küçük/orta LLM modellerini çalıştırmaya yeterli
- CUDA destekli Ampere GPU (SM87) — yerel, internet gerektirmeyen çıkarım
- Sektörde robot ve kenar yapay zeka uygulamalarında yaygın kullanım

---

## 2. Sistem Mimarisi

Sistem, birbiriyle sıralı çalışan beş bileşenden oluşur:

```
Müşteri konuşur
      │
      ▼
[1] WAKE WORD — "hey garson" algılanınca uyanır
      │
      ▼
[2] VAD + KAYIT — ses bitmeyene kadar kaydeder
      │
      ▼
[3] STT — sesi metne çevirir
      │
      ▼
[4] LLM — Türkçe yanıt üretir
      │
      ▼
[5] TTS — metni sese çevirir ve çalar
      │
      ▼
Tekrar wake word bekler
```

Her bileşen bağımsız modüldür; biri değiştirildiğinde diğerleri etkilenmez.

---

## 3. Bileşen 1: Wake Word Algılama

### Ne İşe Yarar?
Sistemin sürekli dinlemede olmasını sağlar. Mikrofon her zaman açıktır; yalnızca "hey garson" komutu geldiğinde sistem aktif hale geçer.

### Kullanılan Teknoloji: openWakeWord
- Google'ın AudioSet verileriyle eğitilmiş genel ses özellikleri çıkarıcısı (Melspectogram + embedding modeli)
- Üstüne hafif bir FCN (Fully Connected Network) başlığı eğitilir — bu başlık "hey garson"ı tanır
- Model boyutu: **789 KB** (Jetson'da RAM etkisi minimumdur)
- Çalışma formatı: ONNX (donanım bağımsız)

### Neden openWakeWord?
| Alternatif | Neden Reddedildi |
|-----------|-----------------|
| Porcupine (Picovoice) | Ticari lisans, aylık ücret |
| Snowboy | Geliştirilmiyor, Python 3'te sorunlu |
| Whisper sürekli dinleme | Çok yavaş — her saniye STT çalıştırmak GPU'yu yorar |
| openWakeWord | Açık kaynak, özel kelime eğitilebilir, ONNX, hafif |

### Eğitim Süreci
1. **Pozitif örnekler (3000 adet):** MMS-TTS (Meta'nın çok dilli TTS motoru) ile "hey garson" cümlesi farklı ses tonları ve hızlarda sentezlendi
2. **Negatif örnekler (4840 adet):** openWakeWord'ün yerleşik arka plan gürültüsü havuzu kullanıldı
3. **Eğitim:** FCN başlığı Sklearn ile eğitildi, ONNX'e dönüştürüldü
4. **Smoke test sonucu:** Pozitif skor 0.999, negatif skor 0.001

### Eşik Değeri (Threshold = 0.7)
- Başlangıçta 0.5 kullanıldı — çok hassastı, masa konuşmalarında yanlış tetiklendi
- 0.7'ye çıkarıldı — yanlış pozitifler azaldı, gerçek aktivasyonlar hâlâ %100 yakalanıyor

### Teknik Detay: False Positive Sorunu ve Çözümü
**Sorun:** Bot yanıt verdikten sonra mikrofon akışında kalan artık ses (buffer kalıntısı) modeli anında yeniden tetikliyordu.

**Çözüm:** Mikrofon akışı açıldığında ilk 10 chunk (10 × 80ms = 800ms) atlanır. Bu süre zarfında model tahmin yapmaz. Kullanıcıya görünür bir gecikme eklenmez çünkü bu bekleme arka planda gerçekleşir.

```python
_warm_up = [10]  # mutable list — closure içinde değiştirilebilir

def _cb(indata, frames, time_info, status):
    if _warm_up[0] > 0:
        _warm_up[0] -= 1
        return   # ilk 800ms'i atla
    # ... model çalıştır
```

---

## 4. Bileşen 2: Ses Kaydı (VAD)

### Ne İşe Yarar?
Wake word algılandıktan sonra müşterinin konuşmasını kaydeder. Müşteri konuşmayı bitirince kaydı durdurur.

### Kullanılan Teknoloji: webrtcvad
Google'ın WebRTC projesinden çıkan Ses Aktivite Algılama (VAD — Voice Activity Detection) kütüphanesi.

### Neden VAD?

**Eski yöntem:** Sabit 6 saniyelik kayıt
- Müşteri 2 saniyede konuşsa bile 6 saniye bekleniyordu
- Yanıt süresi gereksiz uzuyordu

**Yeni yöntem:** VAD tabanlı değişken süreli kayıt
- Müşteri konuşmayı bitirince 1.5 saniye sessizlik sonrası kayıt durur
- Ortalama kayıt süresi: 3-5 saniye (cümle uzunluğuna göre)

### Teknik Detaylar
```
VAD Aggressiveness = 3    (0-3 arası; 3 en katı, gürültülü ortam için)
Chunk boyutu       = 30ms (webrtcvad'ın kabul ettiği: 10/20/30ms)
Sessizlik eşiği    = 1.5 saniye (konuşma bitti sayılır)
Pre-roll buffer    = 150ms (konuşma başlamadan önceki ses tutulur)
Maksimum kayıt     = 12 saniye (güvenlik kapağı)
```

### Conversation Hold (v4.7)

Eski tasarımda her tur için kullanıcının yeniden "hey garson" demesi gerekiyordu — bu, restoran senaryosunda doğal konuşma akışını bozuyordu.

v4.7'de eklenen mekanizma: bot yanıtı bittikten sonra **10 saniyelik** bir "konuşma penceresi" açılır. Bu pencerede wake word beklenmez; VAD aktif şekilde konuşma dinler.

```
[Bot yanıtı tamamlandı]
       │
       ▼
CONVO_HOLD_S=10s pencere aç (wake word YOK)
       │
       ├── Konuşma geldi → tur devam (LLM history korunur, "bir de şu olsun" mümkün)
       │
       └── 10s sessizlik → wake word moduna dön
               └── Farewell tespit edildiyse → llm.reset_history() + order.reset() + new_customer=True
```

`_record()` artık `initial_wait_s` parametresiyle çağrılır; konuşma başlamadan timeout olursa `b""` döner ve ana döngü pencereyi kapatır. Farewell tespiti (`is_farewell`) artık doğrudan reset uygulamaz — sadece `pending_reset = True` işaretler; reset gerçekten 10s sessizlikten sonra uygulanır (müşterinin "bir de şu olsun" diye eklemesi için fırsat verir).

### USB Mikrofon Uyumluluk Sorunu ve Çözümü
**Sorun:** USB PnP mikrofon yalnızca 48kHz native örnekleme hızını destekler. Ancak webrtcvad ve Whisper 16kHz gerektirir. Sounddevice'a `samplerate=16000` verilince `paInvalidSampleRate` hatası alındı.

**Çözüm:** Mikrofon native hızda (48kHz) açılır, her chunk `np.interp` ile 16kHz'ye yeniden örneklenir (resample). scipy kullanılmadı — NumPy 2.x ile uyumsuz olduğu için.

```python
native_sr = int(sd.query_devices(input_device)["default_samplerate"])  # 48000
audio_16k = np.interp(
    np.linspace(0, len(audio), int(len(audio) * 16000 / native_sr)),
    np.arange(len(audio)),
    audio
).astype(np.int16)
```

---

## 5. Bileşen 3: Konuşmadan Metne (STT)

### Kullanılan Teknoloji: faster-whisper (Whisper small — PC, medium — Jetson hedefi)
OpenAI'ın Whisper modelinin CTranslate2 motoruyla optimize edilmiş versiyonu.

### Model Seçimi

| Model | Parametre | Kalite | Jetson GPU Süresi |
|-------|-----------|--------|-------------------|
| tiny | 39M | Düşük — Türkçe restoran kelimelerini kaçırıyor | ~200ms |
| small | 244M | İyi — restoran ortamı için yeterli | ~850ms |
| **medium** | 769M | **Çok iyi — Türkçe kalitesi belirgin yüksek** | **~1500-2000ms** |

**Jetson'da medium** aktif (7 Haziran 2026 doğrulandı, 1.7s CUDA). **PC'de small** kullanılıyor: 5.64 GB GPU'da (RTX 4050) Qwen3-4B + Whisper medium CUDA workspace birlikte sığmıyor (`CUDA failed with error out of memory`). `demo_usb.py`'deki `_stt_backend()` toplam VRAM'e bakarak otomatik seçer: ≥8 GB → CUDA float16 (Jetson), <8 GB → CPU int8 (PC).

### STT Cihaz Seçimi (v4.6)

`scripts/demo_usb.py:_stt_backend()` toplam VRAM'e bakarak cihazı belirler:

```
Toplam VRAM ≥ 8 GB (örn. Jetson 16 GB) → CUDA float16
Toplam VRAM <  8 GB (örn. RTX 4050 6 GB) → CPU int8
W_BOT_STT_DEVICE env  → manuel override ("cpu"/"cuda")
```

LLM ile aynı GPU'da çakışma riski olduğunda CPU'ya düşülür. PC'de CPU int8 Whisper small latency'si **130-300 ms** (CUDA medium'un 10× hızlısı) çünkü model küçük + int8 kuantizasyonu. VRAM kullanımı 0.

### CUDA Hızlandırması
**Sorun:** ctranslate2'nin standart pip paketi ARM64/Jetson için CUDA içermez.

**Çözüm:** ctranslate2 kaynaktan derlendi:
```bash
cmake .. -DWITH_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=87 \
         -DOPENMP_RUNTIME=COMP -DWITH_MKL=OFF
make -j4
pip install ./python
```
- `CUDA_ARCHITECTURES=87` → Jetson Orin NX'in Ampere GPU'su (SM87)
- `OPENMP_RUNTIME=COMP` → Intel OpenMP yerine GNU libgomp (ARM'da Intel yoktur)
- `WITH_MKL=OFF` → Intel MKL kütüphanesi ARM'da bulunmaz

**Sonuç:**

| | CPU (ARM) | CUDA (SM87) |
|---|---|---|
| 3s ses için STT | 1.88s (ölçüldü) | **0.78s (ölçüldü)** |
| Gerçek konuşma (4-5s) | ~2.5-3.5s | **~0.85-1.1s** |
| Gerçekten kazanılan | — | ~1.5-2 saniye/tur |

### Whisper Doğruluk İyileştirmesi: initial_prompt
Whisper, bir önceki konuşmanın metnini "ipucu" olarak alabilir. Menü kelimeleri (mercimek çorbası, ızgara köfte, künefe...) başlangıçta verilince modelin bu kelimeleri doğru tanıma olasılığı artar.

### Otomatik Cihaz Seçimi
```python
def _stt_backend():
    try:
        import ctranslate2
        if ctranslate2.get_supported_compute_types("cuda"):
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "float32"
```
CUDA varsa float16, yoksa CPU float32 kullanılır. Not: yeni derlenen ctranslate2'de CPU int8 desteklenmiyor — float32'ye geçildi. Kod değişikliği gerekmez.

---

## 6. Bileşen 4: Dil Modeli (LLM)

### Kullanılan Model: Qwen3-4B
Alibaba'nın Qwen3 serisinin 4 milyar parametreli modeli. Türkçe dahil çok dilli eğitim almış, instruction-tuned (talimat takibi için ince ayarlı).

### Neden Qwen3-4B?

| Kriter | Açıklama |
|--------|----------|
| Türkçe kalitesi | Türkçe eğitim verisine sahip en iyi küçük modeller arasında |
| Boyut | 4B parametre → Q4_K_M quantization sonrası ~2.37 GB VRAM |
| Hız (Jetson) | ~12-15 token/saniye |
| Thinking modu | Kapatılabilir — kısa, doğrudan yanıtlar için gerekli |

### Qwen3-1.7B ile Karşılaştırma (Reddedildi)
1.7B modeli test edildi:
- Hız: 23.4 tok/s (1.9× daha hızlı)
- Kalite: Yetersiz — "pizza var mı?" sorusuna anlamsız yanıt, "güle güle"ye yanlış tepki, sipariş yerine soru sorma
- **Karar:** 4B kalite açısından zorunlu, 1.7B reddedildi

### İki Backend: Neden İkisi Var?

| Backend | Nerede | Teknoloji | Neden |
|---------|--------|-----------|-------|
| `qwen3_backend.py` | Geliştirme PC (RTX 4050) | HuggingFace Transformers + BitsAndBytes 4-bit NF4 | Kolay geliştirme, tam Python ekosistemi |
| `llama_cpp_backend.py` | Jetson Orin NX | llama-cpp-python + GGUF Q4_K_M | Jetson için CUDA-optimized, düşük bellek kullanımı |

Geliştirme PC'de Transformers ekosistemi tam çalışır. Jetson'da ise `llama-cpp-python` CUDA SM87 için özel derlenmiştir ve GGUF formatı daha az VRAM kullanır.

### Quantization: Neden Q4_K_M?
Model boyutunu 4 bitte saklamak (Q4) VRAM kullanımını ~4× azaltır. `_K_M` (K-means, Medium) kalite/hız dengesini optimize eder. Jetson'un 16GB birleşik belleği model, OS ve diğer bileşenleri aynı anda barındırır.

### KV Cache Ön Isıtma
**Sorun:** LLM'in sistem promptu (~944 token) her ilk istekte işlenmesi gerekirdi. Bu soğuk başlangıç için ~2.96 saniye gecikme yaratır.

**Çözüm:** Uygulama başlarken `generate_reply("Merhaba.") + reset_history()` çağrısı yapılır. Bu çağrı sistem promptunu KV cache'e yükler. Sonraki tüm isteklerde cache'den okunur.

```
Soğuk TTFT: ~2.96 saniye
Sıcak TTFT: ~0.25 saniye  (12× iyileşme)
```

### Sistem Promptu Tasarımı
LLM'e verilen sistem promptu şu kuralları içerir:
- Yalnızca Türkçe yanıt, emoji ve madde işareti yasak
- Yalnızca menüdeki ürünler, uydurma ürün yok
- Karşılama ve genel menü sorusunda dört kategori adının (çorba, ana yemek, tatlı, içecek) dördü de geçmek zorundadır; ürün adı sayılmaz
- **Öneri/tavsiye sorusunda** ("ne önerirsin/ne yesem/ne alsam" gibi): 1-2 ürün **YALNIZCA İSİMLE** önerilir, fiyat söylenmez (v4.7). Kategori belirtildiyse (örn. "çorba olarak") o kategoriden 2 ürün
- **Fiyat söyleme kuralı (v4.7):** Fiyat sadece şu üç durumda söylenir: (1) müşteri açıkça fiyat sorduysa, (2) sipariş onayında, (3) hesap istendiğinde. Öneri/tanıtım/sohbette fiyat söylenmez
- Sipariş onayı için yapısal şablon: "Elbette/Tabii ki/..." gibi olumlu kabul + ürün adı + TL fiyat + sonunda "başka bir şey alır mısınız?" anlamına gelen bir soru. "Getireyim mi?" sipariş onayında YASAK — yalnızca "nedir/nasıl" ürün sorusunda kullanılır
- Toplam yalnızca hesap istenince söylenir; ara toplam soruları için "Bu konuda bilgim yok, personelimize sorabilirsiniz" yönlendirmesi
- Vejetaryen/allerjen sorusu için menü etiketlerini kullan

**v4.6 değişikliği — birebir şablon → yapısal yönerge:** Prompt KURALLAR bloğundaki cümle örnekleri (örn. "Elbette, [ürün] [fiyat] TL eklendi. Başka bir şey alır mısınız?" gibi birebir kalıplar) "şu içeriği şu sırayla, doğal bir varyasyonla söyle" tarzına çevrildi. Greedy decoding + birebir şablon kombinasyonu her turda kelimesi kelimesine aynı yanıt üretiyordu; bu kalıplaşma kullanıcı şikayeti olarak işaretlendi.

### Thinking Modunu Kapatma
Qwen3 modeli varsayılan olarak yanıttan önce uzun bir iç akıl yürütme (`<think>...</think>`) bloğu üretir. Bu blok 100-300 token uzunluğunda olabilir ve yanıt gecikmesini ciddi şekilde artırır. Restorant senaryosunda hızlı yanıt gerektiğinden bu mod kapatıldı:

```python
# llama_cpp_backend — format_prompt içinde:
parts.append("<|im_start|>assistant\n<think>\n\n</think>\n\n")
# Boş think bloğu → model düşünmeden yanıta geçer

# qwen3_backend — apply_chat_template içinde:
enable_thinking=False
```

### Decoding Parametreleri (v4.6)

v4.5'e kadar her iki backend de greedy decoding (`do_sample=False` / `temperature=0`) kullanıyordu. Sonuç: aynı kullanıcı cümlesi her seferinde **kelimesi kelimesine aynı yanıtı** üretiyordu. Restoran senaryosunda aynı müşteri farklı turlarda aynı cümleyi duyduğunda doğallık kaybediliyordu.

v4.6'da sampling tabanlı decoding'e geçildi:

| Parametre | Değer | Gerekçe |
|-----------|-------|---------|
| `temperature` | 0.55 | Çeşitlilik için 0 → 0.55. 0.7+ değerlerde model sayı/format halüsinasyonu yapıyordu (örn. "Bir köfte" → "İki köfte 480 TL"). |
| `top_p` | 0.9 | Düşük olasılıklı tokenlerin tamamen elenmesi yerine üst %90'ı tutar |
| `top_k` | 40 | (v4.8) En yüksek 40 token havuzu; daha sağlıklı varyasyon |
| `repetition_penalty` / `repeat_penalty` | 1.2 | (v4.8'de 1.15→1.2) Sampling açıkken tekrarlanan n-gram'ları azaltır |
| `max_tokens` / `max_new_tokens` | 50 | (v4.8'de 80→50) "1 cümle / 20 kelime" hedefi; uzun listeleme engellenir |

Aynı parametreler `qwen3_backend.py` (HuggingFace transformers `model.generate`) ve `llama_cpp_backend.py` (`llm.create_completion`) için ortak. Eval suite 16/16 (%100) PASS oranı korundu; ortalama latency 1745 ms → 2330 ms (greedy → sampling overhead'i).

**Seed (4 Temmuz 2026 notu):** `llama_cpp_backend.py`'nin `Llama()`
çağrısında açık bir `seed=` parametresi yok. Buna rağmen wbot_v4
eval'inde (`eval_gguf.py`) aynı 38 senaryoluk koşu iki kez birebir aynı
sonucu verdi — llama-cpp-python'ın seed verilmediğinde kullandığı
varsayılan davranış zamana/entropiye dayanmıyor gibi görünüyor, ama bu
koda yazılı/garanti edilmiş değil. Öneri: `seed=42` gibi sabit bir değer
açıkça geçilsin — hem tekrarlanabilirlik dokümante edilmiş olur hem de
gelecekte llama-cpp-python sürüm değişikliğiyle varsayılan davranış
değişirse sessiz bir regresyon riski önlenir.

### Konuşma Geçmişi Yönetimi
Jetson'da bağlam penceresi (n_ctx) **4096 token** (sistem prompt ~2100 tok olduğundan 1536 yetersizdi). Konuşmaya kalan: ~1931 token (~10-12 tur).

`_trim_history()` fonksiyonu toplam geçmiş boyutu eşiği aşınca en eski user+assistant çiftini siler:

```python
_MAX_HIST_CHARS = 4000  # Jetson: karakter cinsinden
# PC (qwen3_backend): 12000 karakter — uzun oturumlar için geniş bağlam

def _trim_history(self):
    while len(self._history) > 1:
        total = sum(len(m["content"]) for m in self._history)
        if total <= self._MAX_HIST_CHARS:
            break
        self._history = self._history[2:]  # en eski çifti sil
```

### LLM Eval Sonuçları
`eval_llm.py` ile 16 senaryo, 10 müşteri diyalogu otomatik test edildi:

| Versiyon | Başarı |
|---------|--------|
| Prompt v4.0 | 14/16 (%87) |
| Prompt v4.1 | 16/16 (%100) |
| **Prompt v4.6 (sampling + gevşetilmiş prompt)** | **16/16 (%100)** |

---

## 7. Bileşen 5: Metinden Sese (TTS)

### Kullanılan Teknoloji: Piper TTS
Mozilla'nın açık kaynak offline TTS motoru. Türkçe ses modeli: `tr_TR-fahrettin-medium.onnx`.

### Neden Piper?

| Alternatif | Neden Reddedildi / Neden Piper? |
|-----------|-------------------------------|
| edge-tts (Microsoft) | İnternet bağlantısı gerekiyor — restoran interneti güvenilmez olabilir |
| Google TTS | Ücretli API, internet gerekli |
| gTTS | Düşük kalite, internet gerekli |
| **Piper** | **Offline, aarch64 uyumlu binary, doğal Türkçe ses** |

### Streaming Pipeline: İlk Sesi Hızla Başlatma
Naive yaklaşım: LLM tüm yanıtı üretir → TTS sentezler → ses çalar. Bu yaklaşım gereksiz gecikme yaratır.

Kullanılan yaklaşım: Paralel pipeline

```
LLM thread → cümle biter → sentence_q'ya koy
                                    │
                            tts_worker alır → Piper sentezler → audio_q'ya koy
                                                                       │
                                                               play_worker alır → ses çalar
```

`tts_worker` ve `play_worker` eş zamanlı çalışır: birinci cümle çalarken ikinci cümle sentezlenir. Bu yaklaşım ilk sese kadar geçen süreyi (TTFA) önemli ölçüde azaltır.

### Latency Ölçümleri (Jetson, CUDA STT aktif)

| Aşama | Süre |
|-------|------|
| STT (Whisper small, CUDA) | ~850–1100ms |
| LLM ilk cümle üretimi (warm cache) | ~750ms |
| Piper ilk cümle sentezi | ~600–800ms |
| **İlk kelimeyi duyma (TTFA)** | **~2.2–2.7 saniye** |
| Tam yanıt (konuşma süresi dahil) | ~7–8 saniye |

Not: 7–8 saniyelik ölçüm botun konuşma süresini de içerir. Müşteri botun ilk kelimesini ~2.5 saniyede duyar; gerisi botun konuşmasıdır.

---

## 8. OrderTracker: Sipariş Takibi

### Neden Ayrı Bir Modül?
LLM konuşma bağlamına dayanarak sipariş onaylar, ancak uzun konuşmalarda geçmişin bir kısmı silinir (`_trim_history`). Doğru fatura hesabı için LLM'in hafızasına güvenilemez.

**Çözüm:** Python tarafında bağımsız `OrderTracker` sınıfı. LLM'in çıktısına değil, kullanıcının söylediğine bakılır.

### Nasıl Çalışır?

Kullanıcı metni aşağıdaki üç duruma göre parse edilir:

**Durum 1 — Ekleme:**
```
"alayım / istiyorum / getir / ..." kelimelerinden biri geçiyorsa
→ eşleşen menü ürününü toplamaya ekle
```

**Durum 2 — İptal:**
```
"istemiyorum / iptal / çıkar / ..." kelimelerinden biri geçiyorsa
→ eşleşen menü ürününü toplamdan çıkar (negatife düşme)
```

**Durum 3 — Takas ("X yerine Y"):**
```
"yerine" kelimesi geçiyorsa
→ soldaki ürünü çıkar, sağdaki ürünü ekle
```

### Adet Tespiti
"iki köfte alayım" → 480 TL (2 × 240) doğru hesaplanır. Alias'tan önceki 1-2 kelimeye bakılır:

```python
_QUANTITIES = {"iki": 2, "üç": 3, "dört": 4, "2": 2, "3": 3, "4": 4}

m1 = re.search(r'(\w+)\s+' + re.escape(alias), t)  # "iki köfte"
m2 = re.search(r'(\w+)\s+\w+\s+' + re.escape(alias), t)  # "iki tane köfte"
qty = _QUANTITIES.get(m1.group(1), 1)
```

### Türkçe İ Sorunu
Python'da `"İ".lower()` → `"i̇"` (i + birleştirme noktası U+0307) üretir. Bu standart `"i"` ile eşleşmez. Çözüm:

```python
t = user_text.lower().replace('̇', '')
```

### Bilinen Sınırlama — Ekle+Kapat Çakışması (4 Temmuz 2026)
**Sorun şüphesi (statik analiz, testle doğrulanmadı):** `detect_order()`
önce "İptal" dalını kontrol ediyor (`is_cancel = any(v in t for v in
_CANCEL_VERBS)`), bu da "ekleme" dalından ÖNCE çalışıyor. "Bir de ayran,
başka istemiyorum." gibi bir cümlede "istemiyorum" `_CANCEL_VERBS`
içinde olduğu için `is_cancel=True` oluyor; iptal dalı "ayran"ı bulup
`_remove_item()` çağırıyor ama ayran sepette olmadığından bu no-op
kalıyor, fonksiyon **erken `return` ediyor** — ayran hiçbir zaman
`_add_item()` ile eklenmiyor. Yani aynı cümlede hem yeni bir ürün
belirtilip hem de kapanış sinyali ("başka istemiyorum") verildiğinde,
cancel dalı ekleme dalına hiç ulaşılmasını engelliyor.

Bu, S12 (sipariş kapanışı özeti) runtime guard tasarımının önkoşulu
olarak keşfedildi — henüz kod düzeltmesi yapılmadı, doğrulama ve
düzeltme sırası: `claude_code_prompt_C_paketi_dataset.md` Bölüm 6.

### Hesap + Sipariş Aynı Cümlede
**Sorun:** "Bir köfte alayım, toplam ne kadar?" → LLM sistem promptunda "sipariş sırasında toplam söyleme" kuralı olduğu için toplam vermiyordu.

**Çözüm:** Sipariş fiili + hesap isteği birlikte algılanınca LLM girdisine özel yönerge eklenir:

```python
if has_new_order and _is_bill_request(user_text):
    llm_input = (f"{user_text} [Yanıtın sonu şöyle bitmeli: "
                 f"Toplam {order_tracker.total} TL. Afiyet olsun!]")
```

Bu yaklaşım LLM'in doğal sipariş onay davranışını bozmadan toplam ekletir.

---

## 9. Teknik Kararlar ve Gerekçeleri

### asyncio Tercih Edilmesi
Sistemin tüm bileşenleri (kayıt, STT, LLM, TTS, oynatma) I/O bağımlıdır. `asyncio.to_thread` ile tüm bloke eden işlemler ayrı thread'lere taşınır; event loop bloke olmaz. Bu streaming pipeline'ın mümkün olmasını sağlar.

### aplay ile Ses Çalma (sounddevice Değil)
Sounddevice hem kayıt hem oynatma için kullanıldığında USB cihaz çakışması yaşandı. `aplay` subprocess olarak çağrılır — kayıt cihazını etkilemez.

### scipy Kullanılmaması
Jetson'da sistem Python paketleri (pandas, sklearn) NumPy 1.x için derlenmiş. pip ile NumPy 2.x yüklü olunca scipy ile çakışma oluyordu. Resampling için `np.interp` yeterli; scipy bağımlılığı tamamen kaldırıldı.

### LLM Backend Otomatik Seçimi
```python
try:
    from robot_waiter_ai.inference.llama_cpp_backend import LlamaCppBackend
    llm = LlamaCppBackend()
    print("LLM: llama-cpp-python GGUF (GPU)")
except Exception:
    from robot_waiter_ai.inference.qwen3_backend import Qwen3Backend
    llm = Qwen3Backend()
    print("LLM: Qwen3 transformers (PC)")
```
Aynı kod Jetson'da ve geliştirme PC'de çalışır.

---

## 10. Karşılaşılan Teknik Sorunlar ve Çözümler

| Sorun | Kök Neden | Çözüm |
|-------|-----------|-------|
| `paInvalidSampleRate` | USB mikrofon yalnızca 48kHz destekliyor | Native rate'de aç, np.interp ile 16kHz'e çevir |
| Wake word false positive | Buffer kalıntısı anında tetikliyordu | 800ms warm-up (ilk 10 chunk'ı atla) |
| Thinking modu açık kalıyor | Qwen3'ün varsayılan davranışı | llama.cpp'de boş `<think>` prefix; transformers'da `enable_thinking=False` |
| Sipariş geçmişi kaybı | `_trim_history` eski konuşmaları siliyor | OrderTracker LLM'den bağımsız Python tarafında çalışır |
| Hesap + sipariş çakışması | "Toplam söyleme" kuralı hesap isteğini engelliyor | `has_new_order` tespiti + özel LLM yönergesi |
| **Demo 2. turdan sonra tamamen donuyor** | `TextIteratorStreamer` timeout yok — `model.generate()` CUDA hatası/OOM atınca streamer stop sinyali almıyor; `for token in streamer:` sonsuza bloklanıyor | `timeout=30.0` + `_generate_safe()` wrapper (exception'da manuel stop sinyali) + `gen_thread.join(timeout=10)` + `torch.cuda.empty_cache()` (v4.5) |
| **STT CUDA OOM (`CUDA failed with error out of memory`)** | 5.64 GB GPU'da Qwen3-4B (2.5 GB) + KV cache + Whisper medium CUDA workspace birlikte sığmıyor | (1) `WHISPER_MODEL = "small"` (Codex), (2) `_stt_backend()` toplam VRAM'e bakar; <8 GB ise CPU int8 (v4.6), (3) KV ısıtmadan sonra `torch.cuda.empty_cache()` |
| Her turdan sonra sistem sessiz bekliyor | `ww_task` yeniden yaratılırken "hey garson bekleniyor" print yok | Her yeni `ww_task` sonrası print eklendi (v4.5) |
| HuggingFace Hub'a her başlatmada istek atılıyor | `from_pretrained` varsayılan olarak Hub'u kontrol ediyor | `local_files_only=True` + ilk çalıştırmada download fallback (v4.5) |
| openwakeword import hatası | NumPy 2.x — sistem scipy uyumsuzluğu | `pip install "numpy<2.0"` ile 1.26'ya düşürüldü |
| openwakeword model bulunamadı | pip paketi model dosyalarını içermiyor | `openwakeword.utils.download_models()` çağrısı |
| ctranslate2 CUDA ARM64'te yok | pip paketi ARM için CUDA içermiyor | Kaynaktan derleme (cmake + CUDA SM87) |
| ctranslate2 Intel OpenMP hatası | ARM'da Intel kütüphanesi yok | `-DOPENMP_RUNTIME=COMP -DWITH_MKL=OFF` |
| ctranslate2 MKL bulunamadı hatası | ARM'da Intel MKL yok | `-DWITH_MKL=OFF` |
| ctranslate2 CPU int8 desteklenmiyor | Yeni derleme ARM için int8 optimizasyonu içermiyor | CPU fallback'i float32'ye geçirildi |

---

## 11. Performans Özeti (Jetson Orin NX)

| Bileşen | Değer |
|---------|-------|
| LLM VRAM kullanımı | ~2.37 GB / 15.6 GB |
| LLM token üretim hızı | ~12-15 tok/s |
| LLM ilk token (sıcak cache) | ~250ms |
| STT latency (Whisper medium, CUDA float16) | ~1700-2100ms (ölçüldü, 7 Haziran 2026) |
| TTS sentez (Piper, CPU) | ~500-800ms |
| **Müşteriye ilk ses (TTFA)** | **~5-7 saniye** (VAD 1.5s + STT 1.7s + LLM+TTS ~2s) |
| LLM eval başarı (GGUF, Jetson) | 31/32 (%96) |

---

## 12. Mevcut Durum ve Sonraki Adımlar

### Tamamlananlar ✅
- Wake word eğitimi ve Jetson deployment
- VAD tabanlı akıllı ses kaydı
- openwakeword Jetson'a kuruldu (numpy<2.0 uyumlu)
- ctranslate2 CUDA SM87 kaynaktan derlendi (`-DWITH_CUDA=ON -DOPENMP_RUNTIME=COMP -DWITH_MKL=OFF`)
- Whisper **medium** CUDA STT (kalite için small'dan yükseltildi, v4.5)
- Qwen3-4B GGUF LLM (llama-cpp-python CUDA)
- Piper TTS offline Türkçe ses
- OrderTracker (ekleme + iptal + takas + adet)
- Streaming pipeline (paralel TTS + oynatma)
- LLM eval %100 başarı
- False positive düzeltme (800ms warm-up)
- Hesap + sipariş aynı cümlede doğru yanıt
- Per-turn STT ve LLM+TTS latency ölçümü
- **TextIteratorStreamer donma düzeltmesi** — 2. turdan itibaren donma giderildi (v4.5)
- **Öneri/tavsiye yanıtı** — "ne önerirsin?" sorusunda menüden ürün önerilir (v4.5)
- **Bağlam penceresi genişletildi** — PC'de _MAX_HIST_CHARS 6000 → 12000 (v4.5)
- **Offline model yükleme** — local_files_only=True, HF Hub'a gereksiz istek yok (v4.5)
- **Sampling tabanlı decoding** — greedy yerine T=0.55/top_p=0.9; eval 16/16 korundu, kalıplaşma azaldı (v4.6)
- **Sistem prompt'unda birebir kalıplar yapısal yönergeye çevrildi** (v4.6)
- **STT VRAM-aware cihaz seçimi** — toplam VRAM <8 GB ise CPU int8 (PC 5.64 GB), aksi halde CUDA float16 (Jetson 16 GB hedefi) (v4.6)
- **Conversation hold** — yanıt sonrası 10s wake word'süz dinleme penceresi; doğal sohbet akışı (v4.7)
- **Fiyat bağlam kuralı** — fiyat sadece müşteri sorduğunda / sipariş onayında / hesapta söylenir (v4.7, v4.8'de TL kelimesi yasağıyla sertleştirildi)
- **Kısa yanıt zorlaması** — max_tokens 80→50, "1 cümle 20 kelime" prompt kuralı, top_k=40, rep_pen 1.15→1.2 (v4.8)
- **Karşılama örnekleri kaldırıldı** — model artık örnek kopyalamıyor, gerçek varyasyon üretiyor (v4.8)
- **Offline mod doğrulandı** — `HF_HUB_OFFLINE=1` + `local_files_only=True` ile ağ erişimi gerekmiyor; "Loading weights" mesajı sadece disk cache'den okuma progress bar'ıdır (v4.8)

### Çözülen Sorunlar

**W11 — Hesap tetikleyici hatası (✅ v4.9):** "Başka bir şey istemiyorum" gibi kapanış cümlelerinde bot bazen hesap istenmedeyken "Toplam X TL" söylüyordu. `_is_bill_request()` gereğinden geniş eşleşiyordu. Çözüm: "BU DURUMDA TOPLAM SÖYLEME" + ara toplam ayrı kural olarak eklendi; farewell ve bill request tetikleyicileri birbirinden ayrıldı.

**W12 — Robotik ton (✅ v4.9):** Sistem promptu kural listesi biçimindeydi; model doğru kurallara uysa da cevaplar soğuk ve mekanikti. Çözüm: persona paragrafı ("sıcakkanlı, güler yüzlü Türk garson"), "Harika seçim!" benzeri kısa olumlu kabul örnekleri, max_tokens 50→65 (ton için biraz daha yer), kalıp örnekleri kaldırıldı.

### Tamamlananlar (Ek — 7 Haziran 2026)
- ✅ USB ses adaptörü temin edildi (card 3 USB Audio Device)
- ✅ Jetson uçtan uca demo: wake word → STT → LLM → TTS → hoparlör
- ✅ wbot_v3 GGUF Jetson'a deploy edildi (`/home/emk/models/`)
- ✅ Whisper medium CUDA Jetson'da aktif (1.7s latency)
- ✅ 32-senaryo eval: 30/32 (%93, `eval_gguf.py`)
- ✅ 3 bug fix: hesap toplam override, karşılama soru işareti, hesap keyword ("hesap" yalın)
- ✅ Geliştirme ortamı Windows 11 WSL2'ye taşındı (18 Haziran 2026)
- ✅ WSL2 kurulumu tamamlandı — PyTorch CUDA, faster-whisper, llama-cpp-python (GPU), Piper TTS model (24 Haziran 2026)
- ✅ Jetson SSH kuruldu — 192.168.1.65 (USB device mode üzerinden)
- ✅ 32-senaryo eval güncellendi: 31/32 (%96) — E21 artık geçiyor, yalnızca E19 kaldı (22 Haziran 2026)

### Bekleyen ⏳
| Görev | Not |
|-------|-----|
| E19 post-processing fix | Açıklama yanıtı "?" ile bitmiyorsa "Getireyim mi?" ekle (kod değişikliği) |
| Gürültülü ortam testi | Restoran müziği + kalabalık ortamda wake word + STT kalitesi |
| wbot_v4 eğitimi | `wbot_v4_train.jsonl` hazır (3605 kayıt — A paketi 490 + B paketi 115), Colab A100, 3 epoch → GGUF → Jetson deploy → %95+ hedef |

---

## 13. Fine-Tuning Metodolojisi (wbot_v1 / wbot_v2 / wbot_v3)

### Neden Fine-Tune?

Qwen3-4B base modeli Türkçe biliyor ancak restoran garson rolüne uygun davranışları (fiyat kuralları, "Getireyim mi?" yasağı, 2 cümle/25 kelime sınırı, "siz" formu) prompt mühendisliği ile kısmen öğrenebiliyor. Fine-tune bu kuralları model ağırlıklarına işleyerek:
- Kısa sistem promptuyla yüksek doğruluk elde etmeyi sağlar (Jetson'da token bütçesi kritik)
- Prompt'un görülmediği / yarı-görüldüğü edge case'lerde de tutarlı davranış üretir

### Yöntem: QLoRA (Quantized LoRA)

```
Base model (Qwen3-4B, NF4 4-bit)
    │
    ├── Ağırlıklar dondurulur (gradient hesaplanmaz)
    │
    └── LoRA adapter (r=32, α=64) eklenir:
            q_proj, k_proj, v_proj, o_proj    ← attention
            gate_proj, up_proj, down_proj     ← FFN
```

- **NF4 4-bit quantization:** Model ~2.37 GB VRAM'de tutulur (Colab T4 16 GB'a sığar)
- **LoRA r=32, α=64:** Eğitilebilir parametre sayısı toplam parametrelerin ~%1'i
- **paged_adamw_8bit:** Optimizer state'leri CPU RAM'de tutulur, GPU baskısı düşer
- **Completion-only SFT:** System + user tokenları -100 ile maskelenir, yalnızca assistant tokenlarında loss hesaplanır

### Dataset Formatı

Her kayıt tam bir konuşmayı içerir. Tek turlu ve çok turlu karışık:

```json
{"messages": [
  {"role": "system", "content": "...~2092 tok uzun sistem promptu..."},
  {"role": "user",      "content": "Merhaba"},
  {"role": "assistant", "content": "Hoş geldiniz, çorba, ana yemek, tatlı ve içeceklerimizden ne arzu edersiniz?"},
  {"role": "user",      "content": "Bir mercimek çorbası istiyorum."},
  {"role": "assistant", "content": "Elbette, Mercimek Çorbası 85 TL. Başka bir şey alır mısınız?"}
]}
```

- Fiyatlar rakamla: `85 TL` (kelimeyle değil)
- Diyet/alerji soruları: `"Bu konuda bilgim yok, personelimize sorabilirsiniz."`
- "Getireyim mi?" sipariş onayında kesinlikle yok
- Tüm kayıtlarda aynı uzun sistem promptu — eğitim-inference tutarlılığı için

### wbot_v1 Sonuçları

| Parametre | Değer |
|-----------|-------|
| Eğitim verisi | 970 kayıt (A–H senaryoları) |
| Süre | ~2.6 saat (Colab T4, 1 epoch) |
| Train loss | 0.116 |
| Eval loss | 0.1275 |
| Eval (kısa prompt) | 12/14 (%85) — E02 ve E09 dataset boşluğu |
| Eval (tam prompt) | 20/20 (%100) |

### wbot_v2 Sonuçları (3 Haziran 2026) ✅

| Parametre | Değer |
|-----------|-------|
| Eğitim verisi | 2216 kayıt, 2 epoch, Colab A100-SXM4-40GB |
| Toplam adım | 500 (early stop tetiklenmedi — loss tüm eğitim boyunca düştü) |
| Formal eval (14 senaryo) | 12/14 (%85) |
| Kapsamlı eval (48 senaryo) | 38/45 (%84, test hataları düzeltilince) |
| Adapter | `Drive: garsonbot_runs/wbot_v2/adapter` (252 MB safetensors) |

### Dataset Denetim Metodolojisi (scripts/audit_dataset.py)

wbot_v2 sonuçları analiz edilince modelin %84'te takılmasının sebebi veri kirliliği olduğu anlaşıldı. Otomatik denetim şu kuralları kontrol eder:

- **Karşılama-4kategori:** Karşılama/genel menü yanıtında "çorba, ana yemek, tatlı, içecek" dördü birden geçmeli
- **Sipariş-başka:** Sipariş onayı yanıtında "başka" kelimesi zorunlu
- **Getireyim-mi yasağı:** Sipariş onayında "Getireyim mi?" geçmemeli
- **TL-yanlış bağlam:** Fiyat/sipariş/hesap dışı bağlamda `\btl\b` veya menü fiyatları geçmemeli
- **Yasak ifade:** "onaylandı/onaylanıyor/kaydedildi" geçmemeli
- **Hesap-toplam:** Hesap yanıtında "toplam" geçmeli

**wbot_v2 denetim sonucu:** 883/2216 kayıt (%40) ihlalli — TL bağlam (618), başka eksik (353), karşılama (97), hesap (50), getireyim mi (4).

### wbot_v3 Dataset (4 Haziran 2026) ✅

**Strateji (revize edildi):** Audit scripti düzeltmesiyle 883 → 21 gerçek ihlal; 1333 → 2195 temiz base.
Yalnızca 805 yeni örnek üretmek yetti.

**Üretim yöntemi:** Her kategori için Python scripti (gen_*.py), her script ilk çalıştırmada 0 ihlal.

| Kategori | Script | Kayıt | Önemli Audit Kuralı |
|---------|--------|-------|---------------------|
| Karşılama | gen_karsilama.py | 200 | GREET_BOT 4 kategori |
| Sipariş-başka | gen_siparis_baska.py | 150 | `_is_specific_order_turn` → başka |
| Hesap | gen_hesap.py | 100 | `_is_bill_turn` → "toplam" |
| Çok turlu | gen_cotturlu.py | 150 | MID_QA: TL yasak, food token safe |
| İptal/takas | gen_iptal.py | 100 | CANCEL_TRIGGER → başka gerekmez; SWAP_TRIGGER → başka zorunlu |
| Öneri | gen_oneri.py | 105 | `_is_valid_price_context`=False → TL yasak |

**Final:** `wbot_v3_train.jsonl` — 3000 kayıt, 0 audit ihlali.
**Hedef:** 48 senaryo testinde %95+ PASS.
**Sonraki:** GGUF dönüşümü + Jetson deploy.

Detaylı dağılım: `PROJE_DURUMU.md` → Fine-Tuning Altyapısı → wbot_v3 bölümü.

### wbot_v3 Eğitim Sonuçları (4 Haziran 2026) ✅

| Parametre | Değer |
|-----------|-------|
| Toplam adım | 676 (2 epoch, eff_batch=8) |
| Train loss | 0.2304 |
| Eval loss | 0.1993 |
| Formal eval kısa prompt | 11/14 (%78) — E03, E08, E11 |
| Formal eval tam prompt | 13/14 (%92) — yalnızca E08 (eval tasarım sorunu) |

**E08 neden sayılmıyor:** Eval "toplam" bekliyor; gerçek sistemde OrderTracker `[Gerçek toplam: X TL]` enjekte eder. Eval bunu simüle etmiyor — deployment'ta model doğru çalışıyor.

**Sonraki adımlar:** 48 senaryo eval (Colab) → GGUF dönüşümü → Jetson deploy → wbot_v4 dataset planı.

---

## 14. Çoklu Dil — Değerlendirilen Alternatifler (karar verilmedi)

26 Haziran 2026 toplantısında (toplanti.md madde 4) çoklu dil desteği için üç
alternatif tartışıldı, **hiçbiri seçilmedi**. Faz 1 pratikte **sadece Türkçe**
kalır; çoklu dil Faz 2'ye işaretlendi.

| # | Alternatif | Mantık | Açık sorun |
|---|-----------|--------|-----------|
| 1 | **Dil algıla + model switch** | Her dil için ayrı küçük model; dil değişimi algılanınca modeli yükleyip geç | Model yükleme süresi gecikme yaratıyor |
| 2 | **Sabit bekletme mesajı** | "Dil değişikliği için lütfen bekleyiniz" + 5-30 sn bekleme, sonra ilgili dil modeli | Uzun ve sabit bekleme; UX zayıf |
| 3 | **Çeviri tabanlı yönlendirme** | Yabancı dildeki isteği anlayıp arka planda bir görevliye/panele ilet | Sistemde "garson" kavramı yok (sadece robot+müşteri); net değil, muhtemelen POS yönlendirmesi |

**Neden henüz reddedilmedi/seçilmedi:** Offline + küçük model kısıtı nedeniyle çoklu
dil eklemek **Türkçe odaklı eğitim kalite kaybı riski** taşıyor. Karar bir sonraki
karar toplantısına bırakıldı. Şimdilik **kod değişikliği önerilmiyor**.

---

## 15. Sürekli Öğrenme / Saha Logları — Gelecek Vizyon (internet bağlı senaryo)

26 Haziran 2026 toplantısında (toplanti.md madde 7) konuşulan uzun vadeli vizyon:
saha kullanımından **log toplama**, beğenilmeyen cevapların geri bildirimle
iletilmesi ve bu verilerle **sunucuda periyodik model güncellemesi** (robotun pasif
olduğu anlarda).

- **Geçerlilik:** Yalnızca **internet bağlantısı olan** senaryolar için. Mevcut
  offline mimariyle doğrudan ilgili değil.
- **İşaret:** Mevcut manuel wbot_v4/v5 döngüsünün (Colab eğitimi → GGUF dönüşümü →
  Jetson deploy) gelecekte **yarı-otomatik bir pipeline'a** dönüşmesi gerektiğine
  işaret ediyor.
- **Durum:** Şimdilik somut görev üretilmiyor; **gelecek vizyon notu** olarak
  kaydedildi. Mevcut manuel süreç yeterli.
