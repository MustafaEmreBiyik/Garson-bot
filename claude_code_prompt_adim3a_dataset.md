# Görev: wbot_v4 Dataset Üretimi — A Paketi (gen_*.py Genişletme)

## Ön Okuma (Sırayla — Atlamadan Yap)

1. `PROJE_DURUMU.md` — wbot_v4 planı, bilinen hatalar (E19/W15, W16),
   kritik kurallar, dataset format gereksinimleri
2. `SENARYO_PLANI_FAZ1.md` — S19-B kanonik yanıt kalıbı, S12 koşulsuz
   özet kararı, S29 küfür politikası, yeni senaryo tablosu (S33-S41)
3. `scripts/audit_dataset.py` — 10 kural (8 içerik + 2 sistem promptu)
4. `scripts/gen_siparis_baska.py` ve `scripts/gen_karsilama.py` — kanonik
   sistem promptu nasıl yükleniyor, üretim pattern'ı nasıl

> Dosya bulunamazsa tahmin etme, sor.

---

## Hedef

Mevcut gen_*.py scriptlerini okuyup genişleterek ~490 yeni kayıt üret.
Bu kayıtlar wbot_v4 fine-tune için `wbot_v3_train.jsonl`'e eklenecek.

**Her üretilen kayıt:**
- Kanonik sistem promptunu içermeli (5460 karakter, wbot_finetune_v1.jsonl'den)
- `audit_dataset.py`'de 0 ihlal vermeli
- Format: `{"messages": [{"role":"system","content":"..."},
  {"role":"user","content":"..."},{"role":"assistant","content":"..."}]}`

---

## 5 Alt Görev

### A1 — W15/E19 Fix: Açıklama + "Getireyim mi?" (~150 kayıt)

**Senaryo:** Müşteri ürün hakkında bilgi soruyor → robot açıklama yapıyor +
"Getireyim mi?" veya eşdeğeri ile bitiriyor.

**Mevcut sorun:** `eval_gguf.py` E19 testi fail — model açıklama yapıyor ama
"Getireyim mi?" demiyor (W15 hata kodu).

**Kanonik yanıt yapısı:**
```
[Ürün açıklaması, 1-2 cümle, max 20 kelime]
+ [Getireyim mi? / Sipariş vermek ister misiniz? / Denemek ister misiniz?]
```

**Üretilecek varyasyonlar:**
- Her menü ürünü için en az 2-3 soru formu ("nasıl bir şey?", "ne var içinde?",
  "tarif eder misiniz?", "anlatır mısınız?")
- Yanıt sonu varyasyonları: "Getireyim mi?", "Sipariş vermek ister misiniz?",
  "Denemek ister misiniz?", "Ekleyeyim mi?"
- Önceki mevcut gen_siparis_baska.py Bölüm D'yi genişlet veya
  `gen_aciklama.py` olarak yeni script yaz

**Audit kontrolü:** Her yanıt "getireyim mi" veya eşdeğerini içermeli.

---

### A2 — Karmaşık/Adetli Sipariş (~150 kayıt)

**Senaryo:** Birden fazla ürün, adet belirtme, toplam hesaplama.

**Kapsanması gereken alt tipler:**
- Adetli sipariş: "İki köfte, üç ayran" → toplam doğru hesaplanmalı
- Karma kategori: çorba + ana yemek + içecek birlikte
- Tur tur ekleme (çok turlu): önce ana yemek, sonra "bir de ayran ekle"
- Onay öncesi koşulsuz özet (S12 kararı):
  "Siparişiniz: [ürünler]. Toplam [X] TL. Onaylıyor musunuz?"

**Kritik:** OrderTracker mantığıyla tutarlı olmalı — toplam LLM'in
hesaplaması değil, ürün fiyatlarından doğru aritmetik.

**Mevcut:** `gen_cotturlu.py` (150 kayıt) ve `gen_siparis_baska.py` (150)
— bunları kopyalama, yeni varyasyonlar üret.

---

### A3 — Uzun Çok Turlu Konuşma (~100 kayıt)

**Senaryo:** 4-7 tur içeren tam restoran deneyimi.
Karşılama → menü sorusu → sipariş → değişiklik → özet → onay → kapanış

**Mevcut:** `gen_cotturlu.py` 3-5 tur, ama sadece sipariş akışı.
Bu set daha zengin akışlar içermeli:
- Menü sorusu + önce ret + sonra sipariş
- Yanlış anlama → düzeltme → tekrar sipariş
- Onay aşamasında değişiklik

**Format:** Multi-turn JSON, her kayıtta en az 4 user-assistant çifti.

---

### A4 — Kısa Onay Senaryosu / S13 (~60 kayıt)

**Senaryo:** Robot özet okuyup "Onaylıyor musunuz?" dedi, müşteri
"evet" / "tamam" / "doğru" / "olur" / "evet öyle" dedi → robot ne yapar?

**Beklenen davranış:** Siparişi sisteme işle + "Afiyet olsun" veya
"Hemen iletiyorum" tarzı kapanış. **"onaylandı/kaydedildi" yasak** (E29 kuralı).

**Format:** Çok turlu seed history ile — önceki konuşmada sipariş verilmiş,
assistant özet okumuş, user "evet" demiş, assistant kapanış yapıyor.

---

### A5 — Yanlış Anlama → Düzeltme / S26 (~30 kayıt)

**Senaryo:** Robot yanlış anladı veya yanlış tekrarladı → müşteri düzeltiyor
→ robot günceller.

**Alt tipler:**
- Ürün adı yanlış: "Döner dedim köfte demedim"
- Adet yanlış: "İki değil bir tane"
- Tamamen farklı: "Hayır, çorba istemiyorum, çay istiyorum"
  (çay menüde yok → bu durumda menüde olmadığını söyle)

**Format:** Çok turlu, hata içeren assistant turu seed olarak verilmiş.

---

## Üretim Sırası

A1 → A2 → A4 → A5 → A3 (en kolay → en zor)

Her alt görev sonrası:
```bash
python scripts/audit_dataset.py --dataset <yeni_dosya.jsonl>
```
0 ihlal olmadan bir sonraki alt göreve geçme.

---

## Çıktı Dosyaları

```
robot_waiter_ai/datasets/processed/wbot_v4_aciklama.jsonl      # A1, 150 kayıt
robot_waiter_ai/datasets/processed/wbot_v4_karmasik.jsonl      # A2, 150 kayıt
robot_waiter_ai/datasets/processed/wbot_v4_cokturlu.jsonl      # A3, 100 kayıt
robot_waiter_ai/datasets/processed/wbot_v4_kisa_onay.jsonl     # A4, 60 kayıt
robot_waiter_ai/datasets/processed/wbot_v4_duzeltme.jsonl      # A5, 30 kayıt
```

`wbot_v3_train.jsonl`'e birleştirme bu görevin kapsamı dışında — önce
B ve C paketleri tamamlanacak, sonra tek seferde birleştirme yapılacak.

---

## Kritik Kısıtlar

- Sistem promptunu hardcode etme — `wbot_finetune_v1.jsonl` ilk satırından oku
  (gen_karsilama.py / gen_siparis_baska.py'nin yaptığı gibi)
- Her alt görev öncesi diff/taslak göster, onay al, sonra üret
- `audit_dataset.py`'de mevcut 10 kural değişmemeli — ihlal çıkarsa
  önce düzelt, sonra bir sonraki alt göreve geç
- Menü fiyatları ve alerjen bilgileri `menu.yaml`'dan oku, hardcode etme
- A5'te "çay" gibi menüde olmayan ürün taleplerine doğru yanıt üret:
  menüde yok → "Maalesef çayımız bulunmuyor" (uydurma fiyat/ürün yasak)
