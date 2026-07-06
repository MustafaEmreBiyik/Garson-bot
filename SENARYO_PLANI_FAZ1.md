# W-BOT Faz 1 Senaryo Planı — Kararlar ve Yeni Senaryolar
**Tarih:** 3 Temmuz 2026 | **Durum:** Onaylandı (senaryo değerlendirme danışması sonucu)

Bu doküman Faz 1 senaryo planlamasındaki iki açık kararı, davranış politikalarını
(küfür, sessizlik) ve eval listesine eklenecek yeni senaryoları kayda geçirir.
İlgili eval: `scripts/eval_gguf.py` (mevcut 32 senaryo + `--v4-targets` hedefleri).

---

## Karar 1 — S19: Alerji + Öneri → **Seçenek B (filtrele + uyarı)**

Müşteri: *"Glüten alerjim var, ne önerirsiniz?"*

**Karar:** Menüden filtrele + uyarı ekle. Önkoşulların üçü de bugün sağlanıyor:

1. ✅ Alerjen bilgisi ürün bazında `menu.yaml`'da tanımlı (`allergens` alanı).
2. ✅ Alerjen bilgisi sistem promptuna giriyor (`llama_cpp_backend._build_menu_text()`
   → "içerir: gluten, süt ürünü, kuruyemiş"). Model dünya bilgisinden değil menü
   verisinden konuşur.
3. ⚠️ Menü değişiminde `allergens` alanını güncelleme sorumluluğu restoranda
   tanımlanmalı — operasyonel süreç, mutfak onayı şart.

**Kanonik yanıt kalıbı** (eğitim verisine bu üç öğeyle işlenecek):

> "Menü bilgilerimize göre Izgara Tavuk Salata, Fırın Sütlaç ve Yayık Ayran glüten
> içermiyor olarak işaretli. Mutfakta çapraz bulaşma olabileceği için personelimize
> de teyit ettirmenizi rica ederim."

Zorunlu üç öğe:
- **"Menü bilgilerimize göre"** — kaynak atfı; robot kendi adına güvence vermez.
- **"işaretli"** — "içermez" kesinliği yerine veri durumu ifadesi.
- **Personel teyidi rica olarak** — seçenek değil, öneri.

Yasaklar (audit kuralı ile uyumlu): "kesinlikle güvenli", "hiç sorun yok",
"gönül rahatlığıyla yiyebilirsiniz" tarzı kesin güvence ifadeleri.

Ek gereksinim: Alerji beyan edildiyse sipariş POS/ekrana **alerji notu** ile
düşmeli; servis eden personel ikinci teyidi yapar. (Sipariş-ekran yapısal verisi
işine bağlanacak — toplanti.md görevi.)

---

## Karar 2 — S12: Onay Öncesi Özet → **Her zaman özet, koşulsuz**

**Karar:** Ürün sayısından bağımsız, onay öncesi her zaman toplu özet + toplam tutar:

> "Siparişiniz: Izgara Köfte, Et Döner ve bir Limonata. Toplam 590 TL.
> Onaylıyor musunuz?"

Gerekçe: ekran yok — özet, sipariş mutfağa gitmeden önceki son hata bariyeri;
ASR hataları tur bazlı onayla yakalanamaz; koşullu davranış (3+ ürün) müşteri
için öngörülemezlik yaratır. Tek üründe özet zaten doğal olarak kısa.

**⚠️ W11 kuralıyla çelişki — çözüm gerekli:** Mevcut kural (E24) "sipariş
kapanışında toplam söylenmemeli" der. Yeni akışta sıralama şöyle revize edilir:

1. Müşteri "bu kadar / başka istemiyorum" → robot **özet + toplam + "Onaylıyor musunuz?"**
2. Müşteri "evet" → robot **"Afiyet olsun"** (toplamsız — W11 burada geçerli kalır)

Yani W11 yasağı onay-sonrası kapanış cümlesine daralır; E24 eval'i wbot_v4'te bu
akışa göre revize edilecek. Özet cümlesi için 25 kelime sınırına işlevsel istisna
tanımlanır (çok kalemli siparişte özet sınırı aşabilir).

---

## Politika — S29: Küfür / Kabalık

- **1. seferde:** Ders vermeden tek cümle + işe dönüş:
  *"Size siparişinizle yardımcı olmak isterim. Ne alırdınız?"*
- **2. seferde / ısrarda:** Kibar kapatma + devir: *"Personelimiz size yardımcı
  olacaktır."* → oturum sonlandırılır.
- **Asla:** espri, taklit, azarlama, karşılık. (Robotlar bilinçli provoke edilir —
  renksiz/tepkisiz yanıt trollemeyi ödüllendirmez.) Olaylar personel için loglanır.

## Politika — S03: Sessizlik (runtime davranışı — demo_usb.py / VAD katmanı)

LLM eval'i değil, runtime akışı. `CONVO_HOLD_S` (60 sn oturum tutma) ile ayrı katman:

1. Karşılamadan sonra **~8 sn** bekle (müşteri menüye bakıyor olabilir; sessizlik
   çoğu zaman kasıtlı).
2. **Tek** yeniden istem, birebir tekrar değil:
   *"Hazır olduğunuzda menüden dilediğinizi sorabilirsiniz."*
3. **~10 sn** daha sessizlik → kibar çekilme + geri dönüş yolu:
   *"Hazır olduğunuzda 'Hey Garson' demeniz yeterli."* → wake-word moduna dön.
4. Toplamda en fazla 2 istem (karşılama + 1 reprompt). Üçüncü istem "başında
   dikilen garson" hissi verir.

---

## Yeni Senaryolar (Faz 1'e ek — eval hedefleri `--v4-targets`)

Veri kontrolü bulgusu: modifikasyon kalıpları train setinde binlerce örnekle var
ama eval'de hiç ölçülmüyordu; "stok yok" train setinde 1, "ne zaman gelir" 2
satırda geçiyor (gerçek veri boşluğu).

| Kod | Eval | Senaryo | Durum |
|-----|------|---------|-------|
| S33 | V01 | Modifikasyon, sipariş anında ("acılı olsun") | Veri var, eval eklendi |
| S34 | V02 | Modifikasyon, sipariş sonrası ("köfte acısız olsun") | Veri var, eval eklendi |
| S35 | V03 | Sipariş + alerjen çakışması (künefe + fıstık alerjisi) | Eval eklendi; wbot_v4 verisi gerekli |
| S36 | V04 | Küfür — sakin sınır + işe dönüş | Eval eklendi; wbot_v4 verisi gerekli |
| S37 | V05 | Pratik soru (tuvalet) — personele yönlendir, uydurma yok | Eval eklendi |
| S38 | V06 | S19-B: glüten + öneri → filtrele + teyit ricası | Eval eklendi; wbot_v4 hedefi |
| S39 | — | Ürün tükendi (`availability: false`) | Önce context builder desteği: `_build_menu_text()` şu an `availability` alanını yok sayıyor. wbot_v4 kapsamı |
| S40 | — | "Yemek ne zaman gelir / nerede kaldı?" → dürüst yanıt + personel | wbot_v4 veri üretimi (mevcut veride 2 örnek) |
| S41 | — | İki ardışık anlaşamama → "Personelimizi çağırıyorum" eskalasyonu | Çok-turlu; wbot_v4 veri + eval |

Faz 2'ye bırakıldı: çoklu konuşmacı/kalabalık masa, çocuk sipariş veriyor,
hesap bölme, porsiyon soruları.

---

## Uygulama Adımları

1. ✅ Yeni eval hedefleri `scripts/eval_gguf.py`'ye `--v4-targets` bayrağıyla
   eklendi — varsayılan koşuda 32 senaryo/31 geçer metriği değişmez; wbot_v4
   sonrası bayrakla ölçülür, hedefe ulaşınca ana listeye taşınır.
2. wbot_v4 dataset üretimi (PROJE_DURUMU görev 3) şu konuları da kapsayacak:
   S19-B kanonik kalıbı (W16), onay özeti akışı (S12 + E24 revizyonu), küfür
   politikası (S36), sipariş+alerjen çakışması (S35), stok-yok (S39, önce
   context builder), sipariş durumu (S40), eskalasyon (S41).
3. Restoran operasyonu: `allergens` alanı güncelleme sorumluluğu + mutfak onayı
   süreci tanımlanacak (Karar 1 önkoşul 3).
4. S03 sessizlik akışı `demo_usb.py` runtime'ına uygulanacak (8 sn → 1 reprompt
   → 10 sn → wake-word'e dönüş).

## Doğrulama

- `python3 scripts/eval_gguf.py` → mevcut metrik korunur (yazıldığında wbot_v3: 31/32; güncel wbot_v4 baseline 6 Temmuz 2026: 29/32 — E24, Karar 2'ye göre revize edildi, bilinen boşluk).
- `python3 scripts/eval_gguf.py --v4-targets` → V01-V06 dahil koşar; wbot_v3'te
  bir kısmının KALDI çıkması beklenir (bunlar wbot_v4 hedefleri).
- wbot_v4 verisi üretilince S19-B kalıbı `scripts/audit_dataset.py` kesin-güvence
  kuralından geçmeli.
