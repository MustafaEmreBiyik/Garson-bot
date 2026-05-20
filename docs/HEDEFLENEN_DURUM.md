# Garson-bot (Robot Waiter AI) - Proje Hedefleri ve İstenen Nokta

**Tarih:** 20 Mayıs 2026

Bu doküman, projede halihazırda tespit edilen sorunların çözülmesinin ardından varılması hedeflenen ideal sistem durumunu, fonksiyonel sınırları ve model performans kriterlerini tanımlar.

## 1. Kusursuz LLM (Qwen) Entegrasyonu
Mevcut durumda modelin bellek (OOM) ve aşırı reddetme (over-refusal) sebepleriyle tam kapasite çalışamadığı tespit edilmiştir. İstenen noktada LLM entegrasyonu tamamen kusursuz olmalıdır.
*   **Tam Hassasiyet veya Kaliteli Kuantizasyon:** Sistemin, RAM sınırlarına takılmadan ve `4-bit` kalite kaybına (Çince karakter halüsinasyonları veya mantıksız kelimeler üretmeye) maruz kalmadan stabil çalışması.
*   **Özgüvenli Yanıtlar ve Menü Okur-Yazarlığı:** Canlı testlerde, sistemin (örneğin *"Ayran ne kadar?"* veya *"Mercimek Çorbası içinde ne var?"*) sorularına, 50 soruluk offline test raprounda olduğu gibi doğrudan, "Yönlendirmeye girmeden" menüden bilgi okuyarak net fiyat ve detay sunabilmesi.
*   **Dengeli Güvenlik Rejimi:** Modelin, gerçekten "Paket Servis" gibi menüde olmayan detayları sorulduğunda dahi kibarca "Menümüzde detay yok" (örnek rapordaki gibi) diyerek doğal cevaplar vermesi, "Ben güvenlik garantisi veremem" gibi abartılı savunmalara girmemesi.

## 2. Stabil ve Akıcı Sesli Diyalog (Voice Web Demo)
*   **Web Speech API İle Eşzamanlılık:** Kullanıcı konuşurken mikrofon verisinin hızla yakalanıp modele iletilmesi ve modelden çıkan yanıtın kesintisiz, akıcı bir Türkçe sentezle (TTS) kullanıcıya iletilmesi.
*   **Asenkron Arka Plan Çalışması:** İşletim sisteminin modeli bir yük olarak görüp *Killed (Exit Code 137)* hatası vermemesi için arka planda uygun asenkron yönetimlerin (batching, streaming generation) yapılması. Sunucunun manuel müdahaleye gerek kalmadan günlerce kapanmadan dinlemede kalabilmesi.

## 3. Doğru İşleyen Veri (Knowledge Grounding) Hattı
*   **Dinamik Menü Algısı:** `menu.yaml` ve `restaurant_info.yaml` dosyalarında fiyat, ürün veya çalışma saati değiştirildiğinde, asistanın modeli yeniden eğitmeye gerek kalmadan bu değişiklikleri (build_menu_context) alıp anında son kullanıcıya yansıtması.
*   **Sınıflandırma ve Doğrulama (Intent Detection):** Kullanıcı doğrudan bir sipariş verdiğinde (örn: *"Bana bir döner, bir ayran yaz"*), sistemin sadece diyaloğu sürdürmekle kalmayıp bunu yapısal bir metne ve toplama (örneğin "*Toplam 325 TL, onaylıyor musunuz?*") çevirebilmesi.

## 4. Eğitim ve İnce Ayar (Fine-Tuning/LoRA) Hedefi
*   **Sağlıklı Veri Seti (Overfitting Olmayan):** Model ağırlıklarının (`qwen25_3b_waiter_v1_1_lora`), reddetme refleksleri dışında "Müşteri Hizmetleri" karakterine doğal şekilde eğitilmiş olması. Menü bilgisinden veri çeken veri kümelerinin (Dataset) zenginleştirilmesi ile uydurma ve halüsinasyon eğilimlerinin sıfırlanması.

## 5. Deployment (Dağıtım) ve Ürünleşme Durumu
*   **Geliştirici Ortamından Çıkış:** Projenin terminal üzerinde local scriptlerle `localhost` bazlı test edilmesinden çıkıp, Docker konteyneri (veya güvenilir bir backend servisi) içinde tam üretim modeli (Production-Ready) halini alması.
*   **Bütünleşik Müşteri Deneyimi:** Sonuç olarak restoran girişine veya masaya konulacak bir tablette, hiçbir ek kodlama müdahalesine gerek duymayan, kendi kendine dinleyen, menüden sipariş öneren ve sorulara eksiksiz, net yanıtlar veren stabil bir dijital garson prototipi ortaya çıkarılması.