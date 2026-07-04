# Görev: wbot_v4 Dataset Üretimi — C Paketi (Görev Tanımı — SADECE DOKÜMAN)

**Durum:** Bu bir görev TANIMIDIR. Bu dosya yazıldığı oturumda veri ÜRETİLMEDİ,
`wbot_v4_train.jsonl`'e HİÇBİR kayıt eklenmedi. Amaç: C paketi ne zaman
üretilirse (muhtemelen Gemini/Claude API ile, ayrı bir oturumda) kullanılacak
somut bir brief bırakmak.

---

## Neden Ayrı Bir Tur / Neden Şimdi Değil

wbot_v4 eğitimi (`wbot_v4_train.jsonl`, 3605 kayıt — A paketi 490 + B paketi
115) başlatılmak üzere. Bu noktada C paketini üretip aynı dataset'e eklemek
üç nedenle ertelendi:

1. **Baseline karışmasın** — wbot_v4 eğitim sonucu, A+B paketinin gerçek
   etkisini ölçmek için temiz bir baseline olmalı. C paketi eklenirse hangi
   iyileşmenin hangi paketten geldiği ayırt edilemez.
2. **3605 kilit** — Dataset zaten audit'ten geçmiş, sistem promptu dağılımı
   doğrulanmış durumda. Eğitim öncesi tekrar birleştirme riski gereksiz.
3. **İki değişkeni aynı anda oynatma** — Hem yeni veri hem yeni eğitim
   sonucu aynı anda değişirse, eval'de görülen fark hangisinden kaynaklandı
   bilinemez.
4. **Kalite kontrol döngüsü farklı** — Anti-hallüsinasyon ve eskalasyon gibi
   "doğal konuşma" gerektiren senaryolar LLM API ile üretilecek; bu, şablon
   scriptlerinden (`gen_*.py`) farklı bir doğrulama akışı ister (audit'ten
   geçirme + elle örneklem inceleme). Eğitim başlamadan hemen önce bu
   döngüyü aceleye getirmenin anlamı yok.

**Sıra:** (1) bu görev tanımını yaz ve commit et → (2) wbot_v4 eğitimini
planlandığı gibi başlat → (3) eval sonuçlarına göre bu tanımı revize et
(V02 gerçekten fail mi, E34 hâlâ uyduruyor mu, başka boşluk çıktı mı) →
(4) ancak o zaman C paketini üret.

---

## Kapsam — Yalnızca 3 Kalem (~140 kayıt)

Önceki "~495 kayıt" rakamı **hiçbir zaman gerçek bir hedef değildi** —
yalnızca "~1100 hedef − 605 üretilen" aritmetik kalıntısıydı. Gerçek kapsam,
şu an üretilebilir olanla sınırlı:

| # | Senaryo | Tahmini Adet | Eval Karşılığı |
|---|---------|-------------|-----------------|
| 1 | S34/V02 — Modifikasyon, sipariş sonrası | ~20 | **Zaten var** (`eval_gguf.py --v4-targets`) |
| 2 | S41 — İki ardışık anlaşamama → eskalasyon | ~20 | **Yok, birlikte tanımlanmalı** (aşağıda) |
| 3 | Anti-hallüsinasyon (menüde olmayan detay) | ~100 | E34 (mevcut bilinen zayıflık) |
| | **Toplam** | **~140** | |

### Kapsam Dışı — Bu Pakette Değil

- **S39 (ürün tükendi)** — Kod ön koşulu eksik: `llama_cpp_backend.py`'deki
  `_build_menu_text()` şu an `availability` alanını okumuyor. Önce context
  builder'a destek eklenmeli, veri ondan sonra.
- **Gürültülü ortam edge case'leri** (~100) — Kod değil, saha testi ön
  koşulu eksik. Gerçek gürültülü ortam testi (Jetson, restoran müziği +
  kalabalık) henüz hiç yapılmadı — "Sıradaki görevler" listesinde bekliyor.
  Testten çıkan gerçek hata örnekleri olmadan icat edilmiş veri üretmek
  gerçekçi olmaz.
- **Alerji + öneri derinleştirmesi** — B paketinde S19-B kanonik kalıbıyla
  (gen_alerji_oneri.py, gen_alerjen_cakisma.py, 35 kayıt) zaten karşılandı.
  Ek derinleştirme bu pakete dahil değil.

---

## 1 — S34/V02: Modifikasyon, Sipariş Sonrası (~20 kayıt)

**Senaryo:** Ürün zaten sipariş edilip onaylandıktan SONRA (ayrı bir turda)
müşteri değişiklik istiyor. S33/V01'den farkı: S33'te modifikasyon sipariş
cümlesiyle AYNI mesajda ("bir şalgam alayım, acılı olsun"); S34'te sipariş
onaylandıktan sonra, ayrı bir kullanıcı mesajında geliyor.

**Örnek akış:**
```
user: Bir et döner alayım.
assistant: Elbette, Et Döner 280 TL. Başka bir şey alır mısınız?
user: Az önce aldığım döneri soğansız yapar mısınız?
assistant: Tabii, Et Döner soğansız olacak şekilde güncellendi. Başka bir şey ister misiniz?
```

**Beklenen davranış:** Kabul + güncellenmiş onay tekrarı (yeni fiyat yok,
ürün aynı — yalnızca modifikasyon notu güncellenir). "Getireyim mi?" veya
"onaylandı/kaydedildi" yasağı burada da geçerli.

**Eval:** `eval_gguf.py --v4-targets`'te V02 zaten tanımlı — bu kayıtlar
doğrudan onu besleyecek.

**⚠️ Eğitim/eval yorumlama notu:** wbot_v4 eval'inde V02'nin **FAIL vermesi
beklenen sonuçtur** çünkü şu an bu senaryoya dair hiç veri yok — model V01
verisinden genelleme yapıp geçerse bonus, geçmezse sürpriz değildir. Bu
sonucu "wbot_v4 başarısızlığı" değil "bilinen veri boşluğunun teyidi"
olarak sınıflandırın.

---

## 2 — S41: İki Ardışık Anlaşamama → Eskalasyon (~20 kayıt)

**Senaryo:** SENARYO_PLANI_FAZ1.md'nin S41 satırı birebir: "**İki ardışık**
anlaşamama → 'Personelimizi çağırıyorum' eskalasyonu." En sadık okuma: 1.
anlaşılamama → netleştirici soru, 2. anlaşılamama → **doğrudan eskalasyon**
(3. bir netleştirme denemesi YOK). Şu an bu senaryonun ne verisi ne eval'i
var — ikisi birlikte tanımlanmalı.

**⚠️ Tasarım notu (revize edildi):** İlk taslakta yanlışlıkla S03'ün "en
fazla 2 istem" ilkesi (karşılama + 1 reprompt, sonra çekilme) buraya
taşınmış ve 3 turlu bir kurgu (netleştir → netleştir → 3.'de eskale)
önerilmişti. Bu hem SENARYO_PLANI_FAZ1.md'nin "iki ardışık" ifadesiyle
çelişiyordu hem de S03 analojisi yanlıştı: S03 **sessizlik** senaryosu
(müşteri hiç konuşmuyor); S41'de müşteri aktif konuşuyor ama anlaşılmıyor —
farklı bir dinamik. Doğru referans doğrudan SENARYO_PLANI_FAZ1.md'nin
kendi S41 tanımı. Aşağıdaki akış ve eval kriteri buna göre düzeltildi.

**Örnek akış (çok turlu, 2 anlaşılamama):**
```
user: [belirsiz/anlaşılmaz girdi #1 — örn. gürültü/STT hatası simülasyonu]
assistant: [netleştirici soru — S25/S27 kalıbı, örn. "Tam anlayamadım, ne almak istersiniz?"]
user: [belirsiz/anlaşılmaz girdi #2 — hâlâ anlaşılmıyor]
assistant: "Sizi tam anlayamıyorum, personelimizi çağırıyorum." (2. anlaşılamamada DOĞRUDAN eskalasyon — 3. deneme yok)
```

### Yeni Eval Tanımı — V07 (taslak)

- **Kod:** V07 (mevcut V01-V06'dan sonraki sıradaki numara,
  `eval_gguf.py --v4-targets`'e eklenecek)
- **Senaryo adı:** Ardışık anlaşamama eskalasyonu
- **Tetikleyici:** Aynı oturumda **iki ardışık** anlaşılamama turu (ikinci
  anlaşılamamada bot üçüncü bir netleştirme denemeden doğrudan eskale eder)
- **PASS kriteri:**
  1. İkinci anlaşılamama turunda yanıt **"personel"** kelimesini VE bir
     çağırma/yönlendirme ifadesini içermeli (örn. "çağırıyorum",
     "yardımcı olacaktır")
  2. Bu turda **YENİ bir netleştirme sorusu SORULMAMALI**
  3. Ton nötr olmalı — espri, taklit, azarlama, suçlama YASAK (S29
     politikasıyla tutarlı)
- **Kapsam dışı:** Oturumun fiilen sonlandırılması runtime'ın işi
  (`demo_usb.py`) — training datada yalnızca kapanış CÜMLESİ yer alır,
  S29/gen_kotu_niyet.py'deki ısrarlı-küfür kaydı ile aynı yaklaşım.

---

## 3 — Anti-Hallüsinasyon (~100 kayıt)

**Senaryo:** Müşteri bir ürün hakkında `menu.yaml`'da YAZILI OLMAYAN bir
detay soruyor veya bot kendiliğinden var olmayan bir malzeme/özellik
uydurma eğiliminde. Bilinen zayıflık E34: "elma dilim patates" gibi
menüde yazılı olmayan detayları model kendiliğinden ekliyor.

**Alt tipler (öneri, ~30-35'er):**
1. **Ürün açıklamasında ekstra detay istemi** — "Hangi tür patates
   kullanıyorsunuz?", "Köftenin içinde soğan var mı, oranı ne?" gibi
   `menu.yaml`'ın `description` alanında yazılı olmayan sorular →
   yalnızca yazılı olanı tekrarla, yoksa "Bu konuda net bilgim yok,
   personelimize sorabilirsiniz."
2. **Malzeme/allerjen ayrıntısı menüde yok** — "Künefede fındık mı ceviz
   mi var?" (menu.yaml sadece "kuruyemiş" diyor, tür belirtmiyor) →
   uydurma yapmadan mevcut bilgiyle sınırlı kal.
3. **Porsiyon/pişirme detayı uydurma riski** — "Kaç gram et var
   dönerde?", "Çorba kaç dakikada pişiyor?" gibi menüde yer almayan
   nicel detaylar → uydurma yok, dürüst "bilgim yok" + personel.

**Kritik kısıt:** Her yanıt yalnızca `menu.yaml`'daki gerçek alanlara
(`description`, `allergens`, `tags`, `price`) dayanmalı; bu alanların
dışında hiçbir sayısal/nitel detay üretilmeyecek.

---

## Üretim Ortamı ve Kalite Kontrol

- **Önerilen üretim yöntemi:** Gemini/Claude API — A/B paketindeki şablon
  tabanlı Python üretiminden (`gen_*.py`) farklı olarak, bu üç kategori
  daha doğal dil çeşitliliği gerektiriyor (özellikle anti-hallüsinasyon ve
  eskalasyon diyalogları kalıplaşmış şablonlarla zayıf kalır).
- **Zorunlu doğrulama adımları (veri üretildiğinde):**
  1. `python scripts/audit_dataset.py --dataset <yeni_dosya.jsonl>` — 0
     ihlal olmadan birleştirmeye geçme.
  2. Elle örneklem incelemesi — LLM API çıktısı şablon script'ten farklı
     olarak öngörülemez varyasyon üretebilir; en az %10 örneklem elle
     okunmalı.
  3. Sistem promptu kanonik 5460 karakter olmalı (`wbot_finetune_v1.jsonl`
     ilk kayıttan okunarak, hardcode edilmeden).

## Boyut Notu

C paketi ~140 kayıtla da "tam" sayılabilir — 495 rakamı bir hedef değil,
aritmetik artıktı. Nihai boyutu wbot_v4 eval bulguları belirlesin: V02
gerçekten fail veriyorsa S34 verisi doğrulanmış olur; E34 hâlâ
görülüyorsa anti-hallüsinasyon kategorisi genişletilebilir.
