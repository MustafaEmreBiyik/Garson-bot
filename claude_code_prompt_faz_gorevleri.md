Sen W-BOT projesinin ana geliştirme asistanısın. Bu görevde **sadece ses/AI tarafıyla** ilgileniyoruz — ROS2, navigasyon, mekanik, donanım (anten, kamera, Jetson kartı) konuları **bu görevin kapsamı dışında**, onlara hiç dokunma.

## Bağlam

Ekip mekanik/ROS tarafıyla bir görüşme yaptı (toplanti.md dosyasında özetlendi). Bu görüşmeden çıkan kararların önemli bir kısmı ses/AI tarafını da etkiliyor. Senden istediğim: bu kararları mevcut kod tabanı ve PROJE_DURUMU.md'deki mevcut görev listesiyle eşleştirip, **Faz 1 ve Faz 2 için somut, dosya bazlı bir görev listesi** çıkarman.

## Yapman Gerekenler (sırayla)

1. Önce `PROJE_DURUMU.md` ve `METODOLOJI.md`'yi oku — mevcut mimari, eval sonuçları, açık sorunlar (E19/W15, W16, gürültülü ortam) ve "Kritik Kurallar" bölümünü hatırla.
2. `toplanti.md`'yi oku (repoya ekledim / ekleyeceğim — yoksa bana sor, kod tabanını tahmin ederek doldurma).
3. toplanti.md içinden **sadece ses/AI tarafını ilgilendiren** maddeleri ayıkla. Aşağıdakiler kesinlikle bu kapsamın DIŞINDA, listeye dahil etme:
   - QR/masa haritalama, 2D harita çıkarma, Frontier Exploration
   - Depth kamera ile masa algılama, hareketli engel kaçınma
   - ROS 2 Humble geçişi, donanım/anten/kamera bağlantı tipi
   - CPU/GPU kaynak paylaşımı (bu ROS tarafının sorumluluğu)

   Sadece şunlarla ilgilen: konuşma tarzı/persona, yanıt gecikmesi/latency davranışı, wake word ve diyalog başlatma mantığı, sipariş akışı ekrana yansıyacak veri yapısı, kötü niyetli/anlamsız girdi davranışı, çoklu dil, sürekli öğrenme/log toplama vizyonu.

4. Her madde için şunu belirle:
   - **Faz 1 mi Faz 2 mi** (toplanti.md'deki Faz 1/Faz 2 tablosuna göre — Faz 1 = tek kişi, tek dil, QR çağırma + temel sesli sipariş; Faz 2 = çoklu kişi/masa ayrımı, çoklu dil, gelişmiş senaryolar)
   - **"YENİ EKLENECEK"** mi yoksa **"MEVCUDU DEĞİŞTİR"** mi (mevcut `demo_usb.py`, `llama_cpp_backend.py`, `qwen3_backend.py`, `eval_gguf.py`, dataset scriptleri içinde zaten karşılığı var mı, yoksa sıfırdan mı yazılacak)
   - Hangi dosya(lar) etkileniyor
   - Kısa teknik yaklaşım önerisi (1-3 satır)
   - Bağımlılığı var mı (örn. ROS'tan gelecek bir sinyale ihtiyaç duyuyor mu — varsa bunu net şekilde işaretle, "ROS tarafından X sinyali beklenir" diye not et ama implementasyonu ROS tarafına bırak)

5. Çıktıyı şu formatta ver:

```
## FAZ 1 — Ses/AI Tarafı Görevleri

### [YENİ EKLENECEK] <görev adı>
- Kaynak: toplanti.md, madde X
- Dosya: ...
- Yaklaşım: ...
- Bağımlılık: (varsa)

### [MEVCUDU DEĞİŞTİR] <görev adı>
- Kaynak: ...
- Dosya: ...
- Mevcut davranış: ...
- Hedeflenen değişiklik: ...

## FAZ 2 — Ses/AI Tarafı Görevleri (aynı format)
```

6. Son olarak, bu listeyi `PROJE_DURUMU.md`'nin "Sıradaki Görevler" bölümüne eklemek için bir **diff/taslak** hazırla ama **dosyayı benden onay almadan değiştirme** — önce taslağı göster.

## Özellikle Değerlendirmeni İstediğim Noktalar

- **Yanıt hızı segmentasyonu:** Basit/rutin sorular ("ne alırsınız", onay istekleri) ile düşünce gerektiren sorular (öneri, alerji+öneri kombinasyonu) için farklı davranış isteniyor. Mevcut `llama_cpp_backend.py`/`qwen3_backend.py`'de intent bazlı bir hızlı yol (fast-path) var mı, yoksa her şey aynı LLM çağrısından mı geçiyor? Yoksa bunu nasıl ekleriz (örn. basit intent'leri regex/küçük sınıflandırıcıyla yakalayıp template cevap, kalanını LLM'e bırakma)?
- **Açılış cümlesi standardizasyonu:** "Hoş geldiniz" hem wake-word tetiklendiğinde hem (ileride) ROS'tan "konuşma noktasına geldim" sinyali geldiğinde kullanılacak. Şu an `demo_usb.py`'de açılış cümlesi sabit mi, sistem promptundan mı geliyor?
- **AI tarafının ROS sinyallerini dinlemesi:** "geldim" ve "hareket ediyor/durdu" sinyalleri için AI tarafında bir dinleyici/handler taslağı (sinyal formatı henüz yok, ama AI tarafındaki arayüz noktasını şimdiden tasarlayabiliriz — örn. basit bir dosya/socket/flag mekanizması, mevcut mimariyle uyumlu olan en az karmaşık seçenek).
- **Kötü niyetli/anlamsız girdi davranışı:** Mevcut 32-senaryo eval'inde bu kategori var mı? Yoksa `eval_gguf.py`'ye yeni senaryo kategorisi ve `audit_dataset.py` ile uyumlu örnek üretim planı öner.
- **Sipariş-ekran senkronizasyonu:** LLM/OrderTracker çıktısının ekran tarafına (kategori, seçili ürünler) yapılandırılmış veri olarak gitmesi gerekiyor — şu an OrderTracker'ın çıktısı bu ihtiyacı karşılıyor mu, yoksa ek bir alan/event mi gerekiyor?
- **Çoklu dil:** toplanti.md'deki 3 alternatif (model switch / bekletme mesajı / çeviri-yönlendirme) için METODOLOJI.md'ye "değerlendirilen ama karar verilmemiş" notu olarak ekle, Faz 2'ye işaretle, şimdilik kod değişikliği önerme.
- **Sürekli öğrenme/log toplama:** Faz 2+ / internet bağlı senaryo notu olarak işaretle, şimdilik somut görev üretme — sadece METODOLOJI.md'de "gelecek vizyon" notu olarak kaydet.

## Yapma

- ROS2/mekanik/donanım görevi üretme.
- toplanti.md'de olmayan, kendi tahminin olan görev ekleme — her görev toplanti.md'deki bir maddeye bağlanmalı.
- PROJE_DURUMU.md veya METODOLOJI.md'yi onay almadan değiştirme.
