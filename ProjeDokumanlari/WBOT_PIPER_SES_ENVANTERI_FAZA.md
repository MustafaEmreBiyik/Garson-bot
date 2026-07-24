# W-BOT Piper Ses-Eğitimi — Salt-Okunur Envanter (Faz A)

**Tarih:** 2026-07-11 · **Kapsam:** working-tree, commit yok · **Yöntem:** yalnız okuma (hiçbir dosya değiştirilmedi, hiçbir eğitim/inference çalıştırılmadı)

## Özet (bir cümle)
Veri hattı **uçtan uca tamamlanmış** (320 cümle → LJSpeech → preprocess → eğitim → **wbot_tr.onnx üretilmiş ve tts.py'ye bağlanmış**); eksik olan tek şey **eğitilmiş sesin kalite kanıtı** — mevcut A/B klasörü bu modeli değil, daha eski Edge (online) seslerini kıyaslıyor.

---

## 1) Dosya envanteri + durum

| Dosya | Boyut | Tarih | Git durumu |
|---|---|---|---|
| `scripts/build_piper_dataset.py` | 2.5 KB | Jul 1 17:49 | `??` (yeni, untracked) |
| `scripts/wbot_piper_training.ipynb` | 22 KB | Jul 3 14:07 | `??` (yeni, untracked) |
| `scripts/record_corpus.py` | — | — | ` M` (değişik, +46/−10) |
| `robot_waiter_ai/speech/tts.py` | — | — | ` M` (değişik, +7/−1) |
| `.gitignore` | — | — | ` M` (değişik, +3) |
| `test.wav` | **0 byte** | Jul 3 03:21 | `??` (boş/başarısız çıktı) |
| `wbot_ses_ornek.wav` | 336 KB (~7.6 sn) | Jul 3 03:16 | `??` |
| `tts_ab_out/` | 26 dosya (~1 MB) | Jun 26 | `??` |
| `data/` | 320+320 wav + preprocess + loglar | Jul 1 | `??` (izlenmiyor) |
| `phoneme_debug.txt` | — | — | `??` |
| **`robot_waiter_ai/models/wbot_tr.onnx`** | **60.6 MB** | **Jul 4 13:50** | gitignore'lu (yeni kuralla) |
| `robot_waiter_ai/models/wbot_tr.onnx.json` | 7.1 KB | Jul 4 08:45 | gitignore'lu |

`.gitignore` diff'i `wbot_tr.onnx` + `wbot_tr.onnx.json` + `*.gguf`'u yok sayıma ekliyor — yani üretilen model kasıtlı olarak repoya girmeyecek (büyük binary).

---

## 2) Veri hattı — hangi aşamada

**TAMAMLANMIŞ, uçtan uca.** Dört aşama da çıktı üretmiş:

1. **Kayıt** (`record_corpus.py`): **320/320 cümle kayıtlı** (`.corpus_progress.json` → 0–319 tam). Kaynak metin `scripts/tts_corpus.txt` (320 satır, Jun 30). Toplam ham ses ≈ **13.3 dakika** — notebook'un "13 dakikalık kendi ses kaydı" ifadesiyle birebir uyuşuyor. → `data/recordings/corpus_0001..0320.wav`
2. **Dataset** (`build_piper_dataset.py`): ham WAV'ları LJSpeech'e çeviriyor — `metadata.csv` (**320 satır**, `file_id|text|normalized_text`) + `wavs/` (320 kopya). Transkript hizalaması dosya-adı indeksiyle yapılıyor (`corpus_0001` → tts_corpus 0. satır). **Tam.**
3. **Preprocess** (`data/piper_preprocessed/`): `config.json` (22050 Hz, espeak-tr, num_symbols 256, tek konuşmacı) + `dataset.jsonl` (**320 kayıt**, her biri phoneme + phoneme_ids + cache path) + `cache/22050/` (**640 dosya** = 320 × `.pt`/`.spec.pt`). **Tam.** Bu adım **yerel** yapılmış (`dataset:"data"`).
4. **Manifest/normalizasyon:** phoneme çıkarımı ve spec cache üretilmiş; eğitime hazır.

Yani veri hattı **yarım değil** — 320 cümlelik korpus toplanmış ve eğitilebilir formata dönüştürülmüş.

---

## 3) Eğitim durumu

**İki ayrı iz var; nihai model Colab'dan gelmiş:**

- **Yerel deneme (LAPTOP-FNJCO3JT, Jul 1):** `lightning_logs/version_0,1,2`. version_0/1 minik (5 KB, saniyeler içinde iptal); **version_2 = 272 MB tfevents**, ~19:04→20:47 (≈1s40dk) çalışmış. Ancak **yerelde hiç `.ckpt` yok** (repo genelinde checkpoint araması sadece venv ve eski Qwen-LoRA'yı buldu). → Muhtemelen terk edilmiş yerel CPU eğitimi.
- **Colab hattı (`wbot_piper_training.ipynb`):** `tr_TR-dfki-medium` checkpoint'inden **fine-tune** (scratch değil — notebook markdown'ı bunu açıkça gerekçelendiriyor), `max_epochs=1000`, batch 16, T4 GPU, ardından ONNX export + Drive'a kaydet + bilgisayara indir. **Notebook'ta kaydedilmiş hücre çıktısı YOK** — loss eğrisi, epoch sayısı, return-code, hiçbiri dosyada saklı değil. İskelet/temiz durumda.

**Model ağırlığı ÜRETİLMİŞ mi? → EVET.** `wbot_tr.onnx` (60.6 MB, Jul 4). `wbot_tr.onnx.json` içinde `dataset:"content"` + `quality:"piper-preprocessed"` (Colab `/content` yolu) — yerel preprocess config'inden (`dataset:"data"`, `piper_preprocessed`) **farklı**. Bu, dağıtılan modelin **Colab fine-tune çıktısı** olup indirildiğini doğruluyor. Kaç epoch eğitildiği ise **belgelenmemiş** (çıktı yok).

---

## 4) A/B kanıtı — `tts_ab_out/`

**Bu klasör eğitilen sesi DEĞİL, daha eski online sesleri kıyaslıyor (Jun 26, Piper çalışmasından ~1 hafta önce):**

- `index.html` → **edge_emel · edge_emel_warm · edge_ahmet** (hepsi Microsoft **Edge/online** TTS). 4 cümle × 3 ses.
- `emotions.html` → "hepsi aynı ses (Emel), yalnızca pitch/hız/ses değişiyor" — prozodi hilesi (neutral/excited/warm/soft/faz-bazlı).
- `emotions_en.html` → aynı, en-US-AriaNeural ile.

→ **`tts_ab_out/` persona/ton seçimi içindir; `wbot_tr.onnx` kalitesine dair kanıt DEĞİLDİR.** Custom Piper sesi bu karşılaştırmada hiç yer almıyor.

**Skor/not dosyası:** yok. **Custom ses vs stok Piper A/B'si:** yok.

Tek custom-ses izi: `wbot_ses_ornek.wav` (~7.6 sn, Jul 3) — tek örnek, kaynağı (hangi checkpoint) belgesiz ve final onnx'ten (Jul 4) bir gün eski; `test.wav` **0 byte** (boş/başarısız). İkisinin de eşlik eden karşılaştırma/skoru yok.

---

## 5) `tts.py` entegrasyon yüzeyi

**Drop-in — arayüz DEĞİŞMEMİŞ.** Diff yalnızca iki şey yapıyor:

1. `_PIPER_MODEL_CANDIDATES` listesinin **başına** `wbot_tr.onnx` eklenmiş (varsa öncelikli, yoksa mevcut `tr_TR-fahrettin-medium/high`'a düşüyor). → **Piper-fallback yolu korunmuş.**
2. Piper CLI çağrısından `--quiet` bayrağı **kaldırılmış** (yorum: pip `piper-tts` v1.4.2+ bu bayrağı tanımıyor ve çıktıyı ~0.3 sn'ye kesiyor; `capture_output=True` zaten stderr'i bastırıyor).

`PiperTTS` sınıfının synth metodu (subprocess → tmp WAV) imzası ve dönüş tipi değişmemiş; yeni sınıf/arayüz eklenmemiş. Yani `synthesize() -> bytes` sözleşmesine dokunulmamış, sadece model önceliği + bir CLI uyumluluk düzeltmesi.

---

## 6) Kritik kural ihlali taraması (salt tespit)

**Yasak desen bulunamadı.**

- `build_piper_dataset.py`: yalnız `shutil` + `pathlib`. Temiz.
- `record_corpus.py`: `sounddevice` **sadece kayıt** için (`sd.InputStream`) — **playback yok** (`sd.play`/`OutputStream` yok). Yeni eklenen `_resample()` **`np.interp` (lineer interpolasyon)** kullanıyor, **`scipy` DEĞİL** — yasak bağımlılıktan bilinçli kaçınma.
- Notebook: `scipy` 0, `sounddevice` 0.

---

## Ne var / ne eksik

| | Durum |
|---|---|
| Korpus (320 cümle / ~13 dk) | ✅ var |
| LJSpeech dataset + preprocess | ✅ tam |
| Eğitim (Colab fine-tune) | ✅ çalışmış, model üretmiş |
| `wbot_tr.onnx` model | ✅ var (60.6 MB), tts.py'ye bağlı |
| Yerel checkpoint (.ckpt) | ❌ yerelde yok (Colab/Drive'da) |
| Eğitim metrikleri (loss/epoch) | ❌ belgelenmemiş (notebook çıktısız) |
| **Custom ses kalite kanıtı (A/B / skor)** | ❌ **yok** |
| Kural ihlali | ❌ yok (temiz) |

---

## PROJE_DURUMU.md için özet blok

> **W-BOT özel-ses (Piper/VITS) — Faz A envanteri (2026-07-11, salt-okunur):**
> 320 cümlelik (~13 dk) kendi-ses korpusu → LJSpeech → preprocess **tamamlandı**. `tr_TR-dfki-medium`'dan Colab T4 fine-tune ile **`wbot_tr.onnx` (60.6 MB) üretildi** ve `tts.py`'de öncelikli aday olarak bağlandı (fahrettin fallback korunuyor; `--quiet` CLI uyumluluğu için kaldırıldı). Kod kural-temiz (scipy yok, playback yok; resample `np.interp`). **Açık boşluk:** eğitilen sesin kalite kanıtı yok — `tts_ab_out/` yalnızca eski Edge/online seslerini kıyaslıyor, custom ses için A/B veya skor dosyası bulunmuyor; eğitim metrikleri (loss/epoch) notebook'ta saklı değil; `wbot_ses_ornek.wav` tek/kaynağı belgesiz örnek, `test.wav` 0 byte. Yerelde `.ckpt` yok (Drive/Colab'da).
