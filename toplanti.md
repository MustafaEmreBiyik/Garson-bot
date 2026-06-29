# W-BOT Proje Toplantısı — Notlar ve Analiz

**Tarih:** 26 Haziran 2025 (ses kayıtları 19:39 ve 20:00 başlıklı, ardışık tek görüşme)
**Katılımcılar (transkriptten çıkarılan):**
- Sen (W-BOT AI/sesli asistan geliştiricisi)
- İşletme/yatırımcı tarafı ("abi" diye hitap edilen, restoran pilotu ve iş modeli sorularını soran kişi)
- Ahmet abi (sahada test sürecinden bahsedilen kişi — "mekanikçi gibi" test edecek)
- Yalçın abi (ROS / navigasyon / donanım geliştiricisi — görüşmede fiziksel olarak yok, üçüncü şahıs olarak konuşuluyor)
- Bir mekanik ekip üyesi (kendini "stajyer" olarak tanımlıyor, Yalçın'ı savunuyor ama zaman yönetimi sorununu teyit ediyor)

> Not: Kayıt otomatik transkripte dökülmüş, konuşmacı etiketleri yok ve bazı bölümler STT hatalarından dolayı anlam kaymış olabilir. Bu nedenle aşağıdaki özet **konuya göre** gruplanmıştır, kişi bazlı alıntı yapılmamıştır.

---

## 1. İş Modeli ve Ürünleşme Vizyonu

- Pilot hedefi: yaklaşık **20 garson çalıştıran bir restoran** → önce 3-4 robot ile test.
- Tek bir "elele" (genel-geçer) model geliştirilmeyecek; **restoran tipine göre konfigüre edilebilir** bir asistan hedefleniyor (kebapçı vs. lüks/a la carte restoran farklı ton kullanacak).
- Şu an için **tamamen resmi/natural** bir dil hedefleniyor — ChatGPT'nin ilk mesajdaki tonu örnek alınıyor: ne aşırı resmi ne aşırı samimi.
- Aşırı kişiselleştirme şimdilik gereksiz görülüyor: "işlem gücümüz belli, kocaman bir sorumluluğumuz yok" — ilk fazda tek restoran/şube odaklı.
- Uzun vadeli hedef: ürünü **stabil + referans gösterilebilir** hale getirip yatırımcı toplama aracı olarak kullanmak. Bunun ön koşulu: soru-cevapta kopmama + navigasyonda takılıp kalmama.

**Çıkarım / aksiyon yok**, ama bu, persona ve gecikme kararlarının "neden" kısmını netleştiriyor — PROJE_DURUMU.md'ye bağlam notu olarak eklenebilir.

---

## 2. Konuşma Tarzı / Persona Kararları

- **Açılış cümlesi standardize edilecek**: "Hoş geldiniz" hem wake-word tetiklendiğinde hem masaya yaklaşıldığında kullanılabilir.
- **Yanıt hızı segmentasyonu** istendi:
  - Rutin/kısa sorular ("Ne alırsınız?", basit onaylar) → **gecikme minimumda** olmalı, 5 saniye gibi bir bekleme kabul edilmiyor.
  - Düşünce gerektiren sorular (öneri isteme, "bugün ne önerirsin" gibi) → biraz bekleme kabul edilebilir.
  - → Bu, `demo_usb.py` / latency optimizasyonu için **soru tipine göre farklı davranış** ihtiyacını doğruluyor (örn. basit intent'lerde kısa max_tokens + hızlı template, açık uçlu sorularda normal LLM akışı).
- **Ses tonunun etkisi çok yüksek** vurgulandı ("ses tonu %80" deniyor — abartılı ama net bir sinyal): enerjik, net, pozitif, **samimi ama "yavşak" değil**. Karşı tarafa "bizden biri" hissi vermesi isteniyor, robotik/mekanik "ne istiyorsun / tamam getiriyorum" tonundan kaçınılmalı.
- Restoran tipine göre **farklı ses paketleri** satılabilir fikri ortaya atıldı (a la carte restoran ↔ köfteci Yusuf tarzı esnaf üslubu), olası fiyatlandırma/konfigürasyon seçeneği olarak not edildi.
- **Kötü niyetli / anlamsız / saçma girdilere** ("git chef'i çağır, bana çorba yapsın" gibi) nasıl cevap üretileceği netleşmedi. Çözüm yaklaşımı olarak veri setine geri bildirimle yeni örnek ekleme öngörülüyor, ancak girdi uzayının pratikte sınırsız olduğu açıkça kabul edildi — **kapalı bir çözüm yok, riskli alan**.

**Aksiyon:**
- [ ] Persona/ton için 2-3 örnek ses üretip ekibe onaylatma (enerjik + samimi, "yavşak değil" çizgisi).
- [ ] Kötü niyetli/anlamsız girdi davranışı için ayrı bir test seti ve fallback stratejisi tasarlanmalı (mevcut E19/W15/W16 listesine ek madde olabilir).

---

## 3. Tetikleme: Wake Word + QR Sistemi

- Şu anki durum: **"hey garson" wake word**, tetiklendiğinde sadece o kişiye odaklanma (mevcut `demo_usb.py` davranışı ile uyumlu).
- Planlanan ek katman: **QR kod tabanlı çağırma**. Her masada QR olacak; müşteri QR okutup "garson çağır" dediğinde masa numarası bilinerek robot doğrudan o masaya yönlendirilecek.
- Bunun için altyapı: restoranın **2D haritası** çıkarılacak, masalar haritaya yerleştirilecek, her masa için ayrı **"teslim noktası"** ve **"konuşma noktası"** tanımlanacak.
- Robot konuşma noktasına ulaştığında **ROS/flow yönetimi → AI tarafına "geldim" sinyali** verecek, bu sinyal diyaloğun (örn. "Hoş geldiniz") başlamasını tetikleyecek. → Bu, AI modülü ile ROS arasında **net bir event/sinyal arayüzü** gerektiriyor; şu an böyle bir entegrasyon noktası `PROJE_DURUMU.md`'de tanımlı değilse eklenmeli.
- **360° ses kaynağı belirleme** ("hangi masadan 'hey garson' denildi") **Faz 2'ye** bırakıldı — mikrofon array gerektirdiği, açısal + derinlik hesaplama karmaşıklığı nedeniyle Faz 1 kapsamı dışında tutuldu.

**Aksiyon:**
- [ ] AI ↔ ROS arasında "konuşma noktasına ulaşıldı" event'i için arayüz tanımı (mesaj formatı, hangi taraf tetikler).

---

## 4. Çoklu Dil Desteği — Karara Bağlanmamış

Üç alternatif tartışıldı, **hiçbiri seçilmedi**:

1. **Dil algıla + model switch**: Her dil için ayrı küçük model, dil değişimi algılandığında modeli sıfırdan yükleyip geçiş. Sorun: model yükleme süresi gecikme yaratıyor.
2. **Sabit bekletme mesajı**: "Dil değişikliği için lütfen bekleyiniz" + 5-30 sn bekleme, ardından ilgili dil modeline geçiş.
3. **Çeviri tabanlı yönlendirme**: Yabancı dildeki isteği anlayıp arka planda bir "görevli"ye ileterek karşılama — ama bu fikir, sistemde "garson" kavramının olmadığı (sadece robot+müşteri var) gerçeğiyle çakışıyor; net değil, muhtemelen restoranın panel/POS sistemine yönlendirme anlamına geliyor.

Gerekçe: offline + küçük model kısıtı nedeniyle **Türkçe odaklı eğitim kalite kaybı riski** taşıyor çoklu dil eklemek. Faz 1 kapsam tanımında ayrıca "dil değiştiremeyecek" notu var → **pratikte Faz 1 = sadece Türkçe** demek.

**Aksiyon:**
- [ ] Çoklu dil mimarisi (model switch / bekletme / yönlendirme) için karar toplantısı — şu an METODOLOJI.md'de "neden reddedildi" bölümüne girecek netlikte bir tartışma yok, kayda geçirilmeli.

---

## 5. Sipariş Akışı ve Panel/Ekran Entegrasyonu

- Robot üzerinde **ekran** olacak; sesli sipariş sırasında ekran **senkron şekilde konfigüre olacak** (örn. "et yemekleri" sayılırken ekranda et yemekleri menüsü açılacak).
- Sipariş hem **sesli** hem **ekrandan dokunarak** verilebilecek.
- Sipariş özeti tekrarlanıp (sözlü veya ekran üzerinden) **onay alındıktan sonra** restoran sistemine işlenecek.
- Şu anki MVP zaten bu mantıkla uyumlu: sipariş bir **JSON dosyasına** yazılıyor, iptal/değişiklik de JSON üzerinden yönetiliyor (mevcut `OrderTracker` yaklaşımı). İşletme tarafı bunu **yeterli** buldu — "JSON'dan yönetebiliyorsa bizim için kolay, restoran yönetim sistemine entegrasyonu biz hallederiz" dendi.

**Sonuç:** Bu madde mevcut mimariyi doğruluyor, değişiklik gerektirmiyor. Ekran/panel senkronizasyonu (ROS/UI tarafı) ayrı bir iş paketi.

---

## 6. Donanım ve ROS / Navigasyon Durumu

- **Mevcut robot:** Jetson Nano, Ubuntu 20.04, **ROS 1 Noetic + Foxy** kombinasyonu (Nano'da Humble çalışmıyor, bu yüzden Foxy seçilmiş).
- **Yeni kart (Jetson Orin NX benzeri, Nano ile aynı boyutta):** Ubuntu 22.04 geliyor → **ROS 2 Humble'a geçiş** gündemde ("Foxy biraz zayıf kalıyor, Humble daha modern, dengeli olur"). Ancak karar kesinleşmedi: "önce entegre etmemiz lazım" deniyor.
- **SLAM + Nav2** ikilisi çalışıyor: SLAM haritayı genişletip düzeltiyor, Nav2 hedef ataması ile hareketi sağlıyor.
- **Restoran haritalama** iki yöntemle planlanıyor: (a) Nav2 Frontier Exploration ile otonom dolaşıp harita çıkarma, (b) bir 2D çizim aracıyla restoran planının çizilip doğrudan ROS'a yüklenmesi.
- **Masa algılama sorunu:** Lidar masa **ayaklarını** görüyor ama masa **yüzeyini/gövdesini** görmüyor. Çözüm: stereo/derinlik (depth) kamera, ~70cm-2m menzilde masa üstü algılama planlanıyor — henüz uygulanmadı.
- **Masa hareketi (birleştirme/kaydırma) sorunu:** Masalar fiziksel olarak taşındığında robot hâlâ eski konumu "biliyor" → operasyonel hata olarak görülüyor. Önerilen (henüz hayata geçmemiş) çözüm: masa kenarlarına **QR etiketi** + teslim noktasına yaklaşırken **beklenen mesafe ile ölçülen mesafeyi karşılaştırma** mantığı (fark varsa ek yaklaşma/düzeltme).
- **Hareketli engellerden kaçınma eksik:** Şu an hareketli engeller sabit engel gibi algılanıyor — robot engelin önüne kadar gidip sonra dönüyor, öngörülü/erken kaçınma manevrası yok. Costmap derinlik parametresiyle ilgili olabileceği söyleniyor ama test edilmemiş.
- **Kaynak paylaşımı:** GPU + RAM AI/LLM tarafına ayrılacak, **CPU navigasyon/ROS tarafına** ayrılacak. Robot hareket ederken AI/konuşma döngüsünün duraklatılması, robot durduğunda ROS'un beklemeye alınması planlanıyor. İlk haritalama sırasında ROS'un tüm çekirdekleri %100 kullanabildiği ve bunun optimize edilmesi gerektiği not edildi.
- **Donanım detayları:** Yedek WiFi anteni konektörünün yeri üzerinde belirsizlik yaşandı, fiziksel olarak teyit edilmeye çalışıldı (uzun mesafe için 2 anten önerisi). Kamera bağlantısının **USB 3.0** üzerinden yapılması gerektiği konuşuldu (USB 2.0 yetersiz).

**Bu kısım W-BOT (AI) tarafını şu noktalardan ilgilendiriyor:**
- AI modülünün CPU kullanımı düşük tutulmalı (CPU önceliği ROS'ta) — Jetson'daki `llama_cpp_backend.py` ayarlarında GPU-ağırlıklı offload tercih edilmeye devam etmeli.
- Robot hareket halindeyken AI/STT-TTS döngüsünün **duraklatılması** gerekiyor — bu, AI tarafında "hareket halinde mikrofon dinleme yapma" durumu için bir state/flag ihtiyacı doğuruyor (ROS'tan AI'ya "hareket ediyorum" sinyali).

**Aksiyon:**
- [ ] AI ↔ ROS arasında "robot hareket ediyor / durdu" state sinyali tanımı (madde 3'teki "geldim" sinyaliyle birlikte ele alınabilir).
- [ ] ROS 2 Humble geçiş kararı netleşince, AI tarafında etkilenen bir şey olup olmadığı kontrol edilmeli (muhtemelen yok, ROS katmanı soyutlanmış durumda).

---

## 7. Sürekli Öğrenme / Model Güncelleme Vizyonu (Uzun Vadeli)

- Saha kullanımından **log toplama**, beğenilmeyen cevapların geri bildirimle iletilmesi, ve bu verilerle **arka planda (sunucuda) periyodik model güncellemesi** vizyonu konuşuldu.
- Güncellemenin robotun **pasif olduğu zamanlarda** (sipariş almadığı anlarda) yapılması öneriliyor.
- Bu özellik **internet bağlantısı olan senaryolar için** geçerli — şu anki offline mimariyle doğrudan ilgili değil, ileri vadeli bir özellik olarak not edildi.

**Not:** Bu, wbot_v4/v5 döngüsünün (Colab eğitimi → GGUF dönüşümü → Jetson'a deploy) gelecekte **yarı-otomatik bir pipeline'a** dönüşmesi gerektiğine işaret ediyor. Şimdilik manuel süreç (mevcut iş akışı) yeterli, ama bu vizyon not olarak METODOLOJI.md'ye eklenebilir.

---

## 8. Faz 1 / Faz 2 Kapsam Ayrımı (Netleşen Karar)

| | **Faz 1** | **Faz 2** |
|---|---|---|
| Odak | Tek kişi, "hey garson" diyen ilk kişi | Aynı masada birden fazla kişi, ayrı sipariş |
| Dil | Sadece Türkçe (dil değiştirilemez) | Çoklu dil (yöntem belirsiz) |
| Tetikleme | Wake word + QR (masa bazlı) | + 360° ses kaynağı belirleme |
| Masa ayrımı | Yok (bir masaya odaklanma) | Masalar arası ayırt etme (komşu masadan etkilenmeme) |
| Navigasyon | Sabit engellerden kaçınma | Hareketli engellerden öngörülü kaçınma |

Bu tablo, sizin paylaştığınız "Bilinen Açık Sorunlar" listesindeki önceliklendirmeyle **uyumlu** — özellikle W16 (alerji+öneri) ve E19/W15 (post-processing) gibi maddeler Faz 1 kapsamında kalıyor.

---

## 9. Proje Yönetimi Notları

- Gereksinimlerin netleşmemiş olmasının ROS geliştiricisinin (Yalçın abi) MVP'yi **tahmine dayalı** şekilde tasarlamasına yol açtığı kabul edildi; bu görüşme sayesinde gereksinimlerin netleştiği belirtiliyor.
- **Haftalık / birkaç günde bir feedback döngüsü** kurulması öngörülüyor: geliştirme yapıldıkça çıktı kontrol edilip karşılıklı geri bildirim verilecek.
- Yalçın abi'nin **zaman yönetimi / teslim süreleri** konusunda ekip içinde (saygılı ama net) bir kaygı dile getirildi. Onun işi belirli bir noktaya (1.0) getirip teslim etmesi bekleniyor.
- ROS geliştirme tarafında şu ana kadar geçen süre **~1-1.5 ay**, ancak final dönemi ve paralel projeler nedeniyle yavaşladığı belirtildi; "realistik olmak lazım" vurgusu yapıldı — Faz 1 sonu için **kesin bir tarih verilmedi**, "birkaç ay içinde" gibi muğlak bir çerçeve çizildi.
- Cumartesi müsaitliği teyit edildi (demo/buluşma için).

---

## 10. Açık Riskler / Netleşmemiş Kararlar (Özet)

1. Kötü niyetli/anlamsız/saçma girdilere karşı davranış stratejisi — kapalı değil, açık uçlu risk.
2. Çoklu dil mimarisi — üç alternatif var, hiçbiri seçilmedi.
3. Masa hareketi/QR doğrulama mantığı — fikir var, kod/sistem yok.
4. Hareketli engel kaçınma — geliştirilmedi, test edilmedi.
5. ROS 2 Humble'a geçiş — niyet var, zamanlama ve entegrasyon planı yok.
6. Faz 1 teslim tarihi — net değil.
7. AI ↔ ROS arayüz sinyalleri ("geldim", "hareket ediyorum") — kavramsal olarak konuşuldu, teknik tanım yok.

---

## 11. Aksiyon Maddeleri

**W-BOT (AI/ses) tarafı — sizin sorumluluğunuz:**
- [ ] Açılış cümlesi ("Hoş geldiniz") standardizasyonu — `demo_usb.py` veya prompt seviyesinde.
- [ ] Soru tipine göre yanıt hızı segmentasyonu (rutin vs. düşünce gerektiren sorular).
- [ ] Persona/ses tonu için örnek ses üretimi ve onay süreci.
- [ ] Kötü niyetli/anlamsız girdi davranışı için test seti + strateji araştırması.
- [ ] AI ↔ ROS sinyal arayüzü için teknik öneri hazırlama ("konuşma noktasına geldim", "hareket ediyorum/durdum").
- [ ] Çoklu dil mimarisi kararı için METODOLOJI.md'ye bir "değerlendirilen alternatifler" bölümü açılması.

**ROS/Donanım tarafı (Yalçın abi) — takip edilecek:**
- [ ] QR + 2D masa haritalama sistemi.
- [ ] Depth kamera ile masa üstü algılama.
- [ ] Hareketli engel kaçınma geliştirmesi.
- [ ] ROS 2 Humble geçiş değerlendirmesi.
- [ ] Donanım: anten konektörü teyidi, USB 3.0 kamera bağlantısı.

**Genel:**
- [ ] Haftalık/birkaç günlük feedback döngüsünün fiilen başlatılması.
- [ ] Demo planlaması (Cumartesi müsaitliği üzerinden).

---

*Bu doküman, 26 Haziran 2025 tarihli ses kayıtlarının (Ses_260625_193949 ve Ses_260625_200023) analizinden üretilmiştir. Konuşmacı etiketleri transkriptte bulunmadığından bazı atıflar yaklaşıktır; kritik kararlar için orijinal kayıtla teyit önerilir.*
