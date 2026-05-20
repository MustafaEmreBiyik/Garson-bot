# Garson-bot (Robot Waiter AI) - Proje Güncel Durum Raporu

**Tarih:** 20 Mayıs 2026
**Mevcut Aşama:** Sesli Arayüz Entegrasyonu & Yerel LLM (Qwen2.5-3B-LoRA) Hata Ayıklama

## 1. Genel Durum Özeti
Proje genel mimarisi başarıyla ayağa kaldırılmış ve web tabanlı sesli asistan (Voice Web Demo) yerel bir LLM modeli üzerinden çalışır duruma getirilmiştir. Ancak kullanılan modelin belleğe sığmaması ve LoRA ağırlıklarının aşırı öğrenme (overfitting) yapmasından dolayı yanıt kalitesinde bozulmalar yaşanmaktadır.

## 2. Tamamlanan Geliştirmeler ve Çözülen Sorunlar
*   **Çapraz Platform (Cross-Platform) Uyumluluğu:** Test klasörlerindeki `\` ve `/` yol uyuşmazlığı problemleri `pathlib` kütüphanesi kullanılarak çözüldü, tüm testler geçerli hale getirildi.
*   **Web Sunucu Bağlantısı:** Ses demosunun WSL/Linux ortamından dışarıya açılabilmesi için `localhost` kısıtlaması aşıldı ve sunucu `0.0.0.0` portuna bind edildi.
*   **OOM (Killed 137) Hatası Aşımı:** Modelin VRAM/RAM limitlerini aştığında çökmesi engellendi. `--load_in_4bit` özelliği test edildi, modelin sistemde çalışabilirliği sağlandı.
*   **Aşırı Reddetme (Over-refusal) Engellemesi:** Modelin her şeye "Güvenlik garantisi veremem" veya "Menüye bakmanız lazım" tarzındaki reddetme diyaloğunu aşmak için `qwen_lora_waiter.py` içindeki `SYSTEM_PROMPT` ve `CONTEXT_GUARDRAIL` yapısı daha toleranslı ve menüye güvenen bir yapıya revize edildi.
*   **UI Güncellemesi:** Web arayüzünde "not integrated" yazan durum kısmı "Qwen2.5-3B-LoRA" olarak güncellendi.

## 3. Tespit Edilen Mevcut Sorunlar
*   **LoRA Aşırı Öğrenmesi (Overfitting):** Model, menü okuma ve yönlendirme konularından çok "Müşteriyi kasaya ve menüye yönlendirme" kuralını aşırı derecede ezberlemiştir. Mevcut 3B modeli menü `yaml` dosyasını çekmesine rağmen eski ezberlerine takılarak halüsinatif savunma mekanizmaları göstermektedir.
*   **4-Bit Kuantizasyon Kalite Kaybı:** Model sistem belleğine sığması için 4-bit küçültüldüğünde kelime kaybı yaşamakta ve Çince karakterler (örn: *Yayık Ayran 45.00 TL的价格*) gibi halüsinasyonlar üretebilmektedir. 4-bit kapatıldığında ise bellek darboğazı (OOM) nedeniyle sistem öldürülmektedir.
*   **Test (.md) ve Canlı Sistem Farkı:** Raporlanan 50 soruluk *Mock (Simüle Edilmiş)* test başarıları, şu anki mevcut LoRA ağırlıkları ile tam uyuşmamaktadır; mevcut LoRA daha düşük kaliteli çıktılar vermektedir.

## 4. Sonraki Adımlar (Gelecek Planlaması)
1.  **Veri Setinin Zenginleştirilmesi ve Retrain:** LoRA modelinin `qwen25_waiter_v1_1_taskmaster_targeted_train_400.jsonl` gibi veri setlerine daha fazla *menüden fiyat ve özellik okuma* senaryoları eklenerek baştan eğitilmesi şarttır. Reddetme eğilimi kırılmalıdır.
2.  **Sistem Kaynaklarının Yükseltilmesi:** Modelin `load_in_4bit=False` parametresi ile eksiksiz kalitede (FP16 veya BF16) çalışması için GPU/RAM kapasitesinin artırılması veya tam donanımlı bir ortam kullanılması.
3.  **Deterministik Fallback:** İdeal model kalitesi sağlanana kadar ses demosunda `--backend deterministic` kullanılarak kural tabanlı motorun devreye alınması değerlendirilebilir.

---
*Hazırlayan: AI Proje Asistanı*