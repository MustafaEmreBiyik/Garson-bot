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

---

## Backlog (işlenmemiş hatalar)

> Bu bölüme form doldurulmadan önce hızlı notlar eklenebilir; form daha sonra tamamlanır.

| # | Tarih | Kısa tanım | Kategori | Durum |
|---|-------|------------|----------|-------|
| 1 | 25 Haz | Adana kebap → Şalgam Suyu | Kapsam-içi | ✅ Çözüldü (Guard 2 + prompt) |
| 2 | 25 Haz | STT 8.4s gecikme | Kapsam-içi | ✅ Çözüldü (STT params + Guard 1) |
| 3 | 25 Haz | "İzlemiş" → "Kremalı Mantar" onayı | Kapsam-içi | ✅ Çözüldü (Guard 1) |
| 4 | 22 Tem | E09 "Hamburger var mı?" — wbot_v5 ham adapter'da yanlış çıkmıştı | Kapsam-içi (regresyon şüphesi) | ✅ **Regresyon değilmiş** — 24 Temmuz'da Jetson'da `eval_gguf.py` ile GGUF üzerinde GEÇTİ ("Bu konuda bilgim yok, personelimize sorabilirsiniz."). Ham adapter/formal-eval farkı (sampling/determinizm) sonucuymuş, kod değişikliği gerekmedi |
| 5 | 24 Tem | V05 "Tuvalet nerede?" — personele yönlendirme yerine genel "yardımcı olamıyorum" | Kapsam-içi | ⏳ Form doldurulmadı — wbot_v5 GGUF eval'inde (`--v4-targets`) görüldü, acil değil |
| 6 | 24 Tem | V06 gluten alerjisi+öneri — 3-öğe zorunlu kalıp eksik olabilir | Kapsam-içi | ⏳ Form doldurulmadı — wbot_v5 GGUF eval'inde görüldü, yanıt içerik olarak makul ama kalıba tam uymuyor, acil değil |
| 7 | 24 Tem | V07 iki ardışık anlaşamama → eskalasyon yerine 3. kez netleştirme | Kapsam-içi | ⏳ Form doldurulmadı — wbot_v5 GGUF eval'inde görüldü, acil değil |

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
