# Garson-bot — Proje Durumu ve Hedeflenen Hal
**Son güncelleme:** 13 Temmuz 2026 | **Sürüm:** 5.22

Yeni bir sohbet başladığında bu dosyayı okuyarak projeyi baştan anlat.
Kod tabanını tekrar incelemene gerek yok — her şey burada.

---

## Bir Sonraki Oturum — Hızlı Özet

**Neredeyiz:** Jetson'da uçtan uca demo çalışıyor. Whisper medium aktif (1.7s). Geliştirme ortamı Windows 11 WSL2'ye taşındı (Ubuntu dual-boot kaldırıldı). WSL2 kurulumu tamamlandı — PyTorch CUDA, faster-whisper, llama-cpp-python (GPU), Piper TTS model (24 Haziran 2026). Jetson SSH: 192.168.1.67 (⚠️ DHCP ile değişebilir — her Jetson işi öncesi teyit et; 12 Temmuz 2026'da .65 dev makinenin kendi IP'sine dönüşmüştü). **wbot_v4 eğitildi, GGUF'a dönüştürüldü, Jetson'a deploy edildi ve eval edildi (4 Temmuz 2026)** — güncel baseline (6 Temmuz 2026, E24 revizyonu sonrası): 32 senaryo 29/32 (%90, KALDI: E01, E24, E27), `--v4-targets` 38 senaryo 31/38 (%81); E24 bilinen boşluk, üretimde S12 guard karşılıyor. Görev #21-25 tamamlandı (detect_order fix, S12 guard, seed=0xFFFFFFFF, gen_karmasik incelemesi, E01/V01 post-processing) ve Jetson'a deploy edildi. Görev #25 sonucu: E01 üretimde ZATEN kapalı çıktı (kod yazılmadı), V01 fiyat enjeksiyonu eklendi. **C paketi script-tabanlı veri hazır (görev #27, 7 Temmuz 2026):** S34/V02 (20), V04 küfür (18), V06/E27 alerji kalıp (24) — 62 kayıt, 3 ayrı `wbot_c_*.jsonl`, audit 0 ihlal, MERGE EDİLMEDİ; V06 eval kriteri 3-öğe kalıbına reformüle edildi → yeni 38-senaryo baseline 32/38 (%84, WSL2; E27 bu koşuda geçti — platform notu görev #27'de). **C paketi LLM-API kalemleri DOĞRULANDI + commit'lendi (görev #28, 9 Temmuz 2026):** S41 eskalasyon (20) + anti-hallüsinasyon (100) = 120 kayıt + V07 eval tanımı; bilinmeyen oturumdan gelen commit'siz working-tree çıktısı rijit doğrulandı (audit 0, kanonik 5460, anti-hall'da bağımsız menu.yaml çapraz kontrol → 0 uydurma, alt-tip başına tam benzersizlik), V07 tek koşu 39 senaryo 32/39 (WSL2) V07 doğru yapısal nedenle KALDI. **TÜM C paketi verisi hazır: #27'nin 62 + #28'in 120 = 182 kayıt (hedef 175-185 içinde).** **W11 kanonik prompt revizyonu + wbot_v5 merge TAMAMLANDI (görev #29, 10 Temmuz 2026):** `_SYSTEM_TEMPLATE` kapanış kuralı S12 Karar 2'ye hizalandı (özet+toplam+onay → onay sonrası toplamsız "Afiyet olsun"); yan bulgu olarak `_MAX_HIST_CHARS=4000`'in context-overflow'a (n_ctx aşımı → ValueError çökmesi) yol açtığı ampirik olarak bulundu ve 1000'e düzeltildi (detay: "W11 Kanonik Prompt Revizyonu (wbot_v5)" bölümü). `wbot_v5_train.jsonl` (3787 kayıt) hazır, audit 0 ihlal, süit 490/490 PASS. **Jetson senkronize edildi (görev #30, 10 Temmuz 2026):** `18c429a`'ya
pull edildi, içerik md5/git-blob ile doğrulandı, GGUF'a dokunulmadı. **Erken
doğrulama (retrain-öncesi, mevcut wbot_v4 GGUF + YENİ prompt):** 32 senaryo
29/32, 39 senaryo 32/39 — E01+E27+V04 iyileşti ama **E19 ve E16 önceden
GEÇEN'den KALDI'ya döndü** (E19 gerçek içerik kayması — W11 paragrafının
promptun başka bir bölümünü dolaylı etkilemesi, retrain'le kendiliğinden
düzelmeyecek, ayrı görev gerekiyor; E16 muhtemelen check-tasarım yanlış
alarmı). Detay: "Jetson Senkron + Erken Doğrulama" bölümü. `wbot_v5_colab_training.ipynb` hazır. **Kalan tek adım: Colab'da retrain** (bkz. ilgili bölüm) + sonrasında ayrı bir görevde GGUF dönüşümü/Jetson deploy. Tüm yedekler GitHub + Drive'da.

**TTS hattı — Piper garble kök-neden bulundu + düzeltildi + telaffuz sözlüğü eklendi (11-13 Temmuz 2026):** `wbot_tr.onnx` (W-BOT özel sesi, Colab fine-tune, dfki-medium tabanından ~1120 epoch, deployed=epoch 6799) sesi bazı cümlelerde bulanık geliyordu; kök neden araştırmasında **iki ayrı sorun** bulundu ve ikisi de düzeltildi: (1) pip `piper-tts` 1.4.2 (GPL, OHF-voice fork) Türkçe fonemizasyonu bozuk — temiz UTF-8 girdide bile İngilizce'ye düşüp garble üretiyordu (model bağımsız — hem custom hem stok aynı çöp fonemi veriyordu); **çözüm: arşivlenmiş MIT rhasspy/piper binary'sine geçildi** (`<project>/piper/`, commit `18d1f25`), stok fallback fahrettin (HF'den kaldırıldı) → dfki-medium'a çevrildi, `scripts/setup_piper.sh` ile tekrar-üretilebilir kurulum eklendi; dev+Jetson'da doğrulandı. (2) espeak-tr, İngilizce-yazımlı kelimeleri (cheesecake, cappuccino, latte...) Türkçe harf kurallarıyla yanlış okuyor — **çözüm: `robot_waiter_ai/speech/pronunciation.py`** (30 girişlik telaffuz haritası, sentezden hemen önce uygulanır), commit `338ef7a`, 515 test yeşil, dev+Jetson'da doğrulandı. **Açık kalan iş — overfit hipotezi testi:** wbot_tr ~1120 epoch fine-tune aldı (320 cümle/13 dk için fazla olabilir), görülmemiş cümlelerdeki bulanıklık aşırı-öğrenme imzasına uyuyor; checkpoint kör A/B altyapısı hazır (`build_checkpoint_ab.py`, doğrulandı) ama **erken checkpoint'lerin (5799/6099/6399) ONNX export'u kullanıcı aksiyonu bekliyor** (Colab'da hazır export hücresiyle, private Drive checkpoint'leri yerelde indirilemediği için). Detay: aşağıdaki "TTS — Piper Garble Fix + Telaffuz Sözlüğü + Checkpoint Overfit Testi" bölümü.

**Sıradaki görevler (öncelik sırasıyla):**

1. ~~**`detect_order()` testi**~~ — ✅ Tamamlandı (5 Temmuz 2026, commit a82dcf3): bug doğrulandı ve düzeltildi, detay görev tablosu #21
2. ~~**S12 runtime guard uygulaması**~~ — ✅ Tamamlandı (5 Temmuz 2026): TUR 1 + TUR 2 deterministik guard + saf veda kapsaması, detay görev tablosu #22
3. ~~**Seed sabitleme**~~ — ✅ Tamamlandı (6 Temmuz 2026): `seed=0xFFFFFFFF` uygulandı (örtük varsayılan açıkça yazıldı, davranış değişmedi — Jetson'da 32/32 bit-exact doğrulandı); `seed=42` denendi ve reddedildi (davranışı değiştiriyor), detay görev tablosu #23 + METODOLOJI.md "Seed" notu
4. ~~**`gen_karmasik.py` veri incelemesi**~~ — ✅ Tamamlandı (6 Temmuz 2026): şüphe çürüdü, veri 150/150 doğru yapıda; kök neden kanonik prompttaki S12-öncesi kural + model genellemesi; guard (görev #22) çözüyor, C paketine veri maddesi eklenmeyecek — detay görev tablosu #24
5. ~~**E01/V01 post-processing**~~ — ✅ Tamamlandı (6 Temmuz 2026): E01 kod gereksiz çıktı (üretimde fast-path + E19 katmanıyla zaten kapalı, ham-model bilinen boşluğu), V01 fiyat enjeksiyonu `demo_usb.py`'ye eklendi (22 yeni test, süit 431/431) — detay görev tablosu #25
6. **Gürültülü ortam testi** — restoran müziği + kalabalık ortamda Jetson'da wake word + STT kalitesi

> 📐 **Senaryo kararları (3 Temmuz 2026):** S19 alerji+öneri → filtrele+uyarı (Seçenek B),
> S12 onay öncesi → her zaman özet+toplam (E24 revizyonu ✅ 6 Temmuz'da yapıldı; W11 kanonik prompt revizyonu wbot_v5 döngüsüne kaldı), S29 küfür ve
> S03 sessizlik politikaları netleşti. Yeni eval hedefleri `eval_gguf.py --v4-targets`
> (V01-V06). Tamamı: [SENARYO_PLANI_FAZ1.md](SENARYO_PLANI_FAZ1.md)

> 🎯 **wbot_v4 eval sonuçları (4 Temmuz 2026 — ARŞİV KAYDI):** ⚠️ Bu not,
> 4 Temmuz fotoğrafıdır. Aşağıda anlatılan S12/detect_order işleri o tarihten
> sonra TAMAMLANDI (görev #21, #22 — 5 Temmuz) ve E24 revizyonuyla (görev
> #16 — 6 Temmuz) güncel baseline 29/32'ye (KALDI: E01, E24, E27) döndü.
> Güncel durum: "Sistem durumu" ve görev tablosu. Orijinal kayıt:
> GGUF Jetson'a deploy edildi
> (`/home/emk/models/Qwen3-4B-wbot_v4-Q4_K_M.gguf`), eval çalıştırıldı (2 kez,
> birebir aynı sonuç — deterministik). 32 senaryo: 30/32 (%93), KALDI: E01,
> E27. `--v4-targets` 38 senaryo: 32/38 (%84), KALDI: E01, E27, V01, V02, V04,
> V06. **E01 ve E27 wbot_v3→v4 REGRESYONU** — wbot_v3'te ikisi de GEÇİYORDU
> (31/32'nin parçasıydı), yeni bulgu değil. **Metodoloji notu:**
> `eval_gguf.py`, `demo_usb.py`'nin Guard 1/2/3 + `_fast_path_reply()` +
> post-processing katmanlarını tamamen atlayıp `LlamaCppBackend.generate_reply()`'i
> doğrudan çağırıyor — V04 ham eval'de ciddi görünüyor ("Size çok kızarmak
> istiyorum") ama Guard 3 (`_is_offensive`) zaten "aptal" gibi terimleri
> yakalayıp LLM'e ulaşmadan sabit yanıt döndürüyor, üretimde risk düşük. V01
> (fiyat eksik), V06 (alerjen halüsinasyonu) ve S12/E24 (aşağıda) ise gerçek,
> korumasız boşluklar. Detay ve tam eval çıktıları: aşağıdaki "wbot_v4
> Eğitim, GGUF ve Eval Sonuçları" bölümü.
>
> **S12 manuel test (2 tetikleyici):** (a) Saf kapanış ("Hayır, başka
> istemiyorum, bu kadar.") → eski toplamsız kapanışa döndü, S12 hiç
> tetiklenmedi. (b) Eğitilmiş ekle+kapat kalıbı ("Bir de ayran, başka
> istemiyorum.") → özet+toplam üretti ama onay sorusu YOK, doğrudan "Afiyet
> olsun"a atladı — S12 eğitilmiş kalıpta bile eksik. Bu yüzden runtime guard
> kararlaştırıldı (kod, veri değil) — ama ilk guard taslağı bir mantık hatası
> içeriyordu (`_is_closing_signal`'ın kendi ürün-eşleşme kontrolü, ekle+kapat
> cümlesinde guard'ı yanlışlıkla devre dışı bırakıyordu). Düzeltilmiş
> yaklaşım ve `detect_order()` ön koşulu: `claude_code_prompt_C_paketi_dataset.md`.
> **[SONUÇ — 5-6 Temmuz]:** Ön koşul bug'ı doğrulandı ve düzeltildi (görev
> #21), düzeltilmiş guard uygulandı (görev #22), E24 eval'i S12 kriterine
> revize edildi (görev #16) — bu paragraf artık tarihsel bağlam.

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

**Sistem durumu (4 Temmuz 2026):**
- Jetson: ✅ tam çalışıyor — wake word → Whisper medium CUDA → LLM GGUF → Piper TTS → USB hoparlör
- GGUF: `/home/emk/models/Qwen3-4B-wbot_v4-Q4_K_M.gguf` (2.5 GB) — Drive'da da yedek var, byte-exact doğrulandı
- Eval: `scripts/eval_gguf.py` — 32 senaryo %90 (29/32, KALDI: E01, E24, E27), `--v4-targets` 38 senaryo %81 (31/38) — 6 Temmuz 2026 E24 revizyonu sonrası yeni baseline; E24 bilinen boşluk (ham model, W11 kuralı), üretimde S12 guard karşılıyor. E01 de üretimde kapalı: kısa karşılama fast-path şablonuna düşüyor (LLM bypass), uzunları E19 post-processing "?" garantisi yakalıyor — ham-model bilinen boşluğu olarak eval'de kalır (görev #25). V01 üretimde fiyat enjeksiyonuyla kapalı (görev #25) — eval_gguf.py bu katmanları bypass ettiğinden ham skor değişmez. Eski baseline (30/32, %93) revizyon-öncesi E24 kriteriyle ölçülmüştü
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
│   ├── test_wakeword_usb.py      ✅ USB mikrofon ile gerçek zamanlı wake word testi
│   └── setup_piper.sh            ✅ Piper runtime kurulumu (MIT binary + dfki-medium, arch algılar — 11 Temmuz 2026)
└── robot_waiter_ai/
    ├── inference/
    │   ├── qwen3_backend.py      ✅ PC için — Qwen3-4B transformers 4-bit NF4
    │   │                            _build_system_prompt() export'u var (eval_adapter.py kullanır)
    │   └── llama_cpp_backend.py  ✅ Jetson için — Qwen3-4B GGUF Q4_K_M + CUDA
    ├── speech/
    │   ├── stt.py                ✅ faster-whisper STT wrapper (model: small)
    │   ├── tts.py                ✅ edge-tts + PiperTTS (Piper birincil, edge-tts fallback)
    │   ├── pronunciation.py      ✅ Yabancı-yazımlı kelime → Türkçe telaffuz haritası (11 Temmuz 2026)
    │   └── mic.py                ✅ ReSpeaker Mic Array wrapper
    ├── data/
    │   ├── menu.yaml             ✅ Menü tanımları (name, category, price, description, aliases) — hepsi Türkçe yazımlı
    │   └── restaurant_info.yaml
    ├── models/
    │   ├── hey_garson.onnx           ✅ Wake word modeli (openWakeWord, 789 KB)
    │   ├── wbot_tr.onnx               ✅ Özel W-BOT Piper sesi (gitignore'lu, ~60.6 MB — Colab fine-tune, dfki tabanı)
    │   └── tr_TR-dfki-medium.onnx     ✅ Stok Piper fallback (MIT, gitignore'lu — fahrettin HF'den kaldırıldı)
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
| Model | Qwen3-4B-wbot_v4-Q4_K_M.gguf (4 Temmuz 2026'da wbot_v3'ten değiştirildi) |
| Konum | /home/emk/models/Qwen3-4B-wbot_v4-Q4_K_M.gguf |
| Backend | llama-cpp-python 0.3.23 (CUDA SM87) |
| GPU offload | 37/37 katman (tam GPU) |
| VRAM | ~2.38 GB / 15.6 GB |
| Hız | ~12-15 tok/s |
| Thinking | Kapalı — _format_prompt() `<think>\n\n</think>` prefix ekler |
| n_ctx | **4096** (sistem prompt ~2100 tok olduğundan 1536 yetersizdi) |
| max_tokens | **65** |
| Decoding | temperature=0.55, top_p=0.9, top_k=40, repeat_penalty=1.2 |
| Seed | ✅ **`seed=0xFFFFFFFF`** (6 Temmuz 2026, görev #23) — örtük varsayılan (LLAMA_DEFAULT_SEED) açıkça yazıldı, davranış değişmedi; WSL2+Jetson'da 32/32 bit-exact doğrulandı. `seed=42` denendi ve REDDEDİLDİ (davranışı değiştiriyor). Detay: METODOLOJI.md "Seed" notu |
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
| Piper — model zinciri: `wbot_tr.onnx` (özel W-BOT sesi, öncelikli) → `tr_TR-dfki-medium.onnx` (stok fallback, MIT) | ✅ Birincil, offline |
| edge-tts | Fallback (internet gerekli) |

**Piper binary: MIT rhasspy/piper (arşivlenmiş, `2023.11.14-2`), `<project>/piper/` altında** — pip `piper-tts` 1.4.2 (GPL, OHF-voice fork) DEĞİL; 1.4.2'nin Türkçe fonemizasyonu bozuk (11 Temmuz 2026'da bulundu, detay aşağıda). Kurulum: `scripts/setup_piper.sh` (arch algılar, binary+dfki indirir, idempotent).
Eski `tr_TR-fahrettin-medium` HuggingFace'ten kaldırıldığı için artık indirilemiyor — fallback dfki-medium'a çevrildi.
Telaffuz sözlüğü: `robot_waiter_ai/speech/pronunciation.py` — İngilizce-yazımlı kelimeleri (cheesecake, cappuccino, latte...) sentezden önce Türkçe fonetik yazıma çevirir.

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
| **GGUF eval — eval_gguf.py (32 senaryo, Jetson, wbot_v3, 22 Haziran 2026)** | **31/32 (%96)** | **1** | — | — | — |
| **GGUF eval — eval_gguf.py (32 senaryo, Jetson, wbot_v4, 4 Temmuz 2026)** | **30/32 (%93)** | **2** | — | — | — |
| **GGUF eval — eval_gguf.py --v4-targets (38 senaryo, Jetson, wbot_v4, 4 Temmuz 2026)** | **32/38 (%84)** | **6** | — | — | — |
| **GGUF eval — eval_gguf.py (32 senaryo, Jetson, wbot_v4, 6 Temmuz 2026 — E24 revizyonu sonrası GÜNCEL baseline)** | **29/32 (%90)** | **3** | — | — | — |
| **GGUF eval — eval_gguf.py --v4-targets (38 senaryo, Jetson, wbot_v4, 6 Temmuz 2026)** | **31/38 (%81)** | **7** | — | — | — |
| **GGUF eval — eval_gguf.py --v4-targets (38 senaryo, WSL2, wbot_v4, 7 Temmuz 2026 — V06 reformülasyonu sonrası GÜNCEL)** | **32/38 (%84)** | **6** | — | — | — |
| **GGUF eval — eval_gguf.py --v4-targets (39 senaryo, WSL2, wbot_v4, 9 Temmuz 2026 — V07 eklendi)** | **32/39 (%82)** | **7** | — | — | — |

*wbot_v3 GGUF eval başarısızları: E19 (açıklama sonrası soru yok — gerçek model hatası, wbot_v4'te düzeldi). E21 düzeltildi — artık geçiyor.*

*6 Temmuz baseline'ındaki skor düşüşü (30→29) model regresyonu DEĞİL — E24 kriteri S12 Karar 2'ye revize edildi (görev #16); ham model W11 prompt kuralı nedeniyle E24'te bilerek kalıyor, üretimde S12 guard karşılıyor. KALDI: E01, E24, E27.*

*wbot_v4 32-senaryo başarısızları: **E01, E27 — wbot_v3→v4 REGRESYONU** (wbot_v3'te ikisi de GEÇİYORDU, yeni bulgu değil). E19 artık GEÇİYOR (W15/A1 paketi hedefine ulaşıldı).*

*wbot_v4 --v4-targets ek başarısızlıkları: V01 (modifikasyon onayında fiyat eksik — format), V02 (S34 verisi hiç yok — beklenen/dokümante), V04 (küfüre karşılık — ham eval'de görülüyor ama `demo_usb.py` Guard 3 zaten yakalıyor, üretim riski düşük), V06 (glütensiz listesine gluten içeren ürün ekleme — halüsinasyon). V03, V05 temiz geçti. Sonuçlar 2 ayrı koşuda birebir aynı çıktı — deterministik, örnekleme gürültüsü değil. Detay: `claude_code_prompt_C_paketi_dataset.md`.*

*9 Temmuz 2026 (V07 eklendi, görev #28, WSL2): `eval_gguf.py`'ye V07 (S41 — iki ardışık anlaşamama → doğrudan eskalasyon, çok-turlu seed) eklendi. 39 senaryo 32/39 (%82), KALDI: E01, E24, V01, V02, V04, V06, V07 = 7 Temmuz WSL2 baseline'ı (32/38) + V07; başka senaryo oynamadı (deterministik tutarlı). V07 doğru YAPISAL nedenle düşüyor: ham wbot_v4'te S41 verisi olmadığından model 2. anlaşılamamada eskale etmek yerine 3. kez netleştiriyor ("Anlayamadım, hangi ürünü arzu edersiniz?") — V02/V06 gibi bilinen boşluk, gerçek PASS wbot_v5 (wbot_c_eskalasyon.jsonl merge + retrain) sonrası. E27 yine WSL2'de geçti (platform notu, aşağıda 7 Temmuz).*

*7 Temmuz 2026 (V06 reformülasyonu sonrası, WSL2): V06 kriteri Karar 1'in 3 yapısal öğesine (kaynak atfı + "işaretli" + personel/teyit + yasak-ifade katmanı) sıkılaştırıldı; V04 yasak listesine duygusal-karşılık kalıpları ("kızarmak", "sinirlen-", "bıktım") eklendi (görev #27). KALDI: E01, E24, V01, V02, V04, V06 — V06 artık doğru YAPISAL nedenle düşüyor (yanıt gluten içeren Kremalı Mantar Çorbası'nı glutensiz diye sayıyor + 3 öğenin hiçbiri yok). Tek delta: **E27 bu koşuda GEÇTİ** (31→32) — kriter değişmedi; baseline Jetson'da, bu koşu WSL2'de yapıldı ve E27 yanıtı farklı çıktı (platform/bağlam farkı — wbot_v5 sonrası Jetson eval'inde yeniden görülecek). Geçen E27 yanıtı içerikçe hâlâ sorunlu ("gluten içermeyen ürün bulunmuyor" — yanlış iddia, gevşek E27 kriterinden geçiyor) — madde 5 verisinin (E27'yi de 3-öğe kalıbına yönlendirme) gerekliliğini teyit ediyor. Gerçek V06/E27 PASS doğrulaması wbot_v5 (veri+retrain) sonrası.*

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
| W15 | Ürün açıklaması sonrası soru yok | "Kremalı mantar çorbası nasıl?" → açıklama yapıyor ama "Getireyim mi?" demiyor | wbot_v3 dataseti açıklama+soru örneklerini yeterince içermiyor | ✅ Düzeltildi (wbot_v4 + E19 post-processing — E19 eval'de GEÇİYOR, 4 Temmuz 2026) |
| W16 | Alerji yanıtı anlamsız | "Süt alerjim var, ne yiyebilirim?" → "Süt ürünü içermeyen menüümüz var mı?" (model kendine soruyor) | Yetersiz alerji+öneri kombinasyon örneği | ✅ Büyük ölçüde düzeltildi (wbot_v4 B paketi — V03/V05 geçiyor; kalan parça V06 alerjen halüsinasyonu, C paketi kapsamında) |

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
- Piper TTS — MIT rhasspy/piper binary (`<project>/piper/`, aarch64, `scripts/setup_piper.sh` ile kurulu), wbot_tr.onnx + tr_TR-dfki-medium.onnx
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

**Önkoşul:** ✅ Jetson deploy tamamlandı. 32-senaryo eval 31/32 (%96) yapıldı. Gerçek boşluklar tespit edildi.

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

> **Not — C paketi kapsam dışı (4 Temmuz 2026'da revize edildi):** ~495
> rakamı gerçek bir hedef değildi, yalnızca "~1100 hedef − 605 üretilen"
> aritmetik kalıntısıydı. wbot_v4 eval sonuçlarıyla gerçek kapsam netleşti
> ve ~175-185 kayıt + 2 ayrı kod görevine çıktı: S34/V02 (~20), S41/V07
> (~20), anti-hallüsinasyon (~100), küfür genişletme (~15-20, V04), alerji
> kalıp/doğruluk düzeltmesi (~20-25, E27+V06). S39 ve gürültülü-ortam edge
> case'leri hâlâ kapsam dışı (ön koşulları eksik). Üretim wbot_v4
> S12-guard + kod düzeltmeleri sonrasına ertelendi — bkz.
> [claude_code_prompt_C_paketi_dataset.md](claude_code_prompt_C_paketi_dataset.md).

---

### wbot_v4 Eğitim, GGUF Dönüşümü, Jetson Deploy ve Eval Sonuçları (4 Temmuz 2026) ✅

**Eğitim:** Colab A100, 3 epoch, `train_wbot_v2.py` — adapter + GGUF Drive'a
kaydedildi, yerel makineye ve Jetson'a taşındı; boyutlar Drive metadata'sıyla
byte-exact doğrulandı (GGUF 2.497.280.288 byte, adapter zip 246.817.495 byte
→ 6 dosya, `adapter_config.json` LoRA ayarları train_wbot_v2.py ile birebir
eşleşti: r=32, alpha=64, dropout=0.05, 7 target module).

**Deploy:** `Qwen3-4B-wbot_v4-Q4_K_M.gguf` → `/home/emk/models/` (Jetson),
`llama_cpp_backend.py`'deki `_GGUF_FILENAME` wbot_v3→wbot_v4 güncellendi.

**Eval (`eval_gguf.py`, 2 kez çalıştırıldı — birebir aynı sonuç, deterministik):**

| Koşu | Sonuç | KALDI |
|---|---|---|
| 32 senaryo (temel) | 30/32 (%93) | E01, E27 |
| 38 senaryo (`--v4-targets`) | 32/38 (%84) | E01, E27, V01, V02, V04, V06 |

**Kazanımlar:** E19 (W15/A1 hedefi) artık GEÇİYOR. V03 (S35/B4), V05
(S37/B5) temiz geçti.

**E01, E27 — wbot_v3→v4 REGRESYONU:** Yeni bulgu değil — wbot_v3'te ikisi de
GEÇİYORDU (31/32'nin parçasıydı). wbot_v4'ün yeni 605 kaydı içindeki bir
etkileşim bu iki dar kalıbı seyreltmiş olabilir. Çözüm veri eklemek değil —
`demo_usb.py`'de zaten var olan post-processing'e (E01 için "?" ekleme
zaten mevcut, satır ~1097-1114) benzer, dar/tek-koşullu kod düzeltmesi.

**Kritik metodoloji bulgusu:** `eval_gguf.py`, `LlamaCppBackend.generate_reply()`'i
doğrudan çağırıyor — `demo_usb.py`'nin **Guard 1/2/3**, `_fast_path_reply()`
ve post-processing katmanlarının HİÇBİRİ devreye girmiyor. Bu yüzden:
- **V04 ham eval'de ciddi görünüyor** ("Aptal robot..." → "Size çok
  kızarmak istiyorum, ne yapabilirim?") **ama üründe bu asla çıkmaz** —
  `demo_usb.py`'nin mevcut Guard 3'ü (`_is_offensive`, `_OFFENSIVE_TERMS`
  listesinde "aptal" zaten var) bu girdiyi LLM'e ulaşmadan yakalar. Üretim
  riski düşük, ham model kalitesi sorunu.
- **V01, V06 ve S12/E24 gerçek, korumasız boşluklar** — hiçbir guard
  bunları karşılamıyor.

**S12 manuel test (`llm.generate_reply()` ile 2 ayrı tetikleyici, Jetson'da):**

| Tetikleyici | Beklenen | Gerçek | Sonuç |
|---|---|---|---|
| "Hayır, başka istemiyorum, bu kadar." (ürün adı yok, saf kapanış) | Özet+toplam+onay sorusu | "Hemen hazırlıyorum efendim, afiyet olsun." | S12 hiç tetiklenmedi — eski (S12-öncesi) davranış |
| "Bir de ayran, başka istemiyorum." (eğitilmiş ekle+kapat kalıbı, `gen_karmasik.py`) | Özet+toplam+onay sorusu | Özet+toplam ÜRETTİ, ama onay sorusu YOK, doğrudan "Afiyet olsun" | S12 eğitilmiş kalıpta bile eksik |

**Kök neden şüphesi:** `gen_karmasik.py`'nin assistant örnekleri özet+onay
sorusunu ve kapanışı aynı turda birleştirmiş olabilir, TUR 2'de ayrı bir
onay-sonrası kapanış üretmemiş olabilir — bu, veriye bakılarak
doğrulanmalı (bkz. Sıradaki Görevler #4).

**Runtime guard kararı:** Veri eklemek (E01/V01/V04 tecrübesi) tek başına
güvenilir değil — S12 için de `demo_usb.py`'de `OrderTracker`'ın hesap
override'ıyla aynı desende deterministik bir guard tasarlandı (TUR 1:
özet+toplam+onay, TUR 2: toplamsız afiyet olsun). **İlk guard taslağında
mantık hatası bulundu:** `_is_closing_signal`'ın kendi ürün-eşleşme kontrolü
("cümlede menü ürünü var mı?"), tam olarak hedef senaryoda ("Bir de ayran,
başka istemiyorum." — ayran YENİ eklenen ürün) guard'ı yanlışlıkla devre
dışı bırakıyordu. Ayrıca statik kod analizi, `detect_order()`'ın bu tür
ekle+kapat cümlelerinde `_CANCEL_VERBS` içindeki "istemiyorum" yüzünden
yanlışlıkla cancel dalına düşüp erken `return` ettiğini, ayranın hiç sepete
eklenmediğini gösteriyor — bu ayrı, ön koşul bir bug, guard'dan ÖNCE
doğrulanmalı/düzeltilmeli. Düzeltilmiş tasarım: `claude_code_prompt_C_paketi_dataset.md`.

**Seed (uygulandı — 6 Temmuz 2026):** `Llama()` çağrısına `seed=0xFFFFFFFF`
(örtük varsayılan, açıkça yazılmış) eklendi. WSL2 + Jetson A/B testi (4
karşılaştırma): seed'siz 2 koşu bit-bit aynı (determinizm teyit), Jetson
baseline 30/32 E01+E27 birebir korundu, `0xFFFFFFFF` baseline'la bit-bit
aynı, `seed=42` ise ~26 senaryoda yanıtı değiştirip ortama göre tutarsız
sonuç verdiği için REDDEDİLDİ. Detay: METODOLOJI.md "Seed" notu.

---

## W11 Kanonik Prompt Revizyonu (wbot_v5) — 10 Temmuz 2026

**Kritik not — düzeltme training'e değil `_SYSTEM_TEMPLATE`'e uygulandı:**
Faz A incelemesi, `train_wbot_v2.py::build_hf_dataset()`'in
`short_prompt=True` (varsayılan, wbot_v4 eğitiminde kullanıldı) olduğunda
dataset kayıtlarının `system` alanını tamamen yok sayıp kendi
`_SYSTEM_SHORT` sabitiyle değiştirdiğini ortaya çıkardı. Bu yüzden W11'in
gerçek hedefi hep `llama_cpp_backend.py::_SYSTEM_TEMPLATE` (+
`qwen3_backend.py` eşleniği) oldu — dataset'in `system` alanı
DEĞİŞTİRİLMEDİ (W1-W16'nın tamamı zaten aynı desenle, yalnızca bu
template değiştirilerek düzeltildi ve eval'de doğrulandı; görev #24'ün kök
neden analizi ile aynı emsal).

**Kapanış kuralı değişikliği:** "Başka istemiyorum"/"Bu kadar" gibi kapanış
ifadelerinde artık ÖNCE özet+toplam+"Onaylıyor musunuz?" (bu turda toplam
SÖYLENİR), müşteri onayladıktan SONRA yalnızca "Afiyet olsun!" (toplam
TEKRARLANMAZ) — S12 Karar 2 ile hizalandı, görev #24'ün kök nedenini
giderir. `llama_cpp_backend.py::_SYSTEM_TEMPLATE` ve
`qwen3_backend.py::_build_system_prompt()` aynı anda güncellendi. Gerçek
ölçüm (menu.yaml çözülmüş, llama-cpp-python gerçek tokenizer): 7533
karakter, **2909 token** (eski paragraf ~2850 tok idi, +59 tok).

**Yan bulgu — `_MAX_HIST_CHARS` context-overflow bug'ı (bu görevde bulundu
ve düzeltildi):** Token bütçesi doğrulaması, `_MAX_HIST_CHARS=4000`
değerinin eski/yanlış bir varsayıma (kod yorumundaki "~2100 tok sistem
promptu") dayandığını ortaya çıkardı. Ampirik doğrulama (gerçek dataset
içeriği + gerçek tokenizer ile worst-case geçmiş inşa edilip tokenlendi):
wrapped sistem promptu 2922 tok, worst-case tam prompt **4829 tok** —
n_ctx(4096)'yı 733 tok aşıyor. `llama-cpp-python`'ın kurulu kaynak kodu
(`llama.py`, `Llama.create_completion`: `if len(prompt_tokens) >=
self._n_ctx: raise ValueError(...)`) bu durumda **sert bir çökmeye** yol
açıyor — sessiz kalite düşüşü değil, `generate_reply()` çağrısının
yakalanmamış bir `ValueError` ile patlaması. `_MAX_HIST_CHARS` **1000**'e
çekildi; aynı ampirik testte (gerçek dataset içeriğiyle) tampon **+332
tok** (200 tok risk eşiğinin üstünde, güvenli). Yalnızca
`llama_cpp_backend.py` düzeltildi — `qwen3_backend.py`'deki ayrı
`_MAX_HIST_CHARS=12000` (farklı backend, n_ctx=4096 kısıtına tabi değil)
kapsam dışı bırakıldı.

**wbot_v5_train.jsonl:** `wbot_v4_train.jsonl` (3605) + C paketi
(`wbot_c_modifikasyon_sonrasi` 20, `wbot_c_kufur_genisletme` 18,
`wbot_c_alerji_kalip` 24, `wbot_c_eskalasyon` 20,
`wbot_c_anti_hallusinasyon` 100 = 182) = **3787 kayıt**,
`scripts/rebuild_wbot_v5_train.py` (`random.Random(2028).shuffle`).
Kayıtların `system` alanına dokunulmadı (short_prompt=True eğitiminde
etkisiz, gereksiz risk alınmadı).

**Doğrulama:** `audit_dataset.py` → 0 ihlal (3787/3787 temiz). Tam pytest
süiti → **490/490 PASS** (WSL2, `.venv`; native Windows'ta 3 test —
piper subprocess, shebang script Windows'ta çalıştırılamıyor — ortam
kaynaklı, ilgisiz).

**Retrain kapsam dışı** — kullanıcı Colab'da aşağıdaki komutu (birebir,
`--full-prompt` YOK) çalıştıracak:

```bash
python robot_waiter_ai/training/train_wbot_v2.py \
    --dataset wbot_v5_train.jsonl \
    --output-dir <OUTPUT_DIR> \
    --epochs 3 \
    --run-eval
```

GGUF dönüşümü + Jetson deploy ayrı bir görevde — o görevde
`_SYSTEM_TEMPLATE`'in (bu görevde güncellenmiş) hâli ile yeni GGUF AYNI
ANDA senkronize edilecek. Jetson'a bu görevde `git pull` YAPILMADI (GGUF
hâlâ wbot_v4, prompt+ağırlık uyumsuzluğunu önlemek için).

**Backlog (düşük öncelik, ayrı görev):**
- 4 farklı sistem promptu versiyonu tespit edildi (`_SYSTEM_TEMPLATE`,
  `wbot_finetune_v1.jsonl`, `_SYSTEM_SHORT`, 1773-kr
  `inject_system_and_merge.py` varyantı) — tekilleştirme ayrı görev.
- `_SYSTEM_TEMPLATE` kalori/pairs_with/hitap-tekrarı/karşılama-soru-işareti
  kuralları içeriyor ama dataset bunları örneklemiyor — ayrı görev.
- 1231 kayıtlık kısa-varyant sistem promptu teknik borcu — training'e
  etkisi yok (short_prompt=True), düzeltme ertelendi.
- **`_trim_history()` eval kapsamı dışı (10 Temmuz 2026 ölçümü):**
  `eval_gguf.py`'deki tüm çok-turlu senaryolar kasıtlı kısa (en uzunu E33,
  294 kr/7 mesaj) — hiçbiri `_MAX_HIST_CHARS=1000` sınırını zorlamıyor,
  trim hiç egzersiz edilmiyor. Gerçek restoran diyaloglarında (10+ tur,
  ör. uzun masa siparişi + değişiklik + iptal + tekrar sipariş + hesap) bu
  sınıra ulaşılıp ulaşılmayacağı ve trim tetiklendiğinde hangi bilginin
  (özet turu, alerji notu vb.) kaybolduğu test edilmiyor. Öneri:
  `eval_gguf.py`'ye veya ayrı bir `test_trim_history.py`'ye, kasıtlı olarak
  1000 karakteri aşan sentetik bir uzun-konuşma senaryosu eklenmeli — hem
  trim'in doğru çalıştığını (crash yok) hem de neyin kesildiğini (ideal
  olarak en eski, en az kritik tur) doğrulamak için. Gürültülü-ortam saha
  testinden (görev #8) bağımsız, ayrı bir öncelik.

---

## Jetson Senkron + Erken Doğrulama (wbot_v5, retrain-öncesi) — 10 Temmuz 2026

**Jetson senkron:** `git pull` ile `f6e7341 → 18c429a` (fast-forward,
temiz). İçerik doğrulaması `git show HEAD:<path> | md5sum` ile yapıldı
(checkout satır-sonu farklılıklarından — WSL2 `/mnt/c` CRLF, Jetson native
LF — bağımsız bir yöntemle): `llama_cpp_backend.py`, `qwen3_backend.py`,
`wbot_v5_train.jsonl` üçü de Jetson/WSL2/GitHub arasında birebir aynı.
GGUF'a dokunulmadı (hâlâ wbot_v4).

**Erken doğrulama (mevcut wbot_v4 GGUF + YENİ prompt, retrain'den ÖNCE):**

32 senaryo: **29/32 (%90)**, KALDI: E19, E24, E16 (baseline: 29/32, KALDI:
E01, E24, E27)

| Senaryo | Önce | Şimdi | Değişim |
|---|---|---|---|
| E01 | KALDI | GEÇTİ | ✅ İyileşme |
| E27 | KALDI | GEÇTİ | ✅ İyileşme |
| E24 | KALDI | KALDI | Değişmedi (beklenen — retrain gerekiyor) |
| E19 | GEÇTİ | KALDI | 🔴 Regresyon |
| E16 | GEÇTİ | KALDI | 🔴 Regresyon (check-artefaktı, aşağıda) |

39 senaryo (`--v4-targets`): **32/39 (%82)**, KALDI: E19, E24, E16, V01,
V02, V06, V07 (baseline: 32/39, KALDI: E01, E24, V01, V02, V04, V06, V07)

| Senaryo | Önce | Şimdi | Değişim |
|---|---|---|---|
| E01 | KALDI | GEÇTİ | ✅ İyileşme |
| V04 | KALDI | GEÇTİ | ✅ İyileşme |
| E24, V01, V02, V06, V07 | KALDI | KALDI | Değişmedi (beklenen) |
| E19 | GEÇTİ | KALDI | 🔴 Regresyon |
| E16 | GEÇTİ | KALDI | 🔴 Regresyon (check-artefaktı) |

**Önemli:** V serisinde (V01-V07) hiçbir YENİ regresyon yok — regresyon tam
olarak E19+E16 ile sınırlı, iki koşuda da (32 ve 39 senaryo) aynı, birebir
aynı yanıt metinleriyle (run tekrarında bit-exact doğrulandı).

**E19 regresyonu (AKTİF, düzeltilmedi):** Soru "Kremalı mantar çorbası
nasıl bir şey?" → yanıt "...Sıcak servis edilir mi?" (kural: "Getireyim
mi?" veya "İster misiniz?" ile bitmeli). Kök neden: W11'in kapanış
paragrafı değişikliği, `_SYSTEM_TEMPLATE`'in BAŞKA bir yerindeki
ürün-açıklaması kuralının modelde tutunmasını dolaylı olarak zayıflattı
(paragraf sırası/konumu değiştiğinde token kayması — aynı promptun
ilgisiz görünen bir bölümünü etkileme riski, klasik bir prompt-mühendisliği
yan etkisi). İzole, tekrarlanabilir (32 ve 39 senaryo koşularında birebir
aynı), V serisine yayılmamış. **Kritik: bu, retrain ile KENDİLİĞİNDEN
DÜZELMEYECEK** — `_SYSTEM_TEMPLATE` training pipeline'ında
(`short_prompt=True`, `_SYSTEM_SHORT` kullanılıyor) hiç yer almıyor;
wbot_v5 GGUF'u deploy edildikten sonra da inference'ta AYNI
`_SYSTEM_TEMPLATE` kullanılacağından E19'un aynen kalması beklenir. Ayrı
bir prompt-mühendisliği görevi gerekiyor (ör. ürün-açıklaması kuralını
güçlendirme veya paragraf sırasını yeniden düzenleme). Öncelik: orta
(Jetson henüz prod'da değil, ama deploy öncesi ele alınmalı).

**E16 — check kırılganlığı (model değil, test hatası):** `eval_gguf.py`'nin
`_not_contains("istersin")` kontrolü word-boundary kullanmıyor —
"istersiniz" (doğru, kurala uygun kapanış) içindeki "istersin" alt-dizesini
yanlışlıkla ihlal sayıyor. Model davranışı doğru; düşük öncelik, ayrı küçük
bir düzeltme (regex'e `\b` eklemek yeterli).

**Metodoloji notu — determinizm kapsamı:** `seed=0xFFFFFFFF` bit-exact
garantisi TAM-DİZİ tekrarına özgü — 32 senaryonun tamamını AYNI sırayla iki
kez çalıştırınca birebir aynı sonuç (bu oturumda 32-senaryo koşusu ikinci
kez tekrarlanıp E19/E16 dahil tüm yanıtların bit-exact olduğu doğrulandı).
Ama E19'un girdisini İZOLE (taze model yüklemesinden sonra TEK başına ilk
çağrı olarak) çalıştırınca FARKLI (kurala uyan) bir yanıt geldi — RNG
durumu `Llama()` nesnesi üzerinde art arda yapılan her `generate_reply()`
çağrısıyla ilerliyor, yani bir çıktı yalnızca girdiye değil dizideki çağrı
POZİSYONUNA da bağlı. Görev #23'ün determinizm doğrulaması TAM diziyi
karşılaştırarak yapılmıştı (geçerliliğini korur); izole tekil senaryo
tekrarı bu garantinin kapsamında DEĞİL. İleride tek bir senaryoyu debug
ederken hatırlanmalı — "izole çalıştırdım, farklı çıktı geldi" tek başına
bir regresyon kanıtı değildir.

**Colab hazırlığı:** `robot_waiter_ai/training/wbot_v5_colab_training.ipynb`
oluşturuldu — `wbot_v4_colab_training.ipynb`'nin birebir kopyası, yalnızca
dataset yolu (`wbot_v5_train.jsonl`, 3787 kayıt beklentisi), eğitim/GGUF
çıktı yolları (`wbot_v5_output`, `wbot_v5_merged`,
`Qwen3-4B-wbot_v5-Q4_K_M.gguf`) güncellendi. Hiperparametreler (LoRA
r=32/alpha=64/dropout=0.05, lr=2e-4, batch=1, grad_accum=8,
max_seq_len=800, epochs=3) v4 ile birebir aynı; `--full-prompt`
KULLANILMIYOR (bilerek). Kullanıcı gözden geçirip Colab'a yüklemeden önce
commit edildi, henüz Colab'da çalıştırılmadı.

---

## TTS — Piper Garble Fix + Telaffuz Sözlüğü + Checkpoint Overfit Testi (11-13 Temmuz 2026)

**Bağlam:** Kullanıcı özel W-BOT sesinin (`wbot_tr.onnx`) bazı cümlelerde
"bulanık/net anlaşılmıyor" geldiğini bildirdi. Araştırma **iki bağımsız
sorun** ortaya çıkardı — ikisi de düzeltildi — ve üçüncü bir hipotez
(overfit) test altyapısı hazırlandı ama kullanıcı aksiyonu bekliyor.

### 1) Piper garble kök-nedeni — pip piper-tts 1.4.2 (GPL) fonemizasyon bozukluğu

Faz A envanteri (salt-okunur, `WBOT_PIPER_SES_ENVANTERI_FAZA.md`) sesin
eğitim hattının uçtan uca tamamlandığını doğruladıktan sonra, kalite A/B'si
üretilirken **her iki ses de** (custom + stok) garble çıktı. `--debug`
fonem logu kök nedeni netleştirdi: `.venv-llm`'deki pip paketi
`piper-tts` **1.4.2** (proje: OHF-voice/piper1-gpl, **GPL-3.0**) Türkçe
espeak fonemizasyonunu bozuyor — temiz UTF-8 girdide bile İngilizce'ye
düşüyor (örnek: "Künefede fındık ve süt var." → `kwˈɔːtə/plˈʌs/mˈaɪnəs`
gibi çöp fonem, ~120 fonem × normalin 4 katı süre). **Model/eğitim sorunu
DEĞİL** — hem `wbot_tr` hem `dfki-medium` birebir aynı çöp fonemi üretti.

**Fix (commit `18d1f25`, 12 Temmuz 2026):** Arşivlenmiş **MIT rhasspy/piper**
binary'si (`2023.11.14-2`, piper-phonemize tabanlı) `<project>/piper/`
altına kalıcı kuruldu. `tts.py`'nin `_PIPER_BINARY_CANDIDATES`'ı zaten bu
yolu PATH'teki "piper"dan (1.4.2) önce deniyordu — kod değişikliği
gerekmedi, yalnızca binary'yi kurmak yetti. **Karar gerekçesi (Option B —
binary, Option A — pip pinleme yerine):** (1) **Lisans:** MIT vs GPL-3.0,
ticari ürün için belirleyici; (2) 1.4 öncesi piper-tts `piper-phonemize`
gerektirir, **Windows wheel'i yok** → pip pinleme dev makinede imkânsız;
(3) binary kendi espeak-ng-data + onnxruntime'ını taşır, sürüm sabit,
exe-göreli espeak bulur (cwd bağımsız — test edildi).

**Model fallback zinciri değişti:** `tr_TR-fahrettin-medium/high` artık
HuggingFace'ten kaldırılmış (indirilemiyor) → **`tr_TR-dfki-medium`** (MIT,
`rhasspy/piper-voices`'ta kalan tek tr_TR stok ses) — zaten `wbot_tr`'nin
fine-tune tabanı olduğundan "custom vs stok" kıyası doğrudan anlamlı.
`scripts/setup_piper.sh` eklendi: arch algılar (aarch64/x86_64), binary+dfki
indirir, idempotent, `Jetson`'da da doğrulandı.

**Doğrulama:** Dev'de `PiperTTS()` → binary=`<project>/piper/piper.exe`,
model=`wbot_tr.onnx`, sentez ~1.85sn (eskiden bozukta ~8sn) doğru fonem.
Jetson'da (`192.168.1.67`) `git pull` + `setup_piper.sh` sonrası aynı
doğrulama tekrarlandı — MIT binary zaten Jetson'da mevcuttu (Kas 2023'ten
kalma), production TTS'i **hiç garble olmamıştı** (yalnızca dev'de bozuktu,
1.4.2'ye düşüyordu); Jetson'a `wbot_tr.onnx` (60.6 MB) ayrıca scp'lendi.
`tts_ab_out/wbot_custom/` (10 cümlelik kör A/B) düzeltilmiş binary ile
yeniden üretildi — artık geçerli.

### 2) Yabancı-yazımlı kelime telaffuz sözlüğü

Fix'ten bağımsız ikinci sorun: espeak-tr, İngilizce YAZIMLI kelimeleri
Türkçe harf kurallarıyla okuyor (`cheesecake` → `dʒheesedʒakˈɛ` "cihiyseceyke",
`cappuccino` → `dʒapːudʒːinˈɔ`). Menü taraması (`menu.yaml`, 10 ürün)
**hepsinin Türkçe yazımlı** olduğunu doğruladı (mercimek çorbası, künefe,
lazanya, tiramisu — sorunsuz) → sözlüğün değeri menüde değil, LLM'in serbest
konuşmasında/önerisinde geçebilecek kafe terimlerinde.

**Uygulama (commit `338ef7a`, 13 Temmuz 2026):** `robot_waiter_ai/speech/pronunciation.py`
— 30 girişlik İngilizce/yabancı-yazım → Türkçe-fonetik-yazım haritası
(cheesecake→çizkeyk, cappuccino→kapuçino, latte→late, croissant→kruvasan...),
her hedef `piper --debug` ile doğru fonemlediği teyit edildi. Kelime-sınırı
regex `(?<!\w)(KEY)(['’]\w+)?(?!\w)` — yalnız tam kelime eşleşir (geçmişteki
`_OFFENSIVE_TERMS` "göt"/"götürür" substring hatasının tekrarı önlendi),
Türkçe ek kesme-işaretiyle korunur (cheesecake'i→çizkeyk'i), uzun-önce sıra
(Coca-Cola>cola). `tts.py`'de `PiperTTS._run_piper_blocking` başında —
sentezden hemen önce, kaynağı ne olursa olsun (LLM/fast-path/guard) her TTS
çıktısı kapsanır; yalnız TTS girdisi değişir, ekrana/loglara/OrderTracker'a
giden metin değişmez. 25 yeni test (`test_pronunciation.py`) + **WSL tam
süit 515/515 PASS** (regresyon yok). Dev+Jetson'da doğrulandı.

### 3) wbot_tr overfit hipotezi — checkpoint kör A/B (⏳ kullanıcı aksiyonu bekliyor)

Google Drive araştırması (`wbot-tts/checkpoints/`) kesin epoch bilgisini
ortaya çıkardı: dfki tabanı **epoch 5679** → deployed `wbot_tr.onnx`
**epoch 6799** (~1120 fine-tune epoch, ~11 saat T4, 320 cümle/13 dk ses
üstüne). Bu, kullanıcının "bazen bulanık" şikâyetiyle örtüşen klasik
aşırı-öğrenme imzası olabilir (korpus cümlelerinde net, görülmemiş
cümlelerde bulanık). Kıyas için yerel terk edilmiş CPU denemesi de
incelendi: `lightning_logs/version_2`, sıfırdan, batch 4, **epoch 134'te
bırakılmış**, loss yakınsamamış — gerçek modelle karıştırılmamalı.

**Colab loss eğrisi kayıp:** notebook Drive'a yalnız checkpoint kopyalıyor,
`lightning_logs/tfevents`'i değil — val_loss'un epoch 6799'da platoya
varıp varmadığı doğrulanamıyor. Bir sonraki eğitim için plan (kod
yazılmadı, salt öneri): (1) tfevents'i de periyodik Drive'a kopyala, (2)
val_loss'u düz metne append et (epoch,val_loss,loss_gen_all), (3) export
edilen epoch'u `onnx.json`'a/yan dosyaya yaz, (4) max-epoch yerine best-val
checkpoint export'unu değerlendir.

**Test altyapısı hazır, kullanıcı aksiyonu bekliyor:** Yerel checkpoint
export'u **imkânsız** (845 MB × 4 checkpoint private Drive'da, MCP indirme
kanalı yalnız base64 döndürüyor — tool sınırının kat kat üstünde; ayrıca
`piper_train`/`pytorch-lightning` yerelde kurulu değil). Bunun yerine:
- **Colab export hücresi** hazırlandı — `epoch=5799/6099/6399/6799`
  checkpoint'lerini ONNX'e export edip zip olarak indirir (kullanıcının
  Colab oturumunda Hücre 1-2-3 çalıştıktan sonra yapıştırıp koşması yeterli).
- **Yerel A/B üretici** (`build_checkpoint_ab.py`) yazıldı ve mevcut
  modellerle (deployed=e6799 + dfki + insan referans) **doğrulandı**: 12
  görülmemiş cümleyi (aynı `tts_ab_out/wbot_unseen/` seti, telaffuz sözlüğü
  uygulanmış üretim yoluyla) her mevcut checkpoint'le sentezler, kör N'li
  A/B (Aday 1..N karışık, cevap anahtarı altta) + süre/RMS/hız sağlık
  tablosu üretir. Eksik checkpoint'ler sayfa başlığında otomatik işaretlenir.

**Sıradaki adım (kullanıcı):** Colab hücresini çalıştır → zip'i
`tts_ab_out/_ckpt_models/`'e aç → generator'ı tekrar koştur → tam kör 4'lü
sayfa (5799/6099/6399/6799 yan yana) hazır olur. Kalite yorumu
yapılmayacak — karar kulakla.

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
| 7 | E19 post-processing fix — açıklama yanıtı "?" ile bitmiyorsa "Getireyim mi?" ekle | 🟡 Orta | ✅ Tamamlandı — `demo_usb.py` satır ~1097-1114'te mevcut, E19 eval'de GEÇİYOR |
| 8 | Gürültülü ortam testi (restoran müziği + kalabalık) | 🟡 Orta | ⏳ Bekliyor |
| 9 | wbot_v4 dataset üretimi — A paketi (490) + B paketi (115) = 605 yeni kayıt | 🟢 Düşük | ✅ Tamamlandı — 3 Temmuz 2026 |
| 10 | wbot_v4 eğitimi — Dataset: `wbot_v4_train.jsonl` (3605 kayıt), Notebook: `wbot_v4_colab_training.ipynb`, Script: `train_wbot_v2.py`, Çıktı: `Qwen3-4B-wbot_v4-Q4_K_M.gguf` (Colab A100, 3 epoch) | 🔴 Kritik | ✅ Tamamlandı — 4 Temmuz 2026, adapter+GGUF Drive metadata ile byte-exact doğrulandı |
| 11 | Sistem promptu tutarsızlığı fix (audit_dataset.py 2 yeni kural + 4 gen script + 455 kayıt) | 🔴 Kritik | ✅ Tamamlandı — 3 Temmuz 2026 |
| 12 | Loglama sistemi — demo_usb.py'e oturum loglama (ses + metin + sipariş geçmişi); amaç: hukuki koruma (müşteri itirazları) + gelecekteki yeniden eğitim verisi; kapsam: session JSON (masa no, timestamp, konuşma, sipariş snapshot) + WAV kaydı | 🟡 Orta | ✅ Tamamlandı — 18 Temmuz 2026, commit `7fec6be`. `robot_waiter_ai/session/session_logger.py` (SessionLogger, append-only + crash-safe). Disk düzeni: `data/sessions/<YYYY-MM-DD>/<session_id>/session.json` + `turn_NNN_user.wav`. Ana döngüdeki TÜM yanıt yolları kapsandı (Guard 1/2/3, S12 TUR1/TUR2, fast-path, hesap, ana LLM akışı). 30 gün retention (`cleanup_old_sessions`, run_demo başlangıcında). `data/sessions/` gitignore'lu. Manuel doğrulama + tam süit 525/525 PASS |
| 13 | Senaryo planlaması tamamlandı (S01-S41, SENARYO_PLANI_FAZ1.md) | 🔴 Kritik | ✅ Tamamlandı — 3 Temmuz 2026 |
| 14 | eval_gguf.py — V01-V06 hedef senaryoları eklendi (--v4-targets) | 🔴 Kritik | ✅ Tamamlandı — 3 Temmuz 2026 |
| 15 | W16 ve S12 davranış kararları verildi | 🟡 Orta | ✅ Tamamlandı — 3 Temmuz 2026 |
| 16 | E24 eval revizyonu (S12 koşulsuz özet akışına göre) | 🟡 Orta | ✅ Tamamlandı — 6 Temmuz 2026. E24 çok-turluya çevrildi (köfte siparişi seed'li) ve PASS kriteri S12 Karar 2'ye hizalandı: özet+toplam ("toplam"+"240") + onay sorusu ("?" ile bitiş). Eski kriter ("afiyet VAR, toplam YOK") S12-öncesi politikayı ödüllendiriyordu. **Yeni baseline (Jetson, wbot_v4): 32 senaryo 29/32 (%90), KALDI: E01, E24, E27; `--v4-targets` 38 senaryo 31/38 (%81)** — skor düşüşü model regresyonu DEĞİL, ölçütün doğrulanması: ham model W11 prompt kuralı nedeniyle E24'te bilerek KALIYOR (V02 gibi bilinen boşluk), üretimde S12 guard (görev #22) karşılıyor; W11 kanonik prompt revizyonu (wbot_v5) sonrası ham modelde de geçmesi beklenir |
| 17 | Eval: V01-V06 hedeflerini ana listeye taşı (wbot_v4 sonrası) | 🟢 Düşük | ⏳ Bekliyor |
| 18 | Jetson deploy + eval (wbot_v4) — `eval_gguf.py` 30/32 (%93), `--v4-targets` 32/38 (%84) | 🔴 Kritik | ✅ Tamamlandı — 4 Temmuz 2026, detay yukarıda "wbot_v4 Eğitim, GGUF Dönüşümü, Jetson Deploy ve Eval Sonuçları" bölümünde |
| 19 | wbot_v4_train.jsonl birleştirme (3605 kayıt, 0 ihlal, seed=2027) | 🔴 Kritik | ✅ Tamamlandı — 3 Temmuz 2026 |
| 20 | C paketi görev tanımı — S34/V02 + S41/V07 + anti-hallüsinasyon + küfür genişletme + alerji kalıp düzeltmesi (~175-185 kayıt + 2 kod görevi); üretim wbot_v4 sonrasına ertelendi | 🟢 Düşük | ✅ Tamamlandı — 4 Temmuz 2026, bkz. `claude_code_prompt_C_paketi_dataset.md` |
| 21 | `detect_order()` testi — ekle+kapat cümlelerinde (`"Bir de ayran, başka istemiyorum."`) `_CANCEL_VERBS` yüzünden cancel dalına yanlış düşüp düşmediği | 🔴 Kritik | ✅ Tamamlandı — 5 Temmuz 2026, commit a82dcf3. Bug WSL2'de gerçek OrderTracker ile doğrulandı ve düzeltildi. Kapsam sanılandan genişti: `gen_karmasik.py`'nin 6 eğitilmiş ekle+kapat kalıbından 5'i etkileniyordu (#1 cancel dalı bug'ı, #2/#3/#4/#6 sipariş fiili içermediği için sessiz no-op; yalnızca "alayım" içeren #5 çalışıyordu). Çözüm: `_CLOSING_NEG_RE` ("başka (bir şey) istemiyorum/istemem" kapanış kalıbı cancel sayılmaz) + `_ADD_MARKERS_RE` (fiilsiz ekleme kalıpları: "bir de X", "ayrıca", "son olarak", "bir X daha", "X daha olsun"). "X olsun" modifikasyon çakışması (S34/V02 — "Et Döner soğansız olsun." döneri ikiletiyordu) ayrıca test edilip düzeltildi: "olsun" tek başına ekleme değil. 15 kalıcı test: `robot_waiter_ai/tests/test_order_tracker.py` (15/15 PASS) |
| 22 | S12 runtime guard uygulaması (düzeltilmiş tasarım) — `demo_usb.py`'ye TUR 1 (özet+toplam+onay) + TUR 2 (toplamsız afiyet olsun) deterministik guard | 🔴 Kritik | ✅ Tamamlandı — 5 Temmuz 2026. Ana döngü sıralaması: Guard 1/2/3 → `detect_order()` (öne taşındı) → TUR 2 → TUR 1 → fast-path → LLM. `_is_closing_signal()` düzeltilmiş tasarıma uygun: ürün eşleşmesi yürütmez, `detect_order()` sonrası `order_tracker.items`'a güvenir. Saf veda + dolu sepet ("Teşekkürler." — sepette ürün varken) de TUR 1'e yönlenir (S12 koşulsuz özet; eskiden ≤5 kelimelik vedalar fast-path'e yutulup sepet özetlenmeden kapanıyordu). TUR 2 onayı: sabit "Afiyet olsun!" + `order_tracker.reset()` + `pending_reset`. 36 test: `robot_waiter_ai/tests/test_s12_guard.py`. **Bilinen sınırlamalar:** (a) TUR 2 onayı sepeti sıfırladığından hemen ardından gelen "hesap alabilir miyim" isteği `total=0` nedeniyle deterministik hesap şablonuna girmez, LLM'e düşer (onay = oturum sonu varsayımı — kod değişikliği şimdilik gerekmiyor); (b) guard yanıtları LLM history'sine yazılmıyor — TUR 1 özeti sonrası saf "Hayır" reddinde LLM özetten habersiz kalır (görev #16 E24 revizyonuyla birlikte ele alınmalı) |
| 23 | Seed sabitleme — `llama_cpp_backend.py`'nin `Llama()` çağrısına açık seed ekle | 🟡 Orta | ✅ Tamamlandı — 6 Temmuz 2026. `seed=0xFFFFFFFF` uygulandı (örtük varsayılan açıkça yazıldı — davranış değişmedi, dokümante edildi). WSL2 (0.3.31, 5 Temmuz) + Jetson (0.3.23, 6 Temmuz) A/B eval: seed'siz ×2 bit-bit aynı (MD5 eşit, determinizm teyit); Jetson baseline 30/32 KALDI E01+E27 birebir korundu; `0xFFFFFFFF` vs seed'siz iki ortamda da bit-bit AYNI; `seed=42` iki ortamda da FARKLI (~26 senaryoda yanıt değişti, WSL2'de E16'yı Jetson'da E19'u bozdu — ortama göre tutarsız) ve REDDEDİLDİ. Detay: METODOLOJI.md "Seed" notu |
| 24 | `gen_karmasik.py` veri incelemesi — özet+onay+kapanışın tek turda birleştirilip birleştirilmediği (S12 eğitilmiş kalıpta eksik çıkmasının kök nedeni olabilir) | 🟡 Orta | ✅ Tamamlandı — 6 Temmuz 2026. Şüphe ÇÜRÜDÜ: 150/150 kayıt doğru yapıda (özet "Onaylıyor musunuz?" ile bitiyor + ayrı user-"Evet" turu + ayrı toplamsız "Afiyet olsun" turu; birleşik desen 0). Gerçek kök neden: kanonik sistem promptundaki S12-öncesi kapanış kuralı ("afiyet olsun ile bitir, TOPLAM SÖYLEME") eğitim verisiyle çelişiyor — model iki sinyali harmanlıyor. Guard (görev #22) üretimi zaten koruyor → C paketine veri maddesi EKLENMEYECEK; kalıcı hizalama W11 kural revizyonuyla (wbot_v5 döngüsü, görev #16 ile birlikte). Detay: `claude_code_prompt_C_paketi_dataset.md` kapanış notu |
| 25 | E01/V01 post-processing (C paketi kod görevi 2) — karşılama "?" garantisi + modifikasyon onayında TL fiyat enjeksiyonu | 🟡 Orta | ✅ Tamamlandı — 6 Temmuz 2026. **E01: kod YAZILMADI** — masa başı izleme + WSL2 çalıştırılabilir kanıtla üretimde ZATEN kapalı olduğu doğrulandı: (a) E01'in birebir eval girdisi "Merhaba" (≤2 kelime) fast-path selam şablonuna düşüyor, LLM hiç çağrılmıyor; (b) LLM'e ulaşan uzun karşılamalarda E19 post-processing "Ne istersiniz?" ekliyor — karşılama yanıt dağarcığı ("Hoş geldiniz/Merhaba/Buyurun") veda/fallback filtrelerine takılmıyor. E01 ham-model bilinen boşluğu olarak eval'de kalır. Kök neden adayı: `gen_karsilama.py` BOT_GREET 20 şablondan 3'ü "?"suz (satır 253/254/258) — wbot_v5 veri turunda düzeltilmeli. **V01: uygulandı** — `_modification_price_addition()` saf fonksiyonu + `detect_order()` öncesi/sonrası sepet deltası (`_added_this_turn`): sipariş + modifikasyon sinyali ("soğansız", "acılı", "X olsun" — görev #21 gereği yalnızca SİNYAL, sepet ikilenmez) aynı cümlede ve yanıtta ürünün TL fiyatı yoksa ayrı `_speak()` ile "Şalgam Suyu 50 TL." söylenir (E19 ekleme deseni). S34 turlarında delta boş → tetiklenmez (tasarım: not güncellemesinde yeni fiyat söylenmez). E19 "?" kontrolü artık modelin KENDİ yanıt sonuna bakıyor (`_model_reply`) — fiyat eki mükerrer soru eklettirmez; sıralama: model yanıtı → fiyat → soru. Guard sıralaması (Guard 1/2/3 → detect_order → TUR 2 → TUR 1 → fast-path → LLM) değişmedi. 22 kalıcı test: `robot_waiter_ai/tests/test_v01_price_injection.py`; tam süit 431/431 PASS (WSL2). **Yan bulgular (→ görev #26 ile ÇÖZÜLDÜ, 7 Temmuz):** (a) "İyi günler" açılışı fast-path'te veda sanılıyor — `_FAREWELL_TRIGGERS` ve `_GREETING_TRIGGERS`'ın ikisinde de var, veda dalı önce kontrol ediliyor → müşteriye "Tekrar görüşmek üzere" denip oturum kapanıyor; `conversation_active` bağlamıyla ayrıştırılabilir. (b) "Köfte acısız olsun **lütfen**" sepeti ikiliyor — "lütfen" `_ORDER_VERBS` üyesi, görev #21'in "olsun ekleme değildir" kararını deliyor (`detect_order()` seviyesinde önceden var olan boşluk) |
| 26 | V04 runtime guard + görev #25'in iki yan bulgusu (üç dar kod düzeltmesi) | 🟡 Orta | ✅ Tamamlandı — 7 Temmuz 2026. **(1) "lütfen" sepet ikileme (yan bulgu b):** yeni saf fonksiyon `_is_polite_modification()` — tek sipariş tetikleyicisi "lütfen" + modifikasyon sinyali ("acısız", "X olsun"...) + `_ADD_MARKERS_RE` eşleşmesi yok → sepette ZATEN OLAN ürün ikilenmez; ürün sepette yoksa yine eklenir ("Bir köfte lütfen(, acısız olsun)" bozulmadı, "lütfen" `_ORDER_VERBS`'ten çıkarılmadı). 5 test → `test_order_tracker.py` (görev #21'in 15 testi korundu). **(2) "İyi günler" açılış/veda ayrımı (yan bulgu a):** yeni saf fonksiyon `_salutation_intent(text, in_convo)` — çift anlamlı kalıplar (`_AMBIGUOUS_SALUTATIONS` = `_FAREWELL_TRIGGERS ∩ _GREETING_TRIGGERS`: "iyi günler", "iyi akşamlar") taze açılışta (in_convo=False) selam, yerleşik konuşmada veda; tek anlamlı vedalar ("görüşürüz"...) her bağlamda veda. `_fast_path_reply(text, in_convo=...)` + ana döngüde oturum kapatma kararı da aynı fonksiyona bağlandı (`conversation_active` bağlamı). 10 test → yeni `test_fastpath_greeting.py`. **(3) V04 runtime guard (C paketi 4-b):** `_OFFENSIVE_TERMS` ~29 tek-anlamlı terimle genişletildi (gerzek/dangalak/beyinsiz..., kahpe/yavşak/pezevenk..., sikik/amına/yarrak..., "kes sesini"/"kapa çeneni"); substring eşleşme nedeniyle sınır kelimeler bilinçli DIŞARIDA ("hıyar", "adi"→adisyon, "sus"→susamlı, "lan"→olan, "mal"→malzeme, "hayvan", şikâyet dili) — set üstü yorumda belgeli. `_is_offensive()`/Guard 3 davranışı ve history'ye yazmama korundu. 44 test → yeni `test_offensive_guard.py`. Ana döngü sıralaması (Guard 1/2/3 → detect_order → TUR 2 → TUR 1 → fast-path → LLM) değişmedi. Tam süit 490/490 PASS (WSL2). **Yan bulgu (dokunulmadı):** mevcut "göt" terimi substring ile "götürür müsünüz"ü de yakalar — önceden var olan dar yanlış-pozitif, istenirse ayrı işte word-boundary eşleşmesiyle çözülür |
| 27 | C paketi script-tabanlı veri (3 kalem, 62 kayıt) + V06 eval reformülasyonu | 🟡 Orta | ✅ Tamamlandı — 7 Temmuz 2026. **Veri (hepsi kanonik 5460 sistem promptu, audit 0 ihlal, ≥%10 elle örneklem; MERGE EDİLMEDİ — wbot_v5 turuna ait):** (1) S34/V02 `gen_modifikasyon_sonrasi.py` → `wbot_c_modifikasyon_sonrasi.jsonl` (20 kayıt, 7-mesajlı: sipariş+fiyatlı onay → AYRI turda modifikasyon → fiyat tekrarsız güncellenmiş onay); (2) V04 küfür `gen_kufur_genisletme.py` → `wbot_c_kufur_genisletme.jsonl` (18 kayıt, 11 tek-seferlik + 7 ısrarlı — S29 3:2 oranı korundu, hafif→ağır şiddet yelpazesi, self-check assert); (3) V06/E27 alerji `gen_alerji_kalip_genisletme.py` → `wbot_c_alerji_kalip.jsonl` (24 kayıt: 12 "var mı" formu E27 + 12 3-öğe pekiştirme, boş-kategori dürüstlüğü dahil, self-check = yeni V06 kriteri). Mevcut gen scriptleri YENİDEN ÇALIŞTIRILMADI (çıktıları v4'e merge edilmişti — mükerrer riski), genişletmeler ayrı script/dosyada. **Eval değişikliği (skoru etkiler):** V06 kriteri 3-öğe kalıbına reformüle edildi (kaynak atfı + "işaretli/işaretlenmiş" + personel/teyit + yasak-ifade katmanı — eski kriter alerjen halüsinasyonunu yakalamıyordu); V04 `_not_contains`'e "kızarmak"/"sinirlen"/"bıktım" eklendi. Reformülasyon sonrası tek koşu (WSL2): **32/38 (%84), KALDI: E01, E24, V01, V02, V04, V06** — V06 doğru yapısal nedenle düşüyor; tek delta E27→GEÇTİ (platform/bağlam farkı + içerikçe hâlâ sorunlu yanıt, dipnot: "LLM Eval Sonuçları"). Süit 490/490 PASS. Kalan C paketi: LLM-API kalemleri (S41+V07, anti-hallüsinasyon ~100) + merge + wbot_v5 retrain |
| 28 | C paketi LLM-API kalemleri (S41 eskalasyon 20 + anti-hallüsinasyon 100 = **120 kayıt**) + V07 eval tanımı — DOĞRULANDI + commit'lendi | 🟡 Orta | ✅ Tamamlandı — 9 Temmuz 2026. Dosyalar bilinmeyen bir oturumdan working-tree'de commit'siz/untracked gelmişti (`git log --all` boş); üçüncü-taraf çıktısı gibi rijit doğrulandı, **veri üretilmedi/yeniden çalıştırılmadı**, sadece doğrula+commit. **S41 (`wbot_c_eskalasyon.jsonl`, 20, çok-turlu netleştirme→eskalasyon):** audit 0; sistem promptu 20/20 kanonik 5460; eskalasyon turu 20/20 "personel"+çağırma içerir, yeni netleştirme sorusu YOK (V07 birebir re-elicit listesine göre 0 ihlal), ton nötr; **benzersiz eskalasyon 20/20** (eşik ≥12), benzersiz netleştirme 16/20 (eşik ≥10), i-mod-N sabit eşleme yok; user girdileri 3 farklı anlaşılamama kök nedenine ayrık (STT-gürültü / alakasız kelime / muğlak konuşma); %25 tam kayıt UTF-8 readback temiz. **Anti-hallüsinasyon (`wbot_c_anti_hallusinasyon.jsonl`, 100, tek-turlu):** audit 0; sistem promptu 100/100 kanonik 5460; **hiçbir yanıtta rakam YOK** (uydurma nicel detay yasağı airtight); **bağımsız menu.yaml mekanik çapraz kontrol** (generator FAB_VOCAB'ı kopyalanmadan, menu.yaml doğrudan parse) → honest=80/grounded=20, izinli-metin-dışı malzeme flag'i 8 ama **hepsi honest deferral bağlamında, 0 grounded uydurma** (fındık/ceviz tuzağı doğru defer); alt-tip S1/S2/S3 = 34/33/33, **alt-tip başına benzersizlik 34/34·33/33·33/33**, global 100/100 benzersiz soru+yanıt, ürün dağılımı 7-14 dengeli; %25 tam kayıt + TÜM 8 "bilgim yok" dönüşü UTF-8 readback temiz. **V07 eval tanımı** (`eval_gguf.py`, working-tree diff): 3 PASS öğesi (personel+çağırma / yeni netleştirme yok / nötr ton) + çok-turlu seed (E24/E31 deseni) dokümandaki taslakla örtüşüyor. **Tek koşu (WSL2, --v4-targets): 39 senaryo 32/39 (%82), KALDI: E01, E24, V01, V02, V04, V06, V07** — #27 WSL2 baseline'ı (32/38) + V07; V07 doğru YAPISAL nedenle düşüyor (ham wbot_v4'te S41 verisi yok → model eskale etmek yerine 3. kez netleştiriyor: "Anlayamadım, hangi ürünü arzu edersiniz?"), gerçek PASS wbot_v5 sonrası. Süit 490/490 PASS. Kalan C paketi: **merge + W11 kanonik prompt revizyonu + wbot_v5 retrain** |
| 29 | W11 kanonik prompt revizyonu (`_SYSTEM_TEMPLATE` kapanış kuralı) + wbot_v5 merge (C paketi 182 kayıt entegrasyonu) | 🔴 Kritik | ✅ Tamamlandı — 10 Temmuz 2026, detay yukarıda "W11 Kanonik Prompt Revizyonu (wbot_v5)" bölümünde. Kapanış kuralı `llama_cpp_backend.py::_SYSTEM_TEMPLATE` + `qwen3_backend.py`'de S12 Karar 2'ye hizalandı (training'e değil — `short_prompt=True` dataset `system` alanını yok sayıyor, W1-W16 emsali). **Yan bulgu:** `_MAX_HIST_CHARS=4000` context-overflow'a yol açıyordu (worst-case 4829 tok, n_ctx 4096'yı 733 tok aşıyor → `llama-cpp-python` `ValueError` fırlatıyor); ampirik doğrulamayla 1000'e düzeltildi (tampon +332 tok). `wbot_v5_train.jsonl`: 3787 kayıt (`scripts/rebuild_wbot_v5_train.py`, seed=2028), audit 0 ihlal, süit 490/490 PASS (WSL2). Retrain kapsam dışı — Colab'da ayrı çalıştırılacak |
| 30 | Jetson senkron + erken doğrulama (retrain-öncesi, mevcut wbot_v4 GGUF + yeni prompt) + wbot_v5 Colab hazırlığı | 🔴 Kritik | ✅ Tamamlandı — 10 Temmuz 2026, detay yukarıda "Jetson Senkron + Erken Doğrulama" bölümünde. Jetson `18c429a`'ya pull edildi, içerik md5/git-blob ile doğrulandı, GGUF'a dokunulmadı. Erken eval: 32 senaryo 29/32 (E01+E27 iyileşti, **E19+E16 yeni regresyon**), 39 senaryo 32/39 (V04 iyileşti, V serisinde yeni regresyon YOK). **E19 aktif/düzeltilmedi** — W11 paragrafının promptun başka bölümünü dolaylı etkilemesi, retrain'le düzelmeyecek, ayrı görev gerekiyor; **E16 muhtemelen check-tasarım yanlış alarmı** (`eval_gguf.py` word-boundary eksik). Metodoloji notu: seed determinizmi tam-dizi tekrarına özgü, izole tekil senaryo karşılaştırması bu garantinin kapsamında değil. `wbot_v5_colab_training.ipynb` oluşturuldu (v4 şablonunun birebir kopyası, dataset/çıktı yolları güncellendi), henüz Colab'da çalıştırılmadı |
| 31 | Piper garble kök-neden + fix — pip piper-tts 1.4.2 (GPL) Türkçe fonemizasyonu bozuk (İngilizce'ye düşüyor), MIT rhasspy/piper binary'sine geçildi | 🔴 Kritik | ✅ Tamamlandı — 11-12 Temmuz 2026, commit `18d1f25`. `<project>/piper/` altına arşivlenmiş MIT binary (`2023.11.14-2`) kalıcı kuruldu (lisans: MIT ticari kullanım için GPL yerine tercih edildi; Windows'ta piper-phonemize wheel'i olmadığından pip-pinleme seçeneği elenmiş). Model fallback: fahrettin (HF'den kaldırıldı) → dfki-medium (MIT). `scripts/setup_piper.sh` ile tekrar-üretilebilir kurulum (arch algılar). Dev + Jetson'da doğrulandı: doğru Türkçe fonem, ~2sn (eskiden bozukta ~8sn) |
| 32 | Yabancı-yazımlı kelime telaffuz sözlüğü — espeak-tr İngilizce yazımlı kelimeleri (cheesecake, cappuccino...) yanlış okuyor | 🟡 Orta | ✅ Tamamlandı — 12-13 Temmuz 2026, commit `338ef7a`. `robot_waiter_ai/speech/pronunciation.py` (30 girişlik harita, kelime-sınırı + Türkçe ek toleranslı regex), `tts.py`'de sentezden hemen önce uygulanıyor (yalnız TTS girdisi, ekrana/loglara dokunmaz). Menü ürünleri hepsi Türkçe yazımlı olduğundan kapsam dışı — sözlük garson sohbetinde geçebilecek kafe terimlerini kapsıyor. 25 yeni test + WSL tam süit 515/515 PASS. Dev+Jetson'da doğrulandı |
| 33 | wbot_tr overfit hipotezi testi (checkpoint kör A/B) — dfki tabanı epoch 5679 → deployed epoch 6799 (~1120 fine-tune epoch, 320 cümle/13 dk), görülmemiş cümlelerdeki bulanıklık aşırı-öğrenme imzasına uyuyor | 🟡 Orta | ⏳ **Kullanıcı aksiyonu bekliyor.** Yerel checkpoint export'u imkânsız (845 MB×4 private Drive, MCP kanalı yalnız base64 döndürüyor — tool sınırını aşıyor); Colab export hücresi hazırlandı (5799/6099/6399 checkpoint'lerini ONNX'e export eder). A/B üretici (`build_checkpoint_ab.py`) yazıldı ve mevcut modellerle (e6799+dfki+insan referans) doğrulandı — 12 görülmemiş cümle, kör N'li, sağlık tablosu. Kullanıcı Colab'da export'u çalıştırıp ONNX'leri `tts_ab_out/_ckpt_models/`'e koyunca tek komutla tam kör 4'lü sayfa üretilecek |

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
[ŞU AN] Jetson demo çalışıyor (wbot_v3, 31/32 %96 eval), wbot_v4_train.jsonl hazır (3605 kayıt)
    ↓
Whisper medium testi + E19 post-processing fix
    ↓
Gürültülü ortam testi (restoran müziği, çoklu konuşmacı)
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