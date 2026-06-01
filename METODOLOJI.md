# W-BOT Metodoloji Belgesi

**Proje:** Türkçe Konuşan Restoran Garson Robotu (W-BOT)
**Tarih:** 1 Haziran 2026 (v4.5)
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

### Kullanılan Teknoloji: faster-whisper (Whisper medium)
OpenAI'ın Whisper modelinin CTranslate2 motoruyla optimize edilmiş versiyonu.

### Model Seçimi

| Model | Parametre | Kalite | Jetson GPU Süresi |
|-------|-----------|--------|-------------------|
| tiny | 39M | Düşük — Türkçe restoran kelimelerini kaçırıyor | ~200ms |
| small | 244M | İyi — restoran ortamı için yeterli | ~850ms |
| **medium** | 769M | **Çok iyi — Türkçe kalitesi belirgin yüksek** | **~1500-2000ms** |

v4.5'te `small`'dan `medium`'a geçildi: gürültülü restoran ortamında Türkçe menü kelimelerini daha güvenilir tanıması için. Latency artışı (~600-900ms) sesli yanıt başlamadan önce yaşandığından kullanıcıya etkisi minimumdur.

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
- Genel menü sorusunda kategori özeti: "Çorbalar, ana yemekler, tatlılar ve içecekler var. Ne istersiniz?"
- **Öneri/tavsiye sorusunda** ("ne önerirsin/ne yesem/ne alsam" gibi): 1-2 popüler ürün isim+fiyatla önerilir — jenerik kategoriye gidilmez (v4.5)
- Sipariş onay formatı: "Elbette, [ürün] [fiyat] TL eklendi."
- Toplam yalnızca hesap istenince söylenir
- Vejetaryen/allerjen sorusu için menü etiketlerini kullan

### Thinking Modunu Kapatma
Qwen3 modeli varsayılan olarak yanıttan önce uzun bir iç akıl yürütme (`<think>...</think>`) bloğu üretir. Bu blok 100-300 token uzunluğunda olabilir ve yanıt gecikmesini ciddi şekilde artırır. Restorant senaryosunda hızlı yanıt gerektiğinden bu mod kapatıldı:

```python
# llama_cpp_backend — format_prompt içinde:
parts.append("<|im_start|>assistant\n<think>\n\n</think>\n\n")
# Boş think bloğu → model düşünmeden yanıta geçer

# qwen3_backend — apply_chat_template içinde:
enable_thinking=False
```

### Konuşma Geçmişi Yönetimi
Jetson'da bağlam penceresi (n_ctx) 1536 token ile sınırlıdır. Sistem prompt (~944 token) + max yanıt (80 token) = ~512 token konuşma geçmişi için kalır. Bu ~5-6 tura karşılık gelir.

`_trim_history()` fonksiyonu toplam geçmiş boyutu eşiği aşınca en eski user+assistant çiftini siler:

```python
_MAX_HIST_CHARS = 1400  # Jetson: karakter cinsinden (~350 token)
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
| **Prompt v4.1 (mevcut)** | **16/16 (%100)** |

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
| STT latency (CUDA float16, medium) | ~1500-2000ms |
| TTS sentez (Piper, CPU) | ~500-800ms |
| **Müşteriye ilk ses (TTFA)** | **~2.2-2.7 saniye** |
| LLM eval başarı | 16/16 (%100) |

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

### Bekleyen ⏳
| Görev | Engel |
|-------|-------|
| Hoparlörden ses çıkışı | USB ses adaptörü (~100 TL) gerekiyor |
| Uçtan uca tam demo | Ses adaptörüne bağlı |
| Gürültülü ortam testi (restoran müziği + kalabalık) | Ses adaptörü gerekiyor |
| Whisper medium kalite doğrulaması | Gerçek konuşma kaydı gerekiyor |
| VRAM kullanımı ölçümü (Ubuntu PC, Qwen3-4B) | Sonraki çalıştırmada ekrana basılacak |
