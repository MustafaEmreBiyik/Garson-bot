# TTS Lisans Araştırması — Ticari Kullanım (Production)

**Tarih:** 26 Haziran 2026
**Amaç:** W-BOT *satılabilir/yatırım alınabilir* bir ürün olduğundan, kullanacağımız
TTS motorunun ve sesinin **ticari kullanıma hukuken uygun** olduğunu garantilemek.
İlgili: [PERSONA_TON_FIZIBILITE.md](PERSONA_TON_FIZIBILITE.md).

> ⚠️ **Uyarı:** Lisanslar değişir. Aşağıdaki bilgiler ~Haziran 2026 itibarıyladır;
> deploy öncesi her motorun **resmi lisans dosyasından** teyit edilmelidir (linkler altta).
> Bu hukuki tavsiye değildir; kritik kararda hukukçuya danışın.

---

## Çözmemiz gereken iki ayrı "izin"

| | Ne sorar | Risk |
|---|----------|------|
| **1. Motor (model) lisansı** | "Bu AI modelini satılan üründe kullanabilir miyim?" | Non-commercial modeli ürüne koymak = lisans ihlali |
| **2. Sesin hakkı** | "Bu sesi (klon/kayıt) ticari kullanma hakkım var mı?" | Başkasının/internetten sesi = ses-likeness ihlali |

İkisi **bağımsızdır**: serbest lisanslı motora bile, hakkı olmayan bir sesi koyarsan sorun olur.

---

## 1. Motor Lisansları (doğrulanmış)

| Motor | Lisans | Ticari? | Türkçe? | Expresiflik | Not |
|-------|--------|---------|---------|-------------|-----|
| **XTTS-v2** | CPML | ❌ Hayır | ✅ | ✅ klon | Coqui kapandı (Oca 2024) → ticari lisans **satın alınamıyor**. Sadece demo/değerlendirme. |
| **Fish-Speech / OpenAudio S1-mini** | CC-BY-NC-SA-4.0 (açık ağırlık) | ❌ Hayır | ✅ | ✅ duygu işaretli | **Offline çalışır** (açık ağırlık, CUDA). Sorun bağlantı değil, **NC lisansı**. Ticari kullanım için fish.audio API/ticari lisans gerekir (fiyat belirsiz). |
| **F5-TTS** | CC-BY-NC-4.0 | ❌ Hayır | ⚠️ zayıf/finetune | ✅ klon | NC, fine-tune'a da yansır. |
| **Kokoro** | Apache-2.0 | ✅ **Evet** | ❌ **Yok** | orta | Lisans mükemmel ama **Türkçe desteklemiyor** (talep açık, henüz yok). |
| **Piper** | MIT (eski, arşiv) / **GPL-3.0** (yeni `piper1-gpl`) | ✅ Evet | ✅ (dfki/fahrettin/fettah) | ❌ düz | Biz Piper'ı **ayrı subprocess** çağırıyoruz → GPL kodumuza bulaşmaz. ⚠️ **Ses modeli lisansı ayrı — her ses için MODEL_CARD doğrula.** |
| **StyleTTS 2** | MIT (kod) | ✅ Evet | ⚠️ eğitilmeli | ✅ iyi | Hazır ağırlık İngilizce; Türkçe için **kendi eğitimin** gerekir → eğitirsen sen sahip olursun. |
| **Bark** | MIT | ✅ Evet | ⚠️ zayıf | ✅ (gülme vb.) | İngilizce ağırlıklı, kararsız. |
| **Coqui TTS toolkit** | MPL-2.0 (kod) | ✅ (değişiklik açıklanırsa) | — | — | Sadece **araç**; içindeki XTTS *modeli* CPML (NC). Toolkit ≠ model. |

---

## 2. ⚠️ Kritik Sonuç

**"Bedava + offline + ticari-serbest + Türkçe + expresif" hepsini birden veren bir
açık model ŞU AN YOK.** En expresif açık ağırlıklar (XTTS, Fish, F5) **non-commercial**;
ticari-serbest olanlar (Kokoro/StyleTTS2/Bark) ya **Türkçe yok** ya **hazır Türkçe ses yok**.

Yani bir **ödün** seçmek zorundayız. Üç temiz yol var:

### Yol A — Kendi modelini kendi sesinle eğit *(önerilen: temiz + offline + bedava)*
- **Kod lisansı serbest** mimari kullan (Piper/VITS, StyleTTS2=MIT, Coqui toolkit=MPL).
- **Kendi (ekip) sesinle** eğit/klonla → **çıkan ağırlık senindir** → ticari serbest, offline, marjinal maliyet 0.
- Expresiflik: VITS/Piper **orta** (per-cümle prozodiyle telafi) · StyleTTS2 **iyi** (daha çok emek).
- Maliyet: **para değil, eğitim emeği.**

### Yol B — Ticari lisans/abonelik satın al
- **Fish Audio API** (online, cloud servisi; açık ağırlığın kendisi NC → ticari için API aboneliği şart).
- veya **ElevenLabs / Azure** (online; karakter başı ücret). Demo/premium katman için.
- ⚠️ Not: Fish-Speech açık modeli **offline çalışır** ama CC-BY-NC-SA → ticari üründe kullanamassın.
- Maliyet: **para** (+ ElevenLabs/Azure online).

### Yol C — Piper + ticari-temiz Türkçe ses
- Piper motoru serbest; **ses modelinin** lisansını doğrula (veya kendi sesinle yeni Piper sesi eğit).
- Hukuken en kolay, ama **düz/expresif değil.**

---

## 3. Sesin Hakkı (motordan bağımsız)

| Ses kaynağı | Maliyet | Hak | Karar |
|-------------|---------|-----|-------|
| **Ekipten birinin sesi + yazılı izin** | Bedava | ✅ Temiz | **Pilot/MVP için bunu kullan** |
| Profesyonel ses sanatçısı (buyout sözleşmesi) | Orta | ✅ En temiz | Ürünleşince opsiyonel cila |
| İnternetten "bedava" ses | Bedava | ❌ Belirsiz | **Kullanma** (CC0/ticari ses seti değilse) |

- Klonlama **15-30 sn**, fine-tune **10-30 dk** temiz kayıt ister.
- İzin belgesi: bir paragraf ("sesimin W-BOT ticari ürününde kullanımına izin veriyorum") yeterli sigorta.

---

## 4. Öneri ve Karar Kapıları

**Önerilen production yolu:** **Yol A** — ekip üyesinin sıcak Türkçe sesiyle, kod-lisansı
serbest bir mimaride (başlangıç: **Piper/VITS**; daha expresif istenirse **StyleTTS2 eğitimi**)
**kendi modelimizi** üret. Hukuken tertemiz, offline, tekrarlayan maliyet yok.
**Expresiflik açığı** per-cümle prozodi + (gerekirse) sonra Yol B'ye yükseltme ile kapatılır.

**ElevenLabs/Fish-API** = yatırımcı demosu + interneti olan şubeler için **opsiyonel premium**.

**Karar kapıları:**
- ☑ **Yol A seçildi** (28 Haz 2026) — ekip üyesi sesi + Piper/VITS eğitimi.
- ☑ **Piper binary'si MIT'e sabitlendi** (12 Tem 2026) — üretim artık pip
  `piper-tts` 1.4.2 (GPL-3.0, OHF-voice/piper1-gpl) DEĞİL, arşivlenmiş
  `rhasspy/piper` MIT binary'si (`2023.11.14-2`) kullanıyor; ayrıca bu 1.4.2
  sürümünün Türkçe fonemizasyonu bozuktu (garble kök-nedeni). Detay:
  PROJE_DURUMU.md "TTS — Piper Garble Fix" bölümü.
- ☑ Piper Türkçe ses modeli lisansı — **dfki-medium** (MIT, `rhasspy/piper-voices`)
  stok fallback olarak kullanımda; fahrettin/fettah HuggingFace'ten kaldırıldı.
- ☑ Ses: ekip üyesi (proje sahibi) kendi sesiyle 320 cümle/~13 dk kaydetti,
  `wbot_tr.onnx` bu kayıtlardan (dfki tabanından fine-tune) üretildi.

---

## 5. Maliyet & Efor — Yol A vs Yol B (~Haziran 2026 fiyatları)

### Yol A — Kendi modelini eğit (tek seferlik EMEK, marjinal maliyet $0)

| Yaklaşım | Veri | Süre (tahmini) | Expresiflik | Para |
|----------|------|----------------|-------------|------|
| **Piper/VITS özel ses** ⭐ | Ekip üyesinden ~30-60 dk temiz Türkçe + transkript | **~1-2 hafta** part-time | Orta (+prozodi telafisi) | ~$0-50 bulut GPU |
| **StyleTTS2 eğitimi** | ~1 saat+ veri + Türkçe G2P | **~3-6 hafta** + ML uzmanlığı | İyi | ~$0-100 |

Emek kalemleri: kayıt (yarım gün) → veri temizleme/hizalama (en zahmetli, 1-3 gün) →
eğitim + deneme-yanılma (birkaç gün) → entegrasyon (1-2 gün, drop-in arayüz hazır).
Ekip zaten LLM fine-tune (QLoRA/Colab) yapıyor → GPU eğitim bariyeri düşük.

### Yol B — Ticari servis (tekrarlayan ÜCRET, online)

Varsayım: **robot başına ~1-3M karakter/ay** (orta-yoğun restoran, yanıt ~80 karakter).

| Servis | Birim | Robot başına / ay | Not |
|--------|-------|-------------------|-----|
| Azure (standart neural) | $16/1M | **~$16-48** | İlk 500K/ay bedava |
| Azure Custom Neural Voice (klon) | $24/1M | **~$24-72** + hosting | Türkçe CNV mümkün; başvuru gerekir |
| Fish API | $15/1M | **~$15-45** | Türkçe çok-byte → biraz yüksek; ⚠️ self-host ticari lisansı belirsiz (3 kaynak 3 lisans) |
| ElevenLabs | kredi=karakter | **~$300-1000** | Scale $299/1.8M, Business $990/6M — premium |

⚠️ Rakamlar **robot başına.** Filo büyüdükçe **lineer çarpılır** + hepsi **online**
(offline'ı seçme sebebimiz olan internet bağımlılığını geri getirir).

**Özet:** A = 1-2 hafta emek → ömür boyu offline/$0/hak temiz (expresiflik orta).
B = sıfır emek → robot başına ~$15-70/ay (ElevenLabs $300+), online, filoyla çarpan.
**Öneri:** A production'da, B (ElevenLabs/Azure) yatırımcı demosunda.

---

## Kaynaklar (deploy öncesi tekrar doğrula)

- Fish/OpenAudio S1-mini lisansı: <https://huggingface.co/fishaudio/openaudio-s1-mini> · tartışma: <https://github.com/fishaudio/fish-speech/discussions/1001>
- XTTS-v2 CPML: <https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt> · <https://github.com/coqui-ai/TTS/discussions/4304>
- Kokoro (Apache-2.0) + Türkçe talebi: <https://huggingface.co/hexgrad/Kokoro-82M> · <https://github.com/hexgrad/kokoro/issues/204>
- Piper (MIT→GPL geçişi): <https://github.com/rhasspy/piper> · <https://github.com/OHF-Voice/piper1-gpl> · sesler: <https://huggingface.co/rhasspy/piper-voices>
- Karşılaştırma derlemesi: <https://www.promptquorum.com/power-local-llm/local-tts-voice-cloning-piper-coqui-xtts>
