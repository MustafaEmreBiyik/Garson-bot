# wbot_v2 Dataset Genişletme — Codex Prompt

Bu dosyayı bir AI asistana (Codex, Claude, GPT-4 vb.) ver.
Çıktıyı inceleyip onaylamamız gerekiyor — henüz dataset üretme.

---

## Görev

Aşağıda bir Türkçe restoran garson yapay zekası (W-BOT) için fine-tune dataset'i genişletme yol haritası hazırlaman gerekiyor.

**Ne istiyorum:**
Her senaryo kategorisi için şunları listele:
1. Kategori adı ve kısa açıklama
2. Alt senaryo örnekleri (kullanıcı cümleleri — Türkçe)
3. Önerilen kayıt sayısı (ve nedeni)
4. Öncelik: 🔴 Kritik / 🟡 Orta / 🟢 Düşük
5. Mevcut dataset'te var mı? (Evet/Kısmen/Hayır)

---

## Proje Bağlamı

**W-BOT:** Türkçe konuşan, fiziksel servis robotuna entegre edilecek garson yapay zekası.
- Qwen3-4B tabanlı, QLoRA fine-tune
- Gürültülü restoran ortamı, müşterilerle doğal konuşma
- **Sadece Türkçe** çıktı
- Müşteriye DAİMA "siz" formu
- Max 2 cümle, 25 kelime yanıt
- Markdown, emoji, madde işareti YASAK

**Menü:**
- Çorba: Mercimek Çorbası (85 TL), Kremalı Mantar Çorbası (95 TL)
- Ana Yemek: Izgara Köfte (240 TL), Et Döner (280 TL), Izgara Tavuk Salata (210 TL)
- Tatlı: Fırın Sütlaç (100 TL), Künefe (140 TL)
- İçecek: Yayık Ayran (45 TL), Limonata (70 TL), Şalgam Suyu (50 TL)

---

## Mevcut Dataset (wbot_finetune_v1, 970 kayıt)

| Kod | Senaryo | Kayıt |
|-----|---------|-------|
| A | Karşılama, genel menü tanıtımı | ~120 |
| B | Tekli/çoklu sipariş alma | ~180 |
| C | Sipariş iptali ve değişikliği | ~100 |
| D | Fiyat sorusu (tekli ürün) | ~100 |
| E | Kategori listesi soruları | ~100 |
| F | Öneri/tavsiye soruları | ~120 |
| G | Alerji ve diyet soruları | ~100 |
| H | Menü dışı ürün, konu dışı, hesap, veda | ~150 |

**Tüm kayıtlar tek turlu (system + user + assistant).** Çok turlu konuşma YOK.

---

## Mevcut Eval Başarısızlıkları (wbot_v1, 1 epoch, kısa prompt)

Bu boşlukları kapatmak zorunlu:

| Kod | Sorun | Örnek başarısız kullanıcı cümlesi |
|-----|-------|-----------------------------------|
| E02 | "Ne yiyebilirim?" genel menü sorusu varyantları dataset'te yok | "Ne yiyebilirim?", "Bugün ne var?", "Menünüz nedir?" |
| E09 | Menüde olmayan ürün sampling'e duyarlı | "Hamburger var mı?", "Pizza siparişi verebilir miyim?" |
| W-G | "Getireyim mi?" hâlâ kullanılıyor (yasak) | Her sipariş onayı ve fiyat sorusunda tekrar ediyor |

---

## Üretilmesi Gereken Senaryo Kategorileri

Aşağıdaki kategorileri değerlendir. Her biri için tablo formatında çıktı ver.

### 1. Genel Menü Soruları (A-EKSİK)
Kategori belirtmeden yapılan genel "ne var" soruları.

### 2. Fiyat Karşılaştırma ve Bütçe Soruları (D-GENİŞLEME)
Örn: "En ucuz ana yemek hangisi?", "50 TL'ye ne yiyebilirim?"

### 3. Bileşik Siparişler (B-GENİŞLEME)
Aynı cümlede 2+ ürün siparişi. Adet varyasyonları dahil.

### 4. Çok Turlu Konuşmalar (YENİ)
2-4 turlu diyalog zincirleri. Karşılama → sipariş → değişiklik → hesap akışları.

### 5. Diyet / İçerik Soruları (G-GENİŞLEME)
Vegan, vejetaryen, gluten, laktoz, düşük kalori, helal sorguları.

### 6. Menüde Olmayan Ürün Varyantları (H-GENİŞLEME)
Fast food, uluslararası mutfak, içecek çeşitleri, atıştırmalık istekleri.

### 7. Belirsiz / Kısmi Sorular (YENİ)
Tek kelime sorular, yarım cümleler, STT hata yansımaları.

### 8. Kapanış / Teşekkür / Veda (YENİ)
"Teşekkürler", "Güle güle", "Harika hizmet", "Tekrar geleceğim."

### 9. Restoran Hakkında Sorular (YENİ)
Çalışma saatleri, konum, rezervasyon, paket servis, ödeme yöntemi.
**Not:** Tümü "Bu konuda bilgim yok, personelimize sorabilirsiniz." ile yanıtlanacak.

### 10. Müşteri Modları (YENİ)
Aceleci ("Hızlı bir şeyler ver"), düşünceli ("Karar veremedim"), çok konuşkan, kısa konuşan.

### 11. Çoklu Tur Sipariş Değişikliği (C-GENİŞLEME)
Birden fazla iptal/ekleme/değişiklik içeren turlar.

### 12. Hesap Varyasyonları (H-GENİŞLEME)
Ara toplam isteği, kısmi ödeme, farklı kapanış formülleri.

---

## Çıktı Formatı

Her kategori için şu tabloyu doldur:

```
### [Kategori Adı]
**Durum:** Yeni / Mevcut genişlemesi
**Öncelik:** 🔴 / 🟡 / 🟢
**Önerilen kayıt sayısı:** X
**Neden bu kadar:** [1-2 cümle gerekçe]

| # | Örnek kullanıcı cümlesi | Beklenen yanıt özeti |
|---|------------------------|----------------------|
| 1 | ...                    | ...                  |
| 2 | ...                    | ...                  |
| 3 | ...                    | ...                  |
(en az 5 örnek)
```

Son olarak özet tablo ver:

| Kategori | Öncelik | Mevcut | Eklenecek | Toplam hedef |
|----------|---------|--------|-----------|--------------|
| ...      | ...     | ...    | ...       | ...          |
| **TOPLAM** | — | 970 | X | ~Y |

---

## Kısıtlar

- Tüm kullanıcı cümleleri gerçekçi Türkçe konuşma dili
- STT çıktısı gibi düşün: noktalama az, bazen eksik
- Yanıt özetleri kısa ve kurala uygun olmalı (max 2 cümle, "Getireyim mi?" YASAK)
- Menüde olmayan ürün yanıtı HEP: "Bu konuda bilgim yok, personelimize sorabilirsiniz."
- Restoran dışı soru yanıtı HEP: "Bu konuda bilgim yok, personelimize sorabilirsiniz."
