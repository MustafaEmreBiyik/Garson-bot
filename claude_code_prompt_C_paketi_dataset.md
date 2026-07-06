# Görev: wbot_v4 Dataset Üretimi — C Paketi (Görev Tanımı — SADECE DOKÜMAN)

**Durum:** Bu bir görev TANIMIDIR. Bu dosyanın yazıldığı oturumda veri
ÜRETİLMEDİ, `wbot_v4_train.jsonl`'e HİÇBİR kayıt eklenmedi. wbot_v4 eğitimi
+ GGUF dönüşümü + Jetson deploy + eval tamamlandı (4 Temmuz 2026) — bu
revizyon gerçek eval bulgularını yansıtıyor.

---

## wbot_v4 Eval Sonuçları (4 Temmuz 2026) — Kapsam Netleşti

`eval_gguf.py` sonuçları **deterministik olarak doğrulandı**: aynı 38
senaryoluk test seti iki kez çalıştırıldı, 38'i de birebir aynı yanıtı
verdi. `llama_cpp_backend.py`'de açık bir `seed=` parametresi YOK
(`Llama(model_path=..., n_gpu_layers=-1, n_ctx=4096, verbose=False)`) —
ama llama-cpp-python'ın bu durumdaki varsayılan davranışı zamana/entropiye
dayanmıyor, bu yüzden sonuçlar süreç boyunca tekrarlanabilir çıkıyor.
Aşağıdaki 6 KALDI, örnekleme gürültüsü DEĞİL — gerçek, tutarlı model
davranışı.

**32-senaryo (temel):** 30/32 (%93) — KALDI: E01, E27
**38-senaryo (`--v4-targets`):** 32/38 (%84) — KALDI: E01, E27, V01, V02, V04, V06

> ⚠️ **Güncelleme (6 Temmuz 2026):** Yukarıdaki skorlar revizyon-ÖNCESİ E24
> kriteriyle ölçüldü. E24, S12 Karar 2'ye hizalandı (görev #16) — güncel
> baseline: 32 senaryo **29/32** (KALDI: E01, E24, E27), 38 senaryo **31/38**.
> E24 bilinen boşluk (W11 kuralı); üretimde S12 guard karşılıyor.

**Kazanımlar:** E19 (W15 — açıklama + "Getireyim mi?") artık GEÇİYOR, A1
paketinin asıl hedefiydi. V03 (S35/alerjen çakışması) ve V05 (S37/pratik
soru) temiz geçti — B4/B5 işe yaradı.

### 6 KALDI — Kategorize Edilmiş Bulgular

| Kod | Kategori | Not |
|---|---|---|
| **E01** | ⚠️ **wbot_v3→v4 REGRESYONU** | wbot_v3'te GEÇİYORDU (31/32'nin parçasıydı). Yeni bulgu değil. |
| **E27** | ⚠️ **wbot_v3→v4 REGRESYONU** | Aynı şekilde wbot_v3'te GEÇİYORDU. Yeni bulgu değil. |
| V01 | Format eksikliği | Modifikasyon onayında fiyat (TL) söylenmiyor — dar, tek koşullu |
| V02 | Beklenen boşluk | Zaten dokümante edilmişti (S34 verisi hiç yok) |
| V04 | Gerçek bulgu — ciddi | S29 ihlali: kabalığa "Size çok kızarmak istiyorum" |
| V06 | Gerçek bulgu — halüsinasyon | Glütensiz listesine gluten içeren ürün ekliyor |

**E01/E27'nin "regresyon" olarak işaretlenmesi önemli:** Bunlar A/B
paketinin YENİ bir boşluğu değil — wbot_v3'te ZATEN doğru çalışan bir
davranışın wbot_v4 eğitimiyle BOZULMASI. Kök neden muhtemelen yeni 605
kayıt içindeki bir etkileşimin bu iki dar kalıbı seyreltmesi (ör. çok
sayıda yeni senaryo türü karşılama/alerji yanıt dağılımını kaydırmış
olabilir). Çözüm "daha fazla aynı tür veri eklemek" değil — bkz. aşağıdaki
kod-seviyesi düzeltmeler.

---

## Kod Seviyesi Düzeltmeler (Veri Değil) — E01, V01

Bu ikisi dar, tek koşullu, kolayca tanımlanan kurallar — E19/W15'in ilk
düşünülen (ve sonra veriyle çözülen) çözümüyle aynı mantık, ama burada
ek veri yerine post-processing daha güvenilir çünkü kural zaten TÜM
eğitim verisinde mevcut; sorun hacim değil, üretim-anı atlaması.

- **E01** — Karşılama yanıtı "?" ile bitmeli kuralı tüm eğitim verisinde
  var; modelin bunu bazen atlaması ek veriyle garanti çözülemeyecek
  kadar ince bir üretim davranışı.
- **V01** — Modifikasyon onayında fiyatı söyleme kuralı da eğitim
  verisinde hep vardı; eksiklik veri hacminden çok tek seferlik atlama.

**Önerilen düzeltme (`demo_usb.py` post-processing katmanı):**
- Karşılama yanıtı (4 kategori tespit edildiğinde) "?" ile bitmiyorsa
  sona uygun bir soru ekle — E19 fix'i için ilk düşünülen yamayla aynı
  desen.
- Modifikasyon onayı (sipariş + modifikasyon kelimesi birlikte tespit
  edildiğinde) yanıtta ürünün TL fiyatı yoksa OrderTracker'dan regex ile
  enjekte et — hesap toplamı override mekanizmasıyla aynı desen.

Bu iki düzeltme veri üretimi gerektirmiyor, **C paketinin kapsamı DIŞINDA**
— ayrı, küçük bir kod görevi olarak ele alınmalı.

---

## Neden C Paketi Ayrı Bir Tur

wbot_v4 eğitimi tamamlandı, eval sonuçları alındı — dolayısıyla "baseline
karışmasın" gerekçesi artık geçmişte kaldı, ama yeni bir gerekçe kümesi
geçerli:

1. **Kalite kontrol döngüsü farklı** — Anti-hallüsinasyon ve eskalasyon
   gibi "doğal konuşma" gerektiren senaryolar LLM API ile üretilecek; bu,
   şablon scriptlerinden (`gen_*.py`) farklı bir doğrulama akışı ister
   (audit'ten geçirme + elle örneklem inceleme).
2. **Kod düzeltmeleri önce gelmeli** — E01/V01 post-processing + V04
   runtime guard + S12/E24 runtime guard (ki bu, `detect_order()` ön koşul
   testine bağlı), veri eklemeden önce/paralelinde yapılmalı; aksi halde
   hangi iyileşmenin veriden hangisinin koddan geldiği ayırt edilemez.
3. **wbot_v5'e toplu geçiş** — C paketi + kod düzeltmeleri birlikte
   tamamlanıp tek seferde wbot_v5 olarak eğitilmesi, art arda küçük
   yamalarla dataset'i sık sık yeniden karıştırmaktan daha temiz.

---

## Kapsam — 5 Kalem (~175-185 kayıt) + 3 Kod Görevi

Önceki "~495 kayıt" rakamı **hiçbir zaman gerçek bir hedef değildi** —
yalnızca "~1100 hedef − 605 üretilen" aritmetik kalıntısıydı. Eval
sonuçlarıyla netleşen gerçek kapsam:

| # | Senaryo | Tahmini Adet | Eval Karşılığı |
|---|---------|-------------|-----------------|
| 1 | S34/V02 — Modifikasyon, sipariş sonrası | ~20 | Zaten var (`--v4-targets`) |
| 2 | S41 — İki ardışık anlaşamama → eskalasyon | ~20 | Yok, V07 taslağıyla birlikte tanımlandı |
| 3 | Anti-hallüsinasyon (ürün açıklaması, menüde olmayan detay) | ~100 | E34 (bilinen zayıflık) |
| 4 | Küfür/kabalık genişletme | ~15-20 | V04 — mevcut 5 kayıt yetersiz kaldı |
| 5 | Alerji kalıp/doğruluk düzeltmesi | ~20-25 | E27 (regresyon) + V06 (kalıp-uyum, aşağıda reformüle) |
| | **Toplam** | **~175-185** | |

**+ 3 ayrı kod görevi (veri değil) — güncel durum (6 Temmuz 2026):**
1. ~~S12/E24 runtime guard~~ — ✅ TAMAMLANDI (5 Temmuz, görev #21 ön koşul
   fix'i + görev #22 guard; E24 eval'i de revize edildi — görev #16).
2. E01/V01 post-processing — ⏳ bekliyor (sıradaki iş).
3. V04 runtime guard — ⏳ bekliyor (madde 4-b).

**Not — kapsam değişikliği:** Önceki taslakta "Alerji + öneri
derinleştirmesi B'de zaten karşılandı, kapsam dışı" denmişti. Eval
sonuçları bunun **yanlış** olduğunu gösterdi (E27 regresyon + V06
halüsinasyon) — bu madde kapsama **geri alındı**.

### Kapsam Dışı — Hâlâ Bu Pakette Değil

- **S39 (ürün tükendi)** — Kod ön koşulu eksik: `llama_cpp_backend.py`'deki
  `_build_menu_text()` şu an `availability` alanını okumuyor. Önce context
  builder'a destek eklenmeli, veri ondan sonra.
- **Gürültülü ortam edge case'leri** (~100) — Kod değil, saha testi ön
  koşulu eksik. Gerçek gürültülü ortam testi (Jetson, restoran müziği +
  kalabalık) henüz hiç yapılmadı — "Sıradaki görevler" listesinde bekliyor.

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
doğrudan onu besleyecek. V02'nin şu ana kadar FAIL vermesi beklenen ve
teyit edilmiş sonuçtu — bu madde artık "bilinen boşluk" durumundan
"üretilecek veri" durumuna geçiyor.

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
kendi S41 tanımı.

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
     politikasıyla tutarlı, V04 bulgusuyla da doğrudan ilişkili)
- **Kapsam dışı:** Oturumun fiilen sonlandırılması runtime'ın işi
  (`demo_usb.py`) — training datada yalnızca kapanış CÜMLESİ yer alır.

---

## 3 — Anti-Hallüsinasyon: Ürün Açıklaması (~100 kayıt)

**Senaryo:** Müşteri bir ürün hakkında `menu.yaml`'da YAZILI OLMAYAN bir
detay soruyor veya bot kendiliğinden var olmayan bir malzeme/özellik
uydurma eğiliminde. Bilinen zayıflık E34: "elma dilim patates" gibi
menüde yazılı olmayan detayları model kendiliğinden ekliyor.

> Not: Bu madde **ürün açıklaması** halüsinasyonuna odaklanır. **Alerjen
> doğruluğu** halüsinasyonu (E27/V06'da görülen) ayrı bir madde olarak
> aşağıda (Bölüm 5) ele alınıyor — ikisi farklı kök nedenlere sahip
> olabilir, karıştırılmamalı.

**Alt tipler (öneri, ~30-35'er):**
1. **Ürün açıklamasında ekstra detay istemi** — "Hangi tür patates
   kullanıyorsunuz?", "Köftenin içinde soğan var mı, oranı ne?" gibi
   `menu.yaml`'ın `description` alanında yazılı olmayan sorular →
   yalnızca yazılı olanı tekrarla, yoksa "Bu konuda net bilgim yok,
   personelimize sorabilirsiniz."
2. **Malzeme ayrıntısı menüde yok** — "Künefede fındık mı ceviz mi var?"
   (menu.yaml sadece "kuruyemiş" diyor, tür belirtmiyor) → uydurma
   yapmadan mevcut bilgiyle sınırlı kal.
3. **Porsiyon/pişirme detayı uydurma riski** — "Kaç gram et var
   dönerde?", "Çorba kaç dakikada pişiyor?" gibi menüde yer almayan
   nicel detaylar → uydurma yok, dürüst "bilgim yok" + personel.

**Kritik kısıt:** Her yanıt yalnızca `menu.yaml`'daki gerçek alanlara
(`description`, `allergens`, `tags`, `price`) dayanmalı.

---

## 4 — V04: Küfür/Kabalık — Veri + Runtime Guard (~15-20 kayıt)

**Sorun:** Model kabalığa *"Size çok kızarmak istiyorum, ne yapabilirim?"*
gibi yanıt veriyor — S29 politikasının "asla karşılık verme" kuralını
doğrudan ihlal ediyor. Mevcut `gen_kotu_niyet.py`'de yalnızca **5** küfür
kaydı var (3605 kayıt içinde ~%0.14) — yetersiz kalmış.

**Çözüm — iki katmanlı, veri TEK BAŞINA yeterli sayılmamalı** (E01/V01
tecrübesi bunu gösterdi):

### a) Veri genişletme (~15-20 yeni kayıt)
`gen_kotu_niyet.py`'nin küfür alt tipini genişlet: daha fazla kabalık
varyasyonu (farklı hakaret kalıpları, farklı şiddet seviyeleri) + tek
seferlik/ısrarlı oranını koru (S29: 1. seferde sakin yönlendirme, 2.
seferde kibar kapanış). Yasak ifade listesine (S29) duygusal karşılık
kalıpları da eklenmeli: "kızarmak", "sinirlen-", "bıktım" gibi.

### b) Runtime guard (kod, veri değil)
Veri tek başına garantili değil. Öneri: `demo_usb.py`'de bir kabalık/küfür
kelime listesi tespit guard'ı (mevcut off-menu/düşük-güven guard desenine
benzer) — kullanıcı mesajında kaba/küfürlü kelime tespit edilirse, sabit
S29 kalıp yanıtlarından biri ("Size siparişinizle yardımcı olmak isterim.
Ne alırdınız?") LLM'den bağımsız olarak döndürülür. Bu, üretim-anı
tutarsızlığından bağımsız garantili bir güvenlik katmanı sağlar.

Bu madde de veri kapsamının yanında **ayrı bir kod görevi** içeriyor —
ikisi birlikte planlanmalı, yalnızca veri eklemek yeterli olmayabilir.

---

## 5 — V06/E27: Alerji Kalıp Uyumu (Madde Sayısı Değil, 3 Zorunlu Öğe) (~20-25 kayıt)

**Mevcut V06 eval kriteri sorunlu:**
```python
_both(_any_of("tavuk","sütlaç","ayran","limonata","şalgam"),
      _both(_any_of("personel","teyit"),
            _not_contains("kesinlikle güvenli","hiç sorun yok")))
```
Bu yalnızca EN AZ BİR gluten-free ürün adının VE personel/teyit
kelimelerinden birinin geçmesini kontrol ediyor — modelin listeye
YANLIŞLIKLA gluten İÇEREN bir ürün eklemesini (ör. "Kremalı Mantar
Çorbası") YAKALAMIYOR. Gördüğümüz halüsinasyon tam olarak bu boşluktan
kaçtı.

**Reformülasyon — SENARYO_PLANI_FAZ1.md Karar 1'in 3 zorunlu öğesi:**
Doğru yanıtın "kaç ürün sayıldığı" değil, şu 3 yapısal öğeyi içerip
içermediği önemli:
1. **Kaynak atfı** — "Menü bilgilerimize göre" (veya eşdeğeri)
2. **Veri-durumu ifadesi** — "işaretli" (kesin "içermez" değil)
3. **Personel teyidi ricası** — "personelimize de teyit ettirmenizi
   rica ederim" (veya eşdeğeri)

**Yeni V06 PASS kriteri (taslak):**
```python
_both(
    _any_of("menü bilgilerimize göre", "menü verilerimize göre"),
    _both(
        _any_of("işaretli", "işaretlenmiş"),
        _both(
            _any_of("personel", "teyit"),
            _not_contains("kesinlikle güvenli", "hiç sorun yok"),
        ),
    ),
)
```
Bu son katman olmadan model 3 zorunlu öğeyi üretip yanına kesin güvence
ifadesi ("kesinlikle güvenli" gibi) eklese bile PASS alırdı — bu da Karar
1'in yasağını sessizce atlar, o yüzden yasak-ifade kontrolü ayrı bir
`_both` katmanı olarak geri eklendi.

Bu kalıp-uyum kontrolü, hangi ürünlerin sayıldığından BAĞIMSIZ çalışır.
Listedeki ürünlerin FİİLEN doğru olup olmadığı (gerçekten gluten içerip
içermediği) AYRI bir doğrulama katmanı gerektirir — bu, basit
string-eşleşmeyle kontrol edilemez, `menu.yaml`'a karşı gerçek bir çapraz
kontrol ister; `eval_gguf.py`'nin şu anki mimarisinin ötesinde, ileride
ele alınabilecek ayrı bir iyileştirme.

**E27 için de aynı kalıp geçerli:** "Glutensiz seçenek var mı?" sorusu
da bu 3-öğeli kalıba yönlendirilmeli — model şu an bu soru formuna
("var mı" tarzı, "ne önerirsiniz" değil) yeterince genellemiyor.

**Veri:** `gen_alerji_oneri.py`'ye ~20-25 yeni kayıt — hem "var mı" tarzı
alternatif soru formları hem de 3-öğe kalıbının pekiştirilmesi için.

---

## 6 — S12/E24: Runtime Guard (Kod, Veri Değil) — Düzeltilmiş Tasarım

> ✅ **UYGULANDI (5-6 Temmuz 2026):** Bu bölümdeki tasarım hayata geçirildi —
> ön koşul `detect_order()` fix'i (görev #21, commit a82dcf3), guard (görev
> #22, commit 69d60eb; 36 test `test_s12_guard.py`) ve E24 eval revizyonu
> (görev #16, commit 113136f). Aşağıdaki metin tasarım kaydı olarak korunuyor.

**Manuel test bulgusu (4 Temmuz 2026, Jetson'da `llm.generate_reply()` ile):**
İki ayrı tetikleyici denendi. (a) Saf kapanış ("Hayır, başka istemiyorum,
bu kadar.") → S12 hiç tetiklenmedi, eski toplamsız kapanışa döndü. (b)
`gen_karmasik.py`'nin birebir eğittiği ekle+kapat kalıbı ("Bir de ayran,
başka istemiyorum.") → özet+toplam ÜRETTİ ama onay sorusu YOK, doğrudan
"Afiyet olsun"a atladı. Sonuç: S12 eğitilmiş kalıpta bile eksik — veri tek
başına yeterli değil, E01/V01/V04 ile aynı ders. Runtime guard
kararlaştırıldı.

### ⚠️ İlk Guard Taslağındaki Bug

İlk önerilen `_is_closing_signal()`:
```python
def _is_closing_signal(text: str, lookup: list) -> bool:
    t = text.lower().replace('̇', '')
    if not any(trigger in t for trigger in _CLOSING_TRIGGERS):
        return False
    return not _match_items(t, lookup)  # BUG: burada
```
Mantık: "cümlede menü ürünü/alias'ı eşleşiyorsa bu bir ürün iptali,
kapanış değil" — `detect_order()`'ın cancel dalıyla çakışmayı önlemek
için tasarlanmıştı. **Ama asıl hedef senaryo tam olarak bunu kırıyor:**
"Bir de ayran, başka istemiyorum." cümlesinde "ayran" bir menü ürünü —
`_match_items()` onu bulur → fonksiyon `False` döner → guard **tam
olarak eğitilmiş hedef kalıpta devre dışı kalır**. Fonksiyon, "ürün
EKLENİYOR" (ayran, yeni) ile "ürün İPTAL EDİLİYOR" (köfte, mevcut sepetten
çıkar) arasındaki farkı salt isim eşleşmesiyle ayırt edemiyor.

### Ön Koşul — `detect_order()` Bug Şüphesi (Guard'dan ÖNCE Doğrulanmalı)

Statik kod analizi ek bir sorun gösteriyor: `OrderTracker.detect_order()`
şu sırayla çalışıyor:
```python
is_cancel = any(v in t for v in _CANCEL_VERBS)  # "istemiyorum" → True
if is_cancel:
    for name, price, qty in _match_items(t, self._lookup):  # "ayran" bulunur
        self._remove_item(name, price, qty)  # ayran sepette YOK → no-op
    return  # ERKEN RETURN — "add" dalına hiç ulaşmıyor
```
"Bir de ayran, başka istemiyorum." cümlesinde "istemiyorum" `_CANCEL_VERBS`
içinde olduğu için `is_cancel=True` oluyor, cancel dalı çalışıyor,
`_match_items` "ayran"ı buluyor ama `_remove_item` bir şey silmiyor (ayran
zaten sepette yok) ve fonksiyon **erken `return` ediyor** — ayran hiçbir
zaman `_add_item` ile eklenmiyor. **Bu, guard'dan bağımsız, önceden var
olan bir bug** — `detect_order()`'ın kendisi bu tür ekle+kapat cümlelerini
yanlış yorumluyor olabilir. **Test edilmeden guard tasarımı ilerletilmemeli**
(bkz. Sıradaki Görevler #1, PROJE_DURUMU.md).

### Düzeltilmiş Yaklaşım

Guard kendi ürün-eşleşme mantığını YÜRÜTMESİN — `detect_order()` zaten
çalıştıktan SONRA `order_tracker.items`'ın güncel durumuna güvensin.
`_is_closing_signal()` yalnızca kapanış ifadesinin metinde var olup
olmadığına baksın, ürün eşleşmesiyle hiç ilgilenmesin:

```python
def _is_closing_signal(text: str) -> bool:
    """Yalnızca kapanış kalıbı var mı diye bakar — ürün eşleşmesiyle
    ilgilenmez, detect_order() zaten order_tracker.items'ı güncellemiş olmalı.
    """
    t = text.lower().replace('̇', '')
    return any(trigger in t for trigger in _CLOSING_TRIGGERS)
```

Ana döngüdeki sıralama da buna göre değişir: **önce `detect_order(user_text)`
çağrılır** (ekle/iptal/takas işlensin, `order_tracker.items` güncellensin),
**sonra** `_is_closing_signal(user_text)` kontrol edilir ve TUR 1 özeti
`order_tracker.items`'ın (artık güncel) durumundan kurulur. Bu, mevcut
kodun zaten `detect_order()`'ı bill-check'ten ÖNCE çağırma prensibiyle
("Race condition fix" yorumu, `demo_usb.py` satır ~1059) tutarlı — aynı
sıralama mantığı burada da geçerli.

**Kalan risk:** `detect_order()`'ın kendisi ekle+kapat cümlelerini yanlış
işliyorsa (yukarıdaki ön koşul bug'ı doğrulanırsa), guard doğru sıralansa
bile yanlış sepet durumundan özet kuracaktır. Bu yüzden ön koşul testi
guard implementasyonundan önce gelmeli — sıra: (1) `detect_order()` testi,
(2) gerekirse `detect_order()` düzeltmesi (örn. cancel dalına girmeden
önce, eşleşen ürün zaten sepette var mı diye kontrol et — yoksa bu bir
"iptal" değil, muhtemelen "ekle" niyetidir), (3) düzeltilmiş
`_is_closing_signal` guard'ı ekle.

**TUR 2 (onay sonrası kapanış) aynı mantıkla deterministik:**
`awaiting_confirmation` state'i True iken kullanıcı onay kelimesi
(evet/tamam/olur/tabii/peki) söylerse, LLM'e hiç sormadan sabit
"Afiyet olsun!" döndürülür — hesap toplamı override'ıyla birebir aynı
güven seviyesi. Yalnızca onay dışı bir şey söylenirse (fikir değiştirme,
yeni ürün ekleme) normal akışa (LLM/`detect_order()`) düşülür.

---

## KAPANIŞ NOTU — gen_karmasik.py İncelemesi (6 Temmuz 2026): Veri Maddesi GEREKSİZ

**Görev #24 araştırıldı ve kapatıldı.** Şüphe, `gen_karmasik.py`'nin assistant
örneklerinin özet+onay+kapanışı tek turda birleştirdiğiydi — **çürütüldü**:
150 kaydın programatik sayımı, 150/150'sinin doğru yapıda olduğunu gösterdi
(özet turu "Onaylıyor musunuz?" ile bitiyor, ardından AYRI user-"Evet" turu,
ardından AYRI ve toplamsız "Afiyet olsun" asistan turu; birleşik desen: 0).

Kök neden veri değil, **model genellemesi + kanonik sistem promptu çelişkisi**:
5460 karakterlik kanonik promptun kapanış kuralı hâlâ S12-öncesi politikayı
("...mutlaka 'afiyet olsun' ifadesiyle bitir. BU DURUMDA TOPLAM SÖYLEME")
emrediyor — hem tüm eğitim kayıtlarının system mesajında hem inference'ta
(`llama_cpp_backend.py` `_SYSTEM_TEMPLATE`). Model iki çelişen sinyali
harmanlıyor: fine-tune'dan özet+toplam, prompttan afiyet-kapanışı → onay
sorusu düşüyor.

**Sonuç:** S12/E24 runtime guard (görev #22) bu davranışı LLM'den bağımsız,
deterministik olarak garanti ettiği için **C paketine gen_karmasik türü yeni
veri maddesi EKLENMEYECEK** — veri zaten doğru, fazlası çelişen promptu
yenemez. Kalıcı hizalama istenirse doğru adres W11 kural revizyonu (kanonik
prompt güncellemesi, wbot_v5 döngüsünde; görev #16 E24 eval revizyonuyla
birlikte ele alınmalı) — veri üretimi değil.

---

## Üretim Ortamı ve Kalite Kontrol

- **Şablon script (Python, `gen_*.py`) ile üretilebilir:** S34/V02 (madde
  1), küfür genişletme (madde 4), alerji kalıp düzeltmesi (madde 5) —
  bunlar A/B paketindeki mevcut desenlere yakın, LLM API gerekmez.
- **LLM API (Gemini/Claude) önerilir:** S41 (madde 2) ve anti-hallüsinasyon
  (madde 3) — "doğal konuşma" çeşitliliği gerektiren, şablonla zayıf kalan
  senaryolar.
- **Zorunlu doğrulama adımları (veri üretildiğinde, kaynak fark etmeksizin):**
  1. `python scripts/audit_dataset.py --dataset <yeni_dosya.jsonl>` — 0
     ihlal olmadan birleştirmeye geçme.
  2. Elle örneklem incelemesi — özellikle LLM API çıktısı için en az %10
     örneklem elle okunmalı.
  3. Sistem promptu kanonik 5460 karakter olmalı (`wbot_finetune_v1.jsonl`
     ilk kayıttan okunarak, hardcode edilmeden).

## Boyut Notu

C paketi ~175-185 kayıt (veri) + 3 kod görevi (E01/V01 post-processing,
V04 runtime guard, S12/E24 runtime guard) ile "tam" sayılabilir. Nihai
boyutu bir sonraki eval turu belirlesin — özellikle V06/E27 düzeltmesinin
gerçekten kalıp-uyumunu sağlayıp sağlamadığı, V04'ün veri+guard
kombinasyonuyla düzelip düzelmediği, ve S12 guard'ının `detect_order()`
ön koşul düzeltmesiyle birlikte gerçekten çalışıp çalışmadığı yeniden
test edilmeli.
