# W-BOT Hata Triyaj Şablonu

**Amaç:** Demo/test sırasında bulunan her hatayı yapısal bir forma dökmek → muğlak "kötü cevap verdi" şikayetini somut backlog maddesine çevirmek.

**Kullanım:** Her hata için aşağıdaki formu bir kez doldur. Biriktirilen kayıtlar wbot_v4+ veri setiyle birleştirilir.

---

## Hata Formu

```
Tarih:
Ortam: [ ] Jetson demo  [ ] PC simülasyon  [ ] Diğer: ___

GÖZLEM
  Müşteri:  "..."
  W-BOT:    "..."
  Beklenen: "..."

KATEGORİ
  [ ] Kapsam-içi — düzeltilebilir
  [ ] Kapsam-dışı — fallback yeterli (sınırsız girdi uzayı, kabul edilebilir)

KÖK NEDEN (birini işaretle)
  [ ] STT hatası       — Whisper yanlış/eksik transkript üretti
  [ ] Guard eksik      — yanlış metin LLM'e ulaştı, guard kesmedi
  [ ] Prompt yetersiz  — LLM bağlamı kavramadı / kuralı uygulamadı
  [ ] Veri eksik       — bu senaryo eğitim setinde yok/az var
  [ ] Kapsam dışı      — menü dışı soru, kötü niyetli girdi, vb.

AKSİYON
  [ ] Guard ekle/güncelle   → demo_usb.py
  [ ] Prompt güncelle       → llama_cpp_backend.py / qwen3_backend.py
  [ ] Dataset'e ekle        → wbot_v4 (kullanıcı/asistan çifti yaz)
  [ ] STT parametresi ayarla→ stt.py / demo_usb.py
  [ ] Kabul et (fallback)   → açıklama: ___
  [ ] Başka: ___

DATASET ÇIFTI (aksiyon "Dataset'e ekle" ise doldur)
  Kullanıcı: "..."
  Asistan:   "..."

NOT: ___
```

---

## Doldurulmuş Örnekler

### Örnek 1 — LLM menü-dışı ürün uydurdu (acil.md P1)
```
Tarih: 25 Haziran 2026
Ortam: [x] Jetson demo

GÖZLEM
  Müşteri:  "Bana bir tane Adana getir, ama çok acılı olsun."
  W-BOT:    "Elbette, Şalgam Suyu 50 TL. Başka bir şey alır mısınız?"
  Beklenen: "Bu konuda bilgim yok, personelimize sorabilirsiniz."

KATEGORİ  [x] Kapsam-içi — düzeltilebilir

KÖK NEDEN [x] Guard eksik  (Adana menüde yok ama sipariş fiili "getir" vardı → LLM rastgele ürün seçti)

AKSİYON
  [x] Guard ekle/güncelle   → demo_usb.py (Guard 2: _is_off_menu_order)  ✅ Yapıldı
  [x] Prompt güncelle       → sipariş kuralı "menüde yoksa ürün adı/fiyat geçmesin" güçlendirildi ✅ Yapıldı
```

### Örnek 2 — STT 8.4 sn gecikme (acil.md P1)
```
Tarih: 25 Haziran 2026
Ortam: [x] Jetson demo

GÖZLEM
  Müşteri:  "İçinşir." (anlamsız/gürültülü ses)
  W-BOT:    8374ms STT süresi, ardından halüsinasyon yanıt
  Beklenen: Hızlı "Tam anlayamadım" yanıtı

KATEGORİ  [x] Kapsam-içi — düzeltilebilir

KÖK NEDEN [x] STT hatası  (kısa/gürültülü ses → Whisper halüsinasyon döngüsüne girdi)
           [x] Guard eksik (düşük güven tespiti yoktu)

AKSİYON
  [x] STT parametresi ayarla → temperature=0.0, condition_on_previous_text=False ✅ Yapıldı
  [x] Guard ekle/güncelle   → Guard 1: _stt_low_confidence  ✅ Yapıldı
```

### Örnek 3 — V05: Pratik soru, personele yönlendirme yerine genel red (wbot_v5 Jetson eval, 24 Tem 2026)
```
Tarih: 24 Temmuz 2026
Ortam: [x] Jetson demo (eval_gguf.py --v4-targets, GGUF)

GÖZLEM
  Müşteri:  "Tuvalet nerede?"
  W-BOT:    "Bu konuda yardımcı olamıyorum, menü veya sipariş için buradayım."
  Beklenen: "personel" veya "bilgim yok" içeren, personele yönlendiren bir yanıt

KATEGORİ  [x] Kapsam-içi — düzeltilebilir

KÖK NEDEN [x] Prompt yetersiz  (model, S37 "pratik soru → personele yönlendir" kalıbıyla
              E10 "konu dışı red" kalıbını ayırt edemiyor — ikisi de "buradayım" tarzı
              genel redle karışıyor; içerik YANLIŞ değil, sadece beklenen kalıba uymuyor)

AKSİYON
  [ ] Prompt güncelle       → S37/E10 ayrımını netleştirecek örnek/kural (düşük öncelik)
  [ ] Dataset'e ekle        → wbot_v6 turunda değerlendirilebilir
  [x] Kabul et (fallback)   → açıklama: yanıt zararsız/nazik, sadece kalıp eksik; acil değil

NOT: eval kriteri katı ("personel"/"bilgim yok" string eşleşmesi), yanıtın kendisi
     kullanıcıyı yanlış yönlendirmiyor.
```

### Örnek 4 — V06: Glüten alerjisi, 3-öğe zorunlu kalıp eksik (wbot_v5 Jetson eval, 24 Tem 2026)
```
Tarih: 24 Temmuz 2026
Ortam: [x] Jetson demo (eval_gguf.py --v4-targets, GGUF)

GÖZLEM
  Müşteri:  "Glüten alerjim var, ne önerirsiniz?"
  W-BOT:    "Menüde gluten içermeyen bir ürünümüz yok, personelimize danışabilirsiniz."
  Beklenen: "menü bilgilerimize/verilerimize göre" + "işaretli"/"işaretlenmiş" + "personel"/"teyit"
            (3 yapısal öğenin HEPSİ), "kesinlikle güvenli" gibi ifadeler olmadan

KATEGORİ  [x] Kapsam-içi — düzeltilebilir

KÖK NEDEN [x] Veri eksik  (V06'nın 3-öğeli spesifik kalıbı — kaynak atfı + veri-durumu
              ifadesi + personel teyidi — yalnızca 12 örnekle pekiştirilmiş, model kalıbı
              tam öğrenmemiş; verdiği yanıt İÇERİK olarak güvenli/doğru — "kesinlikle
              güvenli" demiyor, personele yönlendiriyor — sadece TAM kalıba uymuyor)

AKSİYON
  [ ] Dataset'e ekle        → wbot_v6 turunda V06 örnek sayısı artırılabilir
  [x] Kabul et (fallback)   → açıklama: yanıt güvenli/doğru, sadece katı kalıp testi geçmiyor; acil değil

NOT: eval kriteri kasıtlı katı (alerjen halüsinasyonunu yakalamak için reformüle edilmişti,
     bkz. eval_gguf.py V06 yorumu) — yan etkisi doğru-ama-farklı-ifadeli yanıtları da eleyebiliyor.
```

### Örnek 5 — V07: İki ardışık anlaşamama, eskalasyon yerine 3. netleştirme (wbot_v5 Jetson eval, 24 Tem 2026)
```
Tarih: 24 Temmuz 2026
Ortam: [x] Jetson demo (eval_gguf.py --v4-targets, GGUF, çok-turlu)

GÖZLEM
  Müşteri:  "Höğ mşş bır dğğ." (2. ardışık anlaşılamayan girdi)
  W-BOT:    "Tam anlayamadım, ne almak istersiniz?"
  Beklenen: "personel" + çağırma/yönlendirme ifadesi, YENİ netleştirme sorusu YOK, nötr ton

KATEGORİ  [x] Kapsam-içi — düzeltilebilir

KÖK NEDEN [x] Veri eksik  (S41 eskalasyon verisi yalnızca 20 kayıt — model, 2. ardışık
              anlaşılamama sinyalini yeterince güçlü öğrenememiş, varsayılan "tekrar
              netleştir" kalıbına dönüyor; yanıt AYRICA yasak "ne almak istersiniz?"
              re-elicit kalıbını birebir içeriyor)

AKSİYON
  [ ] Dataset'e ekle        → wbot_v6 turunda S41 eskalasyon örnek sayısı artırılabilir
  [ ] Guard ekle/güncelle   → alternatif: çok-turlu geçmişte 2. ardışık "anlaşılamadı" tespit
      edilirse deterministik eskalasyon şablonu enjekte edilebilir (E19/V01 deseniyle tutarlı)
  [x] Kabul et (fallback)   → açıklama: şimdilik izleniyor, V05/V06'dan daha yüksek öncelikli
      (davranış açıkça yanlış — yasak kalıbı üretiyor), ama acil/blocker değil

NOT: diğer ikisinden farklı olarak bu, "doğru ama farklı ifade" değil, gerçek bir davranış
     boşluğu — kod guard'ı en güvenilir kısa vadeli çözüm olabilir.
```

---

## Backlog (işlenmemiş hatalar)

> Bu bölüme form doldurulmadan önce hızlı notlar eklenebilir; form daha sonra tamamlanır.

| # | Tarih | Kısa tanım | Kategori | Durum |
|---|-------|------------|----------|-------|
| 1 | 25 Haz | Adana kebap → Şalgam Suyu | Kapsam-içi | ✅ Çözüldü (Guard 2 + prompt) |
| 2 | 25 Haz | STT 8.4s gecikme | Kapsam-içi | ✅ Çözüldü (STT params + Guard 1) |
| 3 | 25 Haz | "İzlemiş" → "Kremalı Mantar" onayı | Kapsam-içi | ✅ Çözüldü (Guard 1) |
| 4 | 22 Tem | E09 "Hamburger var mı?" — wbot_v5 ham adapter'da yanlış çıkmıştı | Kapsam-içi (regresyon şüphesi) | ✅ **Regresyon değilmiş** — 24 Temmuz'da Jetson'da `eval_gguf.py` ile GGUF üzerinde GEÇTİ ("Bu konuda bilgim yok, personelimize sorabilirsiniz."). Ham adapter/formal-eval farkı (sampling/determinizm) sonucuymuş, kod değişikliği gerekmedi |
| 5 | 24 Tem | V05 "Tuvalet nerede?" — personele yönlendirme yerine genel "yardımcı olamıyorum" | Kapsam-içi | 📋 Form dolduruldu (Örnek 3) — kabul edilen fallback, acil değil |
| 6 | 24 Tem | V06 gluten alerjisi+öneri — 3-öğe zorunlu kalıp eksik olabilir | Kapsam-içi | 📋 Form dolduruldu (Örnek 4) — kabul edilen fallback, içerik doğru/güvenli, acil değil |
| 7 | 24 Tem | V07 iki ardışık anlaşamama → eskalasyon yerine 3. kez netleştirme (yasak kalıp üretiyor) | Kapsam-içi | 📋 Form dolduruldu (Örnek 5) — gerçek davranış boşluğu, diğer ikisinden öncelikli ama acil değil |

---

## Karar Ağacı (hızlı triyaj)

```
Hata bulundu
    │
    ├─ STT metni zaten yanlıktı?
    │       ├─ Evet → KÖK NEDEN: STT hatası
    │       │         → Aksiyon: STT params / Guard 1 / VAD ayarı
    │       └─ Hayır (metin doğruydu) ↓
    │
    ├─ Guard kesmesi gerekirdi ama kesmedi?
    │       ├─ Evet → KÖK NEDEN: Guard eksik
    │       │         → Aksiyon: Guard ekle/güncelle
    │       └─ Hayır (LLM'e doğru girdi gitti) ↓
    │
    ├─ LLM yanlış kurala uydu / kuralı atladı?
    │       ├─ Evet → KÖK NEDEN: Prompt yetersiz
    │       │         → Aksiyon: Prompt güncelle + dataset çifti ekle
    │       └─ Hayır (kural yok / eğitimde hiç görülmemiş) ↓
    │
    ├─ Benzer senaryo eğitimde var mıydı?
    │       ├─ Hayır → KÖK NEDEN: Veri eksik
    │       │          → Aksiyon: Dataset çifti ekle (wbot_v4)
    │       └─ Evet ama model hâlâ yanlış yapıyor ↓
    │
    └─ Girdi menü/kapsam dışı mı? (sonsuz varyasyon)
            ├─ Evet → KATEGORİ: Kapsam-dışı
            │         → Aksiyon: Kabul et / fallback yeterli
            └─ Hayır → Daha derin analiz / ekip toplantısı
```
