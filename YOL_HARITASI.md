# W-BOT — Ses/AI Konsolide Yol Haritası

**Tarih:** 28 Haziran 2026
**Amaç:** toplanti.md (26 Haz toplantı kararları) + acil.md (Jetson demo bulguları) +
persona/ton/lisans çalışmalarını **tek listede** birleştirmek. Patron istekleri →
somut, sıralı, dosya bazlı görevler. Yeni sohbette devam etmek için referans.

## İlke: "İyi garson" (her şeyi bilen sihirbaz değil)
Hedef: **çekirdek sağlam + sınırda zarif + sıcak ses + kısa konuş + kesilebilir.**
Offline kalır; bulut yalnızca yatırımcı demosu. "Her şeyi bilsin" değil, **"asla rezil
olmasın"**. Patron istekleri bu ilkeyle karşılanır.

## Kaynak dokümanlar (yeni sohbette önce bunları oku)
- **PROJE_DURUMU.md** — mimari, eval sonuçları, Faz 1/2 görevleri
- **METODOLOJI.md** — teknik kararlar; çoklu-dil (§14) ve sürekli-öğrenme (§15) notları
- **PERSONA_TON_FIZIBILITE.md** — ses/persona offline fizibilite + CPU/ROS eş-yaşam
- **TTS_LISANS_ARASTIRMASI.md** — motor lisansları + maliyet/efor (Yol A vs B)
- **acil.md** — Jetson demo P0-P3 bulguları + hazır reçeteler
- **toplanti.md** — 26 Haz toplantı kararları

İşaretler: ✅ tamam · 🔄 devam · ⏳ bekliyor · Etiketler:
[DEĞİŞTİR]/[YENİ]/[VERİ]/[KARAR]/[DONANIM]/[SÜREÇ]

---

## 🟢 1. DALGA — Şimdi, PC'de (deneyim sağlamlığı; donanımsız)
En yüksek ROI. Patronun "kötü cevap / uzatma / hazır değil" şikayetlerini **kökten**
çözer. Hepsi PC'de `qwen3_backend` ile geliştirilip test edilebilir.

- [x] ✅ [DEĞİŞTİR] **Kısa konuşma kuralı** — kelime limiti 25→20, "hesap/veda/afiyet hariç yanıt soruyla bitmeli" kuralı eklendi. `llama_cpp_backend.py` + `qwen3_backend.py` · *toplanti md.2*
- [x] ✅ [SÜREÇ] **Hata triyaj şablonu** — `HATA_TRIYAJ.md` oluşturuldu: form, doldurulmuş örnekler, backlog tablosu, karar ağacı. · *toplanti md.9 feedback*
- [x] ✅ [DEĞİŞTİR] **Menü-dışı sipariş guard** — sipariş fiili var ama `_match_items` boş → "Bu konuda bilgim yok, personelimize sorabilirsiniz." `demo_usb.py` · *acil P1 (2.oturum, Adana→Şalgam) + toplanti md.2* ⚠️ **Jetson'da test edilecek**
- [x] ✅ [DEĞİŞTİR] **Düşük-güven STT guard** — ≤2 kelime / düşük `language_probability` → "Tam anlayamadım, tekrar eder misiniz?" `demo_usb.py` · *acil P1 (2.oturum)* ⚠️ **Jetson'da test edilecek**
- [x] ✅ [DEĞİŞTİR] **STT kalite parametreleri** — `beam_size=5`, `temperature=0.0`, `condition_on_previous_text=False` + erken-eleme eşikleri (`stt.py`). `VAD_SILENCE_S` 1.5→1.8, `VAD_MIN_SPEECH_MS=400`, `STT_INITIAL_PROMPT` zenginleştirildi (`demo_usb.py`). · *acil P1 STT* ⚠️ **Jetson'da test edilecek**
- [x] ✅ [DEĞİŞTİR] **Anti-halüsinasyon prompt** — sipariş YOKSA "başka ürün önerme/uydurma, yanıtta ürün adı/fiyat geçmesin" eklendi; genel menü-dışı kural "benzer ürün önerme" yasağı ile güçlendirildi. `llama_cpp_backend.py` + `qwen3_backend.py` · *acil P1*
- [ ] ⏳ [VERİ] **wbot_v4 dataset** — sıcak small-talk + anti-kaos + **topladığımız gerçek hatalar** + W15 (açıklama+soru) + W16 (alerji+öneri) + anti-halüsinasyon. `gen_*.py` + `audit_dataset.py` · *toplanti md.2 + acil P1 LLM*
- [ ] ⏳ [YENİ] **Fast-path intent yönlendirme** — rutin intent (selam/onay/kapanış/hesap) template/kısa yol; açık uçlu LLM. `demo_usb.py` · *toplanti md.2 (hız segmentasyonu)*
- [ ] ⏳ [DEĞİŞTİR] **Açılış cümlesi `_greet()` tek nokta** — wake-word ve ileride ROS "geldim" aynı yeri çağırsın. `demo_usb.py` · *toplanti md.2/3*
- [x] ✅ [DEĞİŞTİR] **OrderTracker yapısal sipariş verisi** — `_items` dict (name→{price,qty}) + `items` property + bill'e döküm. `demo_usb.py` · *toplanti md.5* ⚠️ **Jetson'da test edilecek**
- [ ] (ops.) [DEĞİŞTİR] `repeat_penalty` 1.2→1.3 denemesi · *acil P1 LLM*

> **Not (zaten yapıldı):** E19 post-processing fix ✅ (`demo_usb.py`), persona METNİ ✅ (W12/v4.9).

---

## 🟡 2. DALGA — Ses kimliği (karar sonrası)
- [ ] ⏳ [KARAR] **Ses yönü: Yol A vs B** — A (kendi sesimizle offline eğit, ücretsiz/lisans temiz, ~1-2 hafta emek) vs B (Fish/ElevenLabs/Azure ücret + online). **Öneri: A.** · *TTS_LISANS_ARASTIRMASI*
- [ ] ⏳ [YENİ] **Yol A pilotu** — ekip üyesi referans kayıt + Piper/VITS Türkçe eğitim → ONNX → `tts.py`. (Adım adım liste hazır; ses hakkı için izin belgesi.)
- [ ] ⏳ [YENİ] **Per-cümle prozodi (duygu)** — kural-temelli: "Harika seçim!"→heyecanlı. Pipeline cümle cümle çaldığı için bedava. `tts` katmanı · ("uzatma"/barge-in ile ilişkili)
- [x] 🔄 [SÜREÇ] **Ses A/B aracı** — `scripts/tts_ab_compare.py` (edge-tts örnekleri + `--emotions` demo). Patron dinledi; gerçek-duygu için anahtar/eğitim bekliyor.

---

## 🔴 3. DALGA — Donanım/ROS (eve dönünce / robota entegre)
- [ ] ⏳ [DONANIM] **ALSA çıkış oto-tespiti** `_find_output_device()` — `demo_usb.py:82` sabit yerine isimle. (Kod PC'de yazılır, Jetson'da doğrulanır.) · *acil P0 — demo dayanıklılığı #1*
- [ ] ⏳ [DONANIM] **STT Jetson doğrulama** — kalite parametreleri + mikrofon konumu + (ops.) large-v3. · *acil P1*
- [ ] ⏳ [DONANIM] **CPU/latency ölçüm** — `tegrastats`/`jtop` boşta+yanıt; `n_threads` kısıtla. · *PERSONA_TON_FIZIBILITE §5*
- [ ] ⏳ [DONANIM] **ReSpeaker mic array** — gerçek barge-in (AEC) + gürültü bastırma. · *toplanti md.6 — barge-in tam çözüm*
- [ ] ⏳ [YENİ] **AI↔ROS sinyalleri** — "geldim"→`_greet`, "hareket/durdu"→dinleme+wake word duraklat. `demo_usb.py` / `integration/ros_signals.py` · *toplanti md.3/6 (⚠️ ROS mesaj formatı bekleniyor)*
- [ ] ⏳ [DONANIM] **Ekran kesme + sipariş kanalı** — robot konuşurken ekrandan dokunarak kesme/sipariş (ucuz barge-in). · *toplanti md.5*
- [ ] ⏳ [DONANIM] **Hesap/sipariş takibi gerçek demo doğrulama** — "hesap" denip OrderTracker toplamı teyit. · *acil P1 LLM #4*

---

## Faz 2 (sonraya)
Çoklu dil (karar yok), restoran-tipi ses paketleri, sürekli öğrenme/log, 360° ses
kaynağı, masa ayrımı. → PROJE_DURUMU Faz 2 + METODOLOJI §14/15.

## Açık kararlar (patron/ekip)
- **Ses yönü A vs B** — en acil iş kararı (2. Dalga'yı açar).
- Çoklu dil mimarisi (Faz 2).
- Fish/OpenAudio ticari lisansı (3 kaynak çelişkili → resmi LICENSE'tan doğrula).
- Faz 1 teslim tarihi (toplantıda net değil).

## Durum notları (önemli)
- Geliştirme: **Windows 11 WSL2 + RTX 4050** (`qwen3_backend` ile test). **Jetson şu an EVDE, erişilemiyor** → 3. Dalga (donanım) ertelendi.
- Persona **METNİ** çözüldü (W12/v4.9); açık olan ses **TINISI** (TTS motoru).
- E19 fix kodda ✅ · ALSA kalıcı fix ⏳ · guard'lar ⏳.
- "Her duruma hazır" = zarif fallback + guard + iteratif geri-bildirim (omniscience değil).
- Barge-in (araya girme): tam çözüm ReSpeaker AEC (3. Dalga); şimdilik **kısa konuş + ekran kesme** ile %80 telafi.

---

## Yeni Sohbet Başlangıç Promptu

```
Sen W-BOT projesinin SES/AI tarafı geliştirme asistanısın. SADECE ses/AI ile ilgilen;
ROS2/navigasyon/mekanik/donanım kapsam dışı (yalnızca arayüz noktası olarak ele al).

ÖNCE şu dosyaları oku (sırayla): YOL_HARITASI.md, PROJE_DURUMU.md,
PERSONA_TON_FIZIBILITE.md, TTS_LISANS_ARASTIRMASI.md, acil.md, toplanti.md, METODOLOJI.md.

BAĞLAM (özet):
- İlke: "iyi garson" — çekirdek sağlam + sınırda zarif + sıcak ses + kısa konuş +
  kesilebilir. Offline kalır; bulut sadece yatırımcı demosu. "Her şeyi bilsin" değil
  "asla rezil olmasın".
- Patron istekleri: daha sıcak/insansı ses, doğal problemsiz sohbet, her duruma hazır
  (zarif fallback), robot konuşurken araya girebilme (barge-in).
- Geliştirme: Windows 11 WSL2 + RTX 4050 (qwen3_backend ile test). Jetson şu an EVDE
  DEĞİL → donanım/3. Dalga işleri ertelendi.
- Açık karar: ses yönü Yol A (kendi sesimizle offline eğitim — önerilen) vs Yol B (ücretli).

ŞU AN: YOL_HARITASI 1. DALGA (PC'de, donanımsız) yürütülüyor.

GÖREVİM: <buraya ne yapmak istediğini yaz — örn. "1. Dalga'dan kısa-konuşma kuralı +
menü-dışı guard + düşük-güven guard'ı uygula" YA DA "Yol A için referans kayıt metnini
ve eğitim kurulumunu hazırla">.

KURALLAR: PROJE_DURUMU.md/METODOLOJI.md'yi onay almadan değiştirme; her değişiklik öncesi
ilgili mevcut kodu oku; offline kısıtı koru; ROS/donanım görevi üretme; her görevi bir
toplanti.md/acil.md maddesine bağla.
```
