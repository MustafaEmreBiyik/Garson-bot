# Persona / Ton — Offline Fizibilite ve CPU Bütçesi Planı

**Tarih:** 26 Haziran 2026
**Bağlam:** Ekip/işletme, asistanın (1) **daha sıcak tonda** konuşmasını, (2) **normal
insan gibi problemsiz sohbet** etmesini, (3) müşteriyi "her duruma sebep olabilecek"
biri varsayıp **her şeye hazır** olmasını istiyor. Soru: **offline donanımımız (Jetson
Orin NX 16GB) ve mevcut yığın bunu kaldırır mı?** Ek kısıt: robota bağlandığında **ROS
tarafı CPU'yu yoğun kullanıyor** (navigasyon/SLAM/Nav2) — AI tarafının CPU ayak izini
bilmemiz ve sınırlamamız gerekiyor.

İlgili: [PROJE_DURUMU.md](PROJE_DURUMU.md) Faz 1/Faz 2 Ses-AI planı · [acil.md](acil.md)
(menü-dışı/düşük-güven guard'ları) · [toplanti.md](toplanti.md) madde 2, 5, 6.

---

## 1. Üç Talep → Offline Fizibilite Verdict

| Talep | Verdict | Gerekçe |
|-------|---------|---------|
| **Sıcak ton — metin** | ✅ Çözülmüş | Qwen3-4B offline sıcak Türkçe üretiyor (W12/v4.9 persona paragrafı). |
| **Sıcak ton — ses** | ⚠️ Darboğaz | Piper robotik. Offline çözüm: XTTS-v2/Fish-Speech ses klonlama (Jetson kaldırır, bedeli latency+VRAM). Bölüm 2. |
| **Doğal/problemsiz sohbet** | ✅ Domain-içi mümkün, ⚠️ açık-uçlu sınırlı | 4B + offline restoran-içi sıcak sohbet yapar; tam açık-uçlu (her konu) yapamaz. Asıl zayıf halka **STT** (gürültüde yanlış duyma). Bölüm 3. |
| **Her duruma hazır ("salak müşteri")** | ✅ Güvenli yapılabilir, ❌ "her şeyi çözer" değil | Güvenlik mühendisliği: guard + anti-kaos dataset + fallback. Hedef: **asla uydurmaz/rezil olmaz**, omniscient değil. Bölüm 3. |

**Tek cümle:** Donanım yeterli. Soru "yapabilir miyiz" değil — **"latency ve CPU
bütçesini nereye harcarız."**

---

## 2. TTS Sıcaklık — XTTS / Fish-Speech Jetson Pilotu

**Hedef:** Piper'ı sıcak, klonlanmış bir Türkçe sesle değiştir; offline kal.

**Adımlar:**
1. **Motor seç (lisans kritik):**
   - **XTTS-v2** — Türkçe + zero-shot klonlama, kaliteli. ⚠️ Coqui Public Model License =
     **ticari kullanıma kapalı** → ürün için risk. Sadece prototip/değerlendirme.
   - **Fish-Speech / OpenAudio** — çok dilli + klonlama, expresif. ⚠️ **DÜZELTME
     (bkz. [TTS_LISANS_ARASTIRMASI.md](TTS_LISANS_ARASTIRMASI.md)):** açık ağırlıklar
     **CC-BY-NC-SA = ticari DEĞİL**; ticari kullanım fish.audio ücretli lisansını
     gerektirir. Bedava+offline+ticari için **kendi sesinle kendi modelini eğitme**
     yolu (Piper/VITS/StyleTTS2 — kod lisansı serbest) tercih edilmeli.
2. **Referans ses kaydı:** Sıcak/samimi bir insan sesinden 15-30 sn temiz Türkçe →
   persona sesi olarak klonla. (Toplantının "2-3 örnek ses onayı" aksiyonu.)
3. **Entegrasyon (drop-in):** `tts.py`'ye mevcut `PiperTTS` arayüzünü taklit eden bir
   `XttsTTS`/`FishTTS` sınıfı (`async synthesize() -> bytes`, `AUDIO_CONTENT_TYPE`).
   `demo_usb.py` zaten `tts.synthesize()` üzerinden konuşuyor → tek satır değişiklik.
   **Piper fallback olarak kalır** (motor yüklenemezse).
4. **Jetson'da ölç:** ilk-cümle latency, cümle başına RTF, **VRAM artışı**, **CPU farkı**
   (Piper'a göre **düşmeli** — Bölüm 5).
5. **A/B onayı:** Aynı karşılama cümlesini Piper / XTTS-klon / edge-tts Emel (/ ops.
   ElevenLabs) ile seslendirip ekibe/patrona dinlet → seç.

**VRAM gerçeği (16GB):** LLM ~2.4GB + Whisper medium ~2-3GB + XTTS ~2-4GB ≈ ~9GB → **sığar.**
Sınır VRAM değil, **latency** (Bölüm 4).

---

## 3. wbot_v4 — Sıcak Small-Talk + Anti-Kaos Dataset Kapsamı

Mevcut wbot_v4 planına (PROJE_DURUMU) **iki yeni eksen** eklenir:

| Kategori | Amaç | Örnek davranış |
|----------|------|----------------|
| **Sıcak small-talk** | "Normal insan gibi sohbet" — selamlaşma ötesi | "Nasılsınız?" / "Yoğun musunuz?" / iltifat → kısa içten cevap + nazikçe menüye dön. Açık-uçlu değil, **sınırlı sıcak.** |
| **Anti-kaos / saçma girdi** | "Her duruma hazır" güvenliği | Menü-dışı sipariş ("Adana getir"), anlamsız STT, şaka/provokasyon → **güvenli fallback**, asla ürün uydurma. |
| **Anti-halüsinasyon** | Menüde olmayan detay uydurmama | (wbot_v4'te zaten planlı) |

**Tasarım kararı (netleştir):** Mevcut sistem konu-dışını **reddediyor**. Boss "insan
gibi sohbet" isteyince bu **bilinçli kapsam genişletmesi** olur: tam açık-uçlu değil,
**sıcak small-talk + nazik yönlendirme**. Dataset bu çizgiyi öğretmeli. Üretim:
`gen_*.py` deseni + `audit_dataset.py` doğrulaması (mevcut iş akışı).

---

## 4. Latency Hedefleri

Toplantı: rutin sorularda "5 sn kabul değil"; düşünce gerektiren sorularda bekleme tamam.
**Uzlaştırıcı: fast-path (Faz 1 #1)** — basit intent anında, ağır yol sadece açık-uçluda.

| Yol | İlk ses hedefi | Nasıl |
|-----|---------------|-------|
| **Rutin (fast-path)** | < ~1.5 sn | Template/kısa max_tokens, ağır TTS atlanabilir |
| **Açık-uçlu (LLM + sıcak TTS)** | < ~3-3.5 sn | Streaming pipeline + XTTS ilk cümle |
| **XTTS ilk-cümle** | < ~1.5 sn (ölçülmeli) | Piper ~0.6sn'den artış kabul, sıcaklık karşılığı |

---

## 5. CPU Bütçesi ve ROS Eş-Yaşam

> **Neden önemli:** Robota bağlanınca ROS (Nav2/SLAM) CPU-yoğun — haritalama sırasında
> tüm çekirdekleri %100 kullanabiliyor (toplanti.md md.6). Tasarım: **GPU+RAM → AI,
> CPU → ROS**, robot durumuna göre zaman paylaşımı. AI tarafının CPU ayak izini
> **bilmemiz ve sınırlamamız** gerek. Jetson Orin NX 16GB = **8× ARM Cortex-A78AE**.

### 5.1 Mevcut CPU tüketicileri (kod-temelli analiz)

| Bileşen | CPU yükü | Ne zaman | Not |
|---------|----------|----------|-----|
| **Piper TTS** | 🔴 Yüksek (burst) | Her yanıt, cümle başına ~0.5-0.8s | **Tamamen CPU** subprocess. AI tarafının en büyük CPU patlaması. |
| **openWakeWord** | 🟠 Düşük-orta, **sürekli** | Boşta "hey garson" dinlerken (her 80ms) | onnxruntime **CPU** (GPU discovery başarısız). Always-on. |
| **llama.cpp host thread'leri** | 🟠 Orta (burst) | Üretim sırasında | `n_gpu_layers=-1` ama `n_threads` **ayarsız** → tüm çekirdekleri alır ([llama_cpp_backend.py:135](robot_waiter_ai/inference/llama_cpp_backend.py#L135)). Ayarlanabilir kol. |
| **Whisper STT** | 🟢 Düşük (GPU'da) | Kayıt sonrası | Jetson'da CTranslate2 **CUDA**; feature extraction CPU'da hafif. (CPU fallback olursa 🔴) |
| **webrtcvad + np.interp** | 🟢 Düşük | Kayıt sırasında | Resampling 48k→16k. |
| **aplay / asyncio** | 🟢 Çok düşük | — | — |

**Sıralama:** Piper TTS > openWakeWord (sürekli) > llama.cpp thread'leri > diğerleri.

### 5.2 Ölçüm planı (Jetson'da çalıştır)

```bash
# 1) En iyi: jetson-stats (per-core CPU + GPU + RAM + güç, tek ekran)
sudo pip3 install -U jetson-stats   # sonra reboot
jtop

# 2) Yerleşik: tegrastats — per-core CPU%, GPU%, RAM, log'lanabilir
tegrastats --interval 1000 | tee /tmp/tegrastats.log
# demo'yu ayrı terminalde çalıştırırken aşama aşama (boşta / wake / STT / LLM / TTS) izle

# 3) Klasik per-core
htop   # veya: top -1

# 4) Aşama-bazlı atıf (kod içi, opsiyonel) — psutil ile:
#    psutil.cpu_percent(percpu=True) değerlerini wake/record/STT/LLM/TTS
#    sınırlarında logla → hangi aşama hangi çekirdeği yiyor net görülür.
```

**Çıktı:** İki sayı isteriz — **(a) boşta** (sadece wake word dinlerken) toplam CPU%,
**(b) yanıt verirken** tepe CPU%. (a) sürekli olduğu için ROS ile asıl çakışan budur.

### 5.3 Azaltma kolları (AI'nın CPU'sunu ROS'a bırak)

1. **🟢 Piper → XTTS/Fish (GPU):** En büyük AI CPU patlamasını **CPU'dan GPU'ya taşır**.
   → Persona yükseltmesi (Bölüm 2) ve CPU-bütçesi **aynı yöne çalışıyor.** Kazan-kazan.
2. **🟢 llama.cpp `n_threads` sınırla:** `Llama(..., n_threads=2)` gibi — hesap zaten
   GPU'da, CPU thread'lerini kısmak ROS'a çekirdek bırakır, latency'e az dokunur.
3. **🟢 Durum-kapılı wake word (Faz 1 AI↔ROS arayüzü):** Robot **hareket ederken** AI
   döngüsü + wake word **tamamen duraklatılır** → navigasyonda AI CPU'su ~0; tam da ROS
   tüm çekirdekleri istediği an. Robot **durunca** AI aktif, ROS boşta. Bu **temel
   eş-yaşam mekanizması** — zaten Faz 1 planında (ROS "hareket ediyorum/durdum" sinyali).
4. **🟡 Çekirdek izolasyonu (gerekirse):** `taskset`/cgroups ile AI thread'lerini birkaç
   çekirdeğe pinle, kalanı ROS'a. Zaman-paylaşımı (#3) genelde daha basit ve yeterli.

### 5.4 CPU hedefleri (ölçüm sonrası netleşir)

- **Navigasyon (robot hareket halinde):** AI CPU ≈ **0%** (durum-kapılı kapatma). ROS
  serbest. ← en kritik kısıt.
- **Konuşma (robot durmuş):** AI CPU patlamaları **kabul** — bu anda ROS boşta.
- **Boşta (masada, dinliyor):** wake word'ün sürekli CPU'su **1 çekirdeğin altında**
  hedeflenir; gerekirse #2/#4 ile sınırlanır.

---

## 6. Önerilen Sıra ve Karar Noktaları

**Sıra:**
1. **CPU/GPU taban ölçümü** (Bölüm 5.2) — Jetson'da boşta + yanıt CPU/VRAM rakamlarını al.
2. **TTS pilotu** (Bölüm 2) — Fish/XTTS klon, latency + CPU farkını ölç (CPU **düşmeli**).
3. **wbot_v4 small-talk + anti-kaos** (Bölüm 3) dataset üretimi.
4. **Durum-kapılı wake word + n_threads** (Bölüm 5.3 #2,#3) — ROS eş-yaşam.
5. **Fast-path** (latency koruması) → A/B ses onayı → karar.

**Açık karar noktaları (işletme/ekip):**
- Ticari lisans şart mı? → XTTS'i eler, **Fish/OpenAudio**'ya yönlendirir.
- "İnsan gibi sohbet" ne kadar açık-uçlu? → **sınırlı sıcak small-talk** öneriyoruz
  (tam açık-uçlu 4B offline'da güvenilmez).
- Latency tavanı: rutin < ~1.5sn, açık-uçlu < ~3.5sn kabul mü?

---

## 7. Doğrulama

1. **CPU/VRAM:** `tegrastats`/`jtop` ile boşta + yanıt rakamları; TTS pilotu sonrası
   CPU'nun düştüğü, VRAM'in 16GB içinde kaldığı teyit.
2. **Latency:** demo'daki `STT`/`LLM+TTS` ms ölçümleri hedeflerin altında mı.
3. **Ses kalitesi:** A/B kör dinleme — ekip "sıcak/samimi" onayı.
4. **Robustluk:** anti-kaos senaryoları (`eval_gguf.py` yeni kategori) + acil.md
   guard'ları → asla ürün uydurmuyor, her girdide nazik fallback var.
5. **ROS eş-yaşam:** robot hareket ederken AI CPU ≈ 0 (durum-kapılı kapatma çalışıyor mu).
