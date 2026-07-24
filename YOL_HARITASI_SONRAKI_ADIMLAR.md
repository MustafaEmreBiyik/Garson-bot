# W-BOT — Dosya Rehberi ve Sonraki Adımlar
**Hazırlanma tarihi:** 24 Temmuz 2026 (patron incelemesi öncesi)

Bu dosya iki şey için var: (1) projedeki durum/plan dosyalarını nasıl
okuyacağını göstermek, (2) şu andan itibaren (patron cihaza baktıktan
sonra tekrar toplanıldığında) nereden devam edileceğini özetlemek.

---

## 1) Bu Dosyaları Nasıl Okumalı

Yeni bir oturuma başlarken (veya araya bir mola girdiğinde) sırayla:

| Dosya | Ne işe yarar | Ne zaman oku |
|---|---|---|
| **PROJE_DURUMU.md** | Ana, en detaylı durum dosyası — her şey burada. Tepedeki "Bir Sonraki Oturum — Hızlı Özet" bölümü çoğu zaman yeterli; detay gerekirse aşağıdaki başlıklara in. | Her zaman ilk oku |
| **Bu dosya** (`YOL_HARITASI_SONRAKI_ADIMLAR.md`) | "Şu an tam olarak nerede kaldık, sırada ne var" — PROJE_DURUMU.md'nin en tepesindeki özetin kısa/aksiyon-odaklı versiyonu | İkinci oku |
| **HATA_TRIYAJ.md** | Bulunan hata/regresyon backlog'u — hangi kod guard'ının hangi sorunu kapattığının kaydı, işlenmemiş yeni bulgular (V05/V06/V07 gibi) | Yeni bir hata/regresyon triyaj edilecekse |
| **TTS_LISANS_ARASTIRMASI.md** | TTS lisans kararları — neden MIT Piper binary, hangi ses modeli, ticari kullanım uygunluğu | Ses/lisans sorusu çıkarsa |
| **SENARYO_PLANI_FAZ1.md** | S01-S41 senaryo tanımları — `eval_gguf.py`'deki eval senaryolarının kaynağı | Yeni bir senaryo/eval eklenecekse |
| **METODOLOJI.md** | Test/eval metodolojisi (seed determinizmi, A/B test kuralları vb.) | Bir eval sonucunu yorumlarken şüphe varsa |
| **PERSONA_TON_FIZIBILITE.md** | Sıcak ses/persona + CPU eş-yaşam fizibilite notu | Persona/ton işine dönülürse |
| **YOL_HARITASI.md** | Daha eski, genel teknik yol haritası — bu dosyayla (SONRAKI_ADIMLAR) karıştırılmasın, o daha çok geçmiş plan kaydı | Nadiren, tarihsel referans için |
| **WBOT_PIPER_SES_ENVANTERI_FAZA.md** | Faz A ses/TTS envanteri raporu | TTS geçmişine bakılırken |

**Kural:** Kod tabanını baştan okumaya gerek yok — PROJE_DURUMU.md ve bu
dosya güncel tutuluyor, oradan devam edilebilir.

---

## 2) Şu Anki Durum (24 Temmuz 2026)

**LLM (Qwen3-4B, wbot_v5):**
- Eğitildi, GGUF'a çevrildi (`Qwen3-4B-wbot_v5-Q4_K_M.gguf`), Jetson'a ve
  dev makineye kopyalandı.
- Jetson'da `eval_gguf.py` ile test edildi: ana 32 senaryo **28/32 (%87)**,
  `--v4-targets` 39 senaryo **32/39 (%82)**.
- **E09 ("Hamburger var mı?") regresyon şüphesi ÇÖZÜLDÜ** — GGUF'ta GEÇİYOR.
- **Production hâlâ v4 kullanıyor** — v5 dosyaları hazır ama koda henüz
  bağlanmadı (bilinçli, doğrulama tamamlanana kadar bekletiliyordu).

**TTS (Piper, wbot_tr → wbot_tr_v2):**
- 970 cümlelik yeni korpusla (694+276 ek) sıfırdan fine-tune edildi,
  ~15.5 saat kesintisiz eğitim, `wbot_tr_v2.onnx` export edildi.
- Jetson'a ve dev makineye kopyalandı (`robot_waiter_ai/models/wbot_tr_v2.onnx`).
- **Production hâlâ v1 (`wbot_tr.onnx`) kullanıyor.**
- Kör A/B testi hazır: `tts_ab_out/wbot_v2_ab/index.html` — **kullanıcı
  dinlemesi/kararı henüz verilmedi.**

**Genel:** İki model de dosya olarak hazır ve deploy edilmiş durumda, ama
**hiçbiri production koduna bağlanmadı**. Bağlama işi, aşağıdaki karar
noktalarından sonra yapılacak.

---

## 3) Sonraki Adımlar

### Şimdi / patron dönmeden önce yapılabilecekler
1. **TTS kör A/B testini dinle** (`tts_ab_out/wbot_v2_ab/index.html`) —
   v1 mi v2 mi daha doğal/net/duygulu karar ver. Cevap anahtarı sayfanın
   altında gizli, önce kör dinle.

### Patron cihaza baktıktan, geri bildirim verdikten sonra
2. **Karar noktası — production'a geçiş:** TTS A/B sonucu + patronun
   geri bildirimine göre:
   - v5 (LLM) production'a bağlanacak mı? (`llama_cpp_backend.py`'deki
     `_GGUF_FILENAME`'i v5'e çevirmek yeterli — kod hazır, sadece bekliyor.)
   - v2 (TTS) production'a bağlanacak mı, yoksa v1 mi kalacak? (`tts.py`'deki
     `_PIPER_MODEL_CANDIDATES` listesi güncellenecek.)
3. **HATA_TRIYAJ.md #5-7 (V05/V06/V07)** — şu an "form doldurulmadı, acil
   değil" durumunda. Patron geri bildiriminde bu senaryolar önemliyse
   triyaj formu doldurulup aksiyon kararı verilmeli.
4. **Gürültülü ortam testi** — hâlâ hiç yapılmadı (restoran müziği/kalabalık
   ortamda wake word + STT kalitesi). Canlı kullanım öncesi kritik.
5. **Barge-in kararı** — 18 Temmuz'da fizibilitesi incelenmiş, echo riski
   nedeniyle ertelenmişti. Patron toplantısında gündeme gelebilir
   (detay: PROJE_DURUMU.md "Uzun Vade / Ertelenmiş" #8).

### Daha ileride
6. Barge-in'e gerçekten geçilecekse: önce ucuz enerji-eşiği prototipi ile
   gerçek donanımda saha testi, doğrudan AEC'ye atlanmamalı.
7. ReSpeaker Mic Array veya benzeri donanımsal AEC değerlendirmesi
   (barge-in kararına bağlı).
8. Fiziksel robot gövdesi entegrasyonu (henüz planlama aşamasında değil).

---

**Not:** Bu dosya bir "canlı" belge değil — belirli bir an (patron
teslimi öncesi) için hazırlanmış bir kesit/özet. Proje ilerledikçe asıl
güncel kaynak yine **PROJE_DURUMU.md** olacak; bu dosya sadece o anki
devir-teslim noktasının kaydı olarak kalsın.
