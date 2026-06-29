# ACİL — W-BOT Jetson Demo: Sorun Analizi ve Düzeltme Rehberi

> Oturum: 24-25 Haziran 2026, Jetson Orin NX (16GB). Demo **çalışıyor**;
> bu belge gözlemlenen sorunları ve çözümlerini sıralar.

## Durum Özeti
Pipeline baştan sona çalıştı: **wake word ("hey garson") → mikrofon → Whisper
medium (CUDA) → Qwen3-4B GGUF (GPU) → Piper TTS → USB hoparlör.** Sesli yanıt
alındı, sipariş tespiti doğru çalıştı (Mercimek Çorbası 85 TL, Et Döner 280 TL).

Donanım:
- 🎙 Mikrofon: C-Media **"USB PnP Sound Device"** — `_find_input_device()` ile
  isimle bulunuyor, kart numarasından bağımsız → sağlam.
- 🔊 Hoparlör: GeneralPlus **"USB Audio Device"** — kart numarası değişken (0 ↔ 1).

---

## 🔴 P0 — ALSA çıkış kart numarası kayması (KRİTİK)

**Belirti**
```
aplay: main:831: audio open error: No such file or directory
WARNING demo_usb: Karşılama TTS hatası: Command '['aplay','-q','-D','plughw:0,0',...]'
returned non-zero exit status 1.
```
TTS hiç ses çıkarmadı; karşılama ve tüm yanıtlar sessiz kaldı.

**Kök neden**
USB ses cihazlarının ALSA kart numaraları her fiş çıkar-tak / boot'ta değişebiliyor:
- Başta: card 0 = hoparlör (GeneralPlus), card 1 = mikrofon (C-Media)
- Replug sonrası: card 0 = mikrofon, card 1 = hoparlör (**yer değiştirdi**)

`scripts/demo_usb.py:82` çıkışı SABİT yazıyor: `ALSA_OUTPUT_DEVICE = "plughw:0,0"`.
Kart değişince yanlış cihaza (mikrofona) çalmaya çalışıp patlıyor. Mikrofon
`_find_input_device()` ile **isimle** bulunduğu için etkilenmiyor — çözüm aynısını
çıkış için yapmak.

**Geçici çözüm (bu oturumda uygulandı)**
```bash
sed -i 's/plughw:0,0/plughw:1,0/' scripts/demo_usb.py
```
Çalışır ama bir sonraki replug/boot'ta yine kırılır. **KALICI DEĞİL.**

**Kalıcı çözüm (önerilen) — çıkışı isimle oto-tespit**
`scripts/demo_usb.py` içine, `_find_input_device()` yanına ekle:
```python
import re as _re

def _find_output_device() -> str | None:
    """USB hoparlörün aplay cihaz string'ini ('plughw:X,Y') döndür.

    sounddevice isimleri '(hw:KART,CİHAZ)' içerir. "USB Audio" geçen ama "PnP"
    geçmeyen (= GeneralPlus hoparlör) ve çıkış kanalı olan cihazı bul, kart
    numarasını isimden çıkar. Bulamazsa None (sistem varsayılanı).
    """
    for d in sd.query_devices():
        name = d["name"]
        if "USB Audio" in name and "PnP" not in name and d["max_output_channels"] > 0:
            m = _re.search(r"hw:(\d+),(\d+)", name)
            if m:
                return f"plughw:{m.group(1)},{m.group(2)}"
    return None
```
`run_demo()` başında, mikrofon tespitinden hemen sonra (~satır 669):
```python
global ALSA_OUTPUT_DEVICE
_out = _find_output_device()
if _out:
    ALSA_OUTPUT_DEVICE = _out
    print(f"Hoparlör: {_out}")
else:
    print(f"Hoparlör: varsayılan ({ALSA_OUTPUT_DEVICE})")
```
`ALSA_OUTPUT_DEVICE` modül-seviyesi global; `_play_wav` bunu okur, `global` ile
güncellemek yeterli. Satır 82 varsayılan olarak kalabilir (oto-tespit üzerine yazar).

**Alternatif (kodsuz):** `~/.asoundrc` veya udev kuralıyla USB cihaza sabit kart
indeksi atanabilir; ama kod tarafı daha temiz ve taşınabilir.

---

## 🟠 P1 — STT (Whisper) Türkçe yanlış tanıma

**Belirti (loglardan)**
- "Anı emek olarak ne ölüsün?" (→ "ana yemek olarak ne var?")
- "Hatlı." (→ muhtemelen "tamam")
- "Ne emekler sen ya, ne emekler." / "Çorba gibi an yemekleri bir sersene."

**Kök neden**
Gürültülü ortam + C-Media USB mikrofon kalitesi + kısa/yarım cümleler. demo_usb.py
kendi webrtcvad'ı ile kaydediyor (`VAD_SILENCE_S=1.5`), ardından faster-whisper
tekrar `vad_filter` uyguluyor → çift VAD bazen cümleyi erken kesiyor. Yanlış metin
LLM'i de yanlış yönlendiriyor (aşağıdaki P1-LLM).

**Çözümler**
1. **faster-whisper kalite parametreleri** — `robot_waiter_ai/speech/stt.py`,
   `_run_transcribe` (~satır 223). Greedy yerine beam + belirleyici örnekleme:
   ```python
   segs_gen, info = self._model.transcribe(
       tmp_path,
       language=language,
       initial_prompt=initial_prompt,
       vad_filter=vad_enabled,
       vad_parameters={"min_silence_duration_ms": _VAD_MIN_SILENCE_MS},
       beam_size=5,                       # daha doğru
       temperature=0.0,                   # halüsinasyon ↓
       condition_on_previous_text=False,  # önceki tur bozmasın
       word_timestamps=False,
   )
   ```
2. **initial_prompt zenginleştir** — `demo_usb.py:70` `STT_INITIAL_PROMPT`. Şu an
   sadece menü kelimeleri var; yaygın sipariş ifadeleri ekle: "ana yemek olarak ne
   var", "hesabı alabilir miyim", "bir tane", "porsiyon".
3. **VAD ayarı** — `demo_usb.py` `VAD_SILENCE_S` 1.5 → 1.8-2.0 (cümle ortasında
   kesmeyi azaltır; latency biraz artar). Çift VAD yerine faster-whisper tarafında
   `use_vad=False` ile sadece webrtcvad'a güvenmeyi de değerlendir.
4. **Donanım (en yüksek kazanç)** — mikrofonu konuşmacıya yakın konumlandır,
   ortam gürültüsünü azalt.
5. **(Opsiyonel) large-v3** — Jetson 16GB'da denenebilir; latency ↑ (medium ~1.7-2.2s).

---

## 🟠 P1 — LLM tekrarlı / bağlamsız yanıtlar

**Belirti**
- "Menümüzde çorba, ana yemek, tatlı ve içecek var. Hangisini tercih edersiniz?" —
  kullanıcı "ana yemekleri say" dese bile tekrarlanıyor.
- "Hatlı." (bozuk STT) → "Harika seçim! Mercimek Çorbası 85 TL" — kullanıcı et döner
  sipariş etmişken alakasız ürün halüsinasyonu.

**Kök neden**
Büyük ölçüde STT'nin bozuk girdisi: kategori adı "an yemek" gibi bozulunca sistem
promptundaki "kategori içeriği" kuralı tetiklenmiyor → genel kategori yanıtı.
Kısmen 4B modelin bağlam takibi sınırı. `repeat_penalty=1.2` var ama her tur ayrı
completion olduğu için tur-arası tekrarı engellemez.

**Çözümler**
1. **Önce STT'yi düzelt** (yukarıdaki P1-STT) — girdi temizse bu sorunların çoğu kaybolur.
2. **wbot_v4 dataset** (PROJE_DURUMU'da planlı) — bağlam takibi + anti-halüsinasyon
   örnekleriyle yeniden eğitim.
3. **repeat_penalty** 1.2 → 1.3 denenebilir (`llama_cpp_backend.py:186,211`); agresif
   olursa akıcılık bozulur.
4. **Hesap/sipariş takibi test EDİLMEDİ** — oturumda "hesap" denmedi; OrderTracker
   toplamı (örn. Et Döner 280 + Mercimek 85 = 365 TL) bir sonraki demoda "hesap
   lütfen" ile doğrulanmalı.

---

## 🟡 P2 — Yanıt gecikmesi (~8-10 sn)
**Belirti:** STT ~1.8-2.2s, LLM+TTS ~6-8s, toplam ~8-10s.
**Kök neden:** Piper TTS CPU'da (494-779ms/cümle); LLM 4B GGUF GPU'da. Cümle-cümle
streaming pipeline zaten var.
**Çözümler:** `max_tokens=65` zaten kısa (iyi). Piper GPU (onnxruntime-gpu) JetPack
R36'da pip'te yok — ertelenmiş. Demo için bloklayıcı değil; kabul edilebilir.

---

## 🟢 P3 — Log gürültüsü / kozmetik (bloklayıcı DEĞİL)
1. **torch CUDA "driver too old (found version 12060)"** — ZARARSIZ. Demo PyTorch'u
   GPU'da kullanmıyor (LLM=llama-cpp, STT=CTranslate2 kendi CUDA'ları). Sadece KV
   warm-up'taki opsiyonel `torch.cuda.empty_cache()` (`demo_usb.py:612-617`,
   try/except). İstersen o bloğu / torch import'unu kaldırarak sustur.
2. **onnxruntime "GPU device discovery failed"** — ZARARSIZ. openWakeWord ONNX CPU'da,
   wake word yüklendi.
3. **`n_ctx_seq (4096) < n_ctx_train (40960)`** — bilgilendirme; 4096 yeterli.
   İstersen `llama_cpp_backend.py:138` `n_ctx` artırılabilir (VRAM ↑).
4. **Ctrl+C'de KeyboardInterrupt traceback** (`threading._shutdown`) — kozmetik;
   `_speak_streaming` thread join + asyncio iptali temizlenebilir. Demo işlevini
   etkilemiyor.

---

## Öncelik Sırası
1. 🔴 **P0 ALSA oto-tespit** — `_find_output_device()`. Demo'yu replug/boot'a dayanıklı
   yapar. En yüksek değer, en küçük değişiklik.
2. 🟠 **P1 STT kalite** — beam_size/temperature/condition_on_previous_text +
   initial_prompt + mikrofon konumu.
3. 🟠 **P1 LLM** — STT düzelince yeniden değerlendir; wbot_v4 planı.
4. 🟡🟢 **P2/P3** — latency ve log temizliği (isteğe bağlı).

---

## Hızlı Komut Referansı
```bash
# Hangi kartta ne var?
aplay -l        # çıkış (hoparlör = "USB Audio Device")
arecord -l      # giriş (mikrofon = "USB PnP Sound Device")
cat /proc/asound/cards

# sounddevice'in gördüğü (oto-tespit bunu kullanır)
python3 -c "import sounddevice as sd; print(sd.query_devices())"

# Hoparlör testi (X = aplay -l'deki USB Audio Device kartı)
speaker-test -D plughw:X,0 -c 2 -t pink -l 1

# Mikrofon→hoparlör testi (Y = mik kartı, X = hoparlör kartı)
arecord -D plughw:Y,0 -d 3 -f S16_LE -r 48000 -c 1 /tmp/mic.wav && aplay -D plughw:X,0 /tmp/mic.wav

# Geçici düzeltme (kalıcı fix yoksa; X = doğru hoparlör kartı)
sed -i 's/plughw:[0-9],0/plughw:X,0/' scripts/demo_usb.py

# Demo
cd ~/Desktop/Garson-bot/Garson-bot
python3 scripts/demo_usb.py
```

## Jetson Ortam Notları
- Proje yolu (Jetson): `~/Desktop/Garson-bot/Garson-bot`. `.venv` YOK — sistem
  Python + `~/.local` paketleri. `source .venv/...` adımı atlanır.
- GGUF model: `/home/emk/models/Qwen3-4B-wbot_v3-Q4_K_M.gguf` (yoksa repo/models'e
  fallback — `llama_cpp_backend.py:18-26`).
- Bu oturumda Jetson'daki demo_usb.py'ye `sed` ile `plughw:1,0` yazıldı; Windows
  repo'su hâlâ `plughw:0,0`. Kalıcı fix uygulanınca Jetson'da
  `git checkout scripts/demo_usb.py` ile sed geri alınıp pull edilmeli.

---

# 2. Oturum Bulguları (25 Haziran 2026)

İkinci demo oturumu (kalıcı ALSA fix henüz uygulanmadı, ses `plughw:1,0` sed ile
çalışıyordu) yeni sorunlar ortaya çıkardı.

## 🔴 P1 — Menüde olmayan ürün siparişinde UYDURMA (en önemli yeni bulgu)
**Belirti**
```
Müşteri: Bana bir tane Adana getir, ama çok acılı olsun... ustaya söyle acayip acılı olsun.
W-BOT:   Elbette, Şalgam Suyu 50 TL. Başka bir şey alır mısınız?
```
Adana kebap menüde YOK; bot alakasız bir ürünü (Şalgam Suyu) sipariş olarak onayladı.

**Kök neden**
Sistem promptunda iki kural çakışıyor: "Menüde olmayan ürün → 'Bu konuda bilgim yok'"
(`llama_cpp_backend.py:55`) ile "Sipariş ('getir' geçiyorsa) → ürün adı + TL onay"
(`llama_cpp_backend.py:44`). Cümlede "getir" sipariş fiili olduğu için model sipariş
kuralını uyguluyor ama menüde eşleşme olmadığından rastgele bir ürün uyduruyor.
`OrderTracker` ise "Adana"yı eşleştiremediği için toplamı güncellemiyor (sessizce) —
yani LLM ile sipariş takibi bu noktada tutarsız.

**Çözümler**
1. **demo_usb.py guard (önerilen)** — `order_tracker.detect_order()` sonrası: cümlede
   sipariş fiili var (`_ORDER_VERBS`) AMA `_match_items()` hiçbir ürün döndürmediyse,
   LLM'e gitmeden ya da bağlam ekleyerek "Bu konuda bilgim yok, personelimize
   sorabilirsiniz." yanıtını ver. Mevcut yardımcılar: `_match_items`, `_ORDER_VERBS`,
   `_load_menu_lookup` (hepsi `scripts/demo_usb.py` içinde).
   ```python
   # order_tracker.detect_order(user_text) çağrısından sonra, _is_bill_request'ten önce:
   t_low = user_text.lower().replace('̇', '')
   if any(v in t_low for v in _ORDER_VERBS) and not _match_items(t_low, order_tracker._lookup):
       reply = "Bu konuda bilgim yok, personelimize sorabilirsiniz."
       await _speak(tts, reply, tts_active)
       # ... wake word'e dön / conversation_active = True
   ```
2. **Sistem promptu güçlendir** (`llama_cpp_backend.py:44/55`) — sipariş kuralına ekle:
   "Sipariş fiili olsa bile istenen ürün MENÜDE YOKSA başka ürün önerme/onaylama; SADECE
   'Bu konuda bilgim yok, personelimize sorabilirsiniz.' de."

## 🟠 P1 — STT gecikme sıçraması (8.4 sn)
**Belirti**
```
Müşteri: İçinşir.
  ⏱  STT: 8374ms       (normal ~1.8-2.2s; tur toplamı 14693ms)
```
**Kök neden** Kısa/gürültülü/anlamsız seste Whisper tekrar-halüsinasyon döngüsüne
girip uzun sürüyor.
**Çözümler** P1-STT'deki `temperature=0.0` + `condition_on_previous_text=False`
ayarları bunu da büyük ölçüde önler. Ek olarak `robot_waiter_ai/speech/stt.py`
`_run_transcribe`'a erken-eleme eşikleri: `compression_ratio_threshold=2.4`,
`log_prob_threshold=-1.0`, `no_speech_threshold=0.6`. Ayrıca `demo_usb.py` webrtcvad'ı
çok kısa segmentleri (örn. <0.4 sn konuşma) STT'ye hiç göndermesin.

## 🟠 P1 — Bozuk/kısa girdide istenmeyen sipariş onayı
**Belirti**
```
Müşteri: İçinşir.        → W-BOT: Elbette, Şalgam Suyu 50 TL. ...   (önceki turu tekrar)
Müşteri: İzlemiş.        → W-BOT: Tabii efendim, Kremalı Mantar Çorbası 95 TL. ...
Müşteri: Sorum anlamadın.→ W-BOT: Anladım, Kremalı Mantar Çorbası 95 TL. ...
```
**Kök neden** STT bozuk + düşük-güven kontrolü yok; LLM önceki bağlamı sürdürüp
uyduruyor.
**Çözüm** Düşük-güven guard (`demo_usb.py`, STT sonrası): `user_text` çok kısaysa
(örn. ≤2 kelime ve menü/komut kelimesi yok) veya `result["language_probability"]`
düşükse, LLM'e gitmeden "Tam anlayamadım, tekrar eder misiniz?" de. STT sonucu zaten
`language_probability` döndürüyor (`stt.py:247`).

## 🟢 İyi çalışanlar (2. oturum — pozitif gözlemler)
- **Konu dışı reddi:** "Havalar nasıl?" → "Benim alanım sipariş ve menü, bu konuda
  personelimize danışabilirsiniz." ✅ (hafif drift: "nasıl bir havadasın" → çorbaya
  bağladı, küçük sorun)
- **Kategori listeleme:** "Çorbaları sayar mısın?" → "Çorbada Mercimek ve Kremalı
  Mantar var. Hangisini tercih edersiniz?" ✅ (fiyat söylemedi, doğru)
- **Ürün açıklaması:** "Hangi mantarı kullanıyorsunuz?" → "taze dağ mantarı
  kullanılmaktadır." ✅

## Güncellenmiş Öncelik
1. 🔴 P0 ALSA oto-tespit (1. oturum) — hâlâ #1.
2. 🔴 P1 **Menü-dışı sipariş guard** (yeni) — yanlış ürün satışını önler, doğruluk kritik.
3. 🟠 P1 STT kalite + gecikme (beam/temperature/eşikler) — düşük-güven guard ile birlikte.
4. 🟠 P1 LLM bağlam/tekrar — STT düzelince yeniden değerlendir; wbot_v4.
```
