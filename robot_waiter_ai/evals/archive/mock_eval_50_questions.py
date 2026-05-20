import json
import time
from pathlib import Path
from robot_waiter_ai.inference.qwen_lora_waiter import QwenLoraWaiterBackend
from robot_waiter_ai.demo.voice_web_demo import build_menu_context

questions = [
    # Çorbalar
    "Menüde hangi çorbalar var?",
    "Mercimek çorbasının fiyatı ne kadar?",
    "Kremalı mantar çorbasının içinde neler var?",
    "Gluten alerjim var, mercimek çorbası içebilir miyim?",
    "Süt alerjim var, kremalı mantar çorbası bana uygun mu?",
    
    # Ana Yemekler
    "Ana yemek olarak neler tavsiye edersiniz?",
    "Izgara köfte ne kadar?",
    "Izgara köftenin yanında ne servis ediliyor?",
    "Et döner porsiyon fiyatı nedir?",
    "Et dönerin içinde neler var?",
    "Diyetteyim, hafif bir şeyler önerir misiniz?",
    "Izgara tavuk salatasının içinde glüten var mı?",
    "Tavuklu yemekleriniz nelerdir?",
    "Menünüzde kırmızı et seçenekleri var mı?",
    "Vejetaryen ana yemeğiniz var mı?", # Yok (sadece tavuk, et, köfte)
    
    # Tatlılar
    "Tatlı olarak neyiniz var?",
    "Fırın sütlaç fiyatı ne kadar?",
    "Sütlaç günlük mü?",
    "Künefe fiyatı nedir?",
    "Künefede ceviz veya fıstık var mı alerjim var da?",
    "Künefe sıcak mı servis ediliyor?",
    "Tatlılarda vegan bir seçeneğiniz bulunuyor mu?",
    
    # İçecekler
    "İçecek olarak soğuk ne alabilirim?",
    "Yayık ayran ne kadar?",
    "Ayranınız nasıl, köpüklü mü?",
    "Limonata taze sıkım mı?",
    "Limonatanız naneli mi oluyor?",
    "Şalgam suyunuz acılı mı acısız mı?",
    "Şalgam suyu ne kadar?",
    "Sıcak içecekleriniz var mı çay kahve gibi?", # Yok
    
    # Menü Dışı Sorular
    "Hamburger yapıyor musunuz?",
    "Pizzanız var mı?",
    "Çocuk menünüz bulunuyor mu?",
    "Makarna çeşidiniz var mıdır?",
    "Salata seçeneklerinizde ton balıklı var mı?",
    "Patates kızartması porsiyon olarak var mı?",
    "Tatlı olarak tiramisu yapabilir misiniz?",
    "Bira veya şarap servisiniz var mı?",
    "Paket servisiniz mevcut mu?",
    "Kredi kartı geçiyor mu?",
    
    # Kombinasyon / Fiyat
    "Bana bir mercimek çorbası, bir de döner verir misin?",
    "İki kişi geldik, 2 ızgara köfte ve 2 ayran ne kadar tutar?",
    "Öğrenci indiriminiz var mı?",
    "Menüdeki en ucuz ana yemek hangisi?",
    "Menüdeki en pahalı yemek nedir?",
    "Toplam 100 liram var, doyurucu ne yiyebilirim?",
    
    # Detaylar
    "Yemekleriniz helal kesim mi?",
    "Izgara köfte acılı mı?",
    "Şalgam suyu Adana'dan mı geliyor?",
    "Haftanın her günü açık mısınız?"
]

def run_eval():
    try:
        backend = QwenLoraWaiterBackend(
            base_model_path="robot_waiter_ai/models/Qwen2.5-3B-Instruct",
            adapter_path="robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora",
            load_in_4bit=False
        )
    except Exception as e:
        print(f"Model yüklenirken hata: {e}")
        return

    menu_context = build_menu_context()
    print("Menü bağlamı:")
    print(menu_context)
    
    results = []
    success_count = 0
    total = len(questions)
    
    print("\nTest başlıyor...")
    start_time = time.time()
    for i, q in enumerate(questions, 1):
        print(f"[{i}/{total}] Soru: {q}")
        reply = backend.generate_reply(q, menu_context)
        print(f"Cevap: {reply}\n")
        
        # Basit bir heuristik ile başarı hesaplaması (model cevap veriyorsa başarılı kabul edeceğiz)
        # Daha doğru değerlendirme insan gözüyle rapordan yapılabilir.
        is_success = bool(reply.strip()) and len(reply) > 5
        if is_success:
            success_count += 1
            
        results.append({
            "id": i,
            "soru": q,
            "cevap": reply,
            "basarili": is_success
        })
        
    duration = time.time() - start_time
    
    # Raporlama
    report_path = Path("qwen_50_soru_test_sonuc.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Qwen2.5 3B Ses Modülü Test Raporu\n\n")
        f.write(f"**Toplam Soru:** {total}\n")
        f.write(f"**Başarı Oranı:** %{(success_count/total)*100:.1f}\n")
        f.write(f"**Test Süresi:** {duration:.1f} saniye\n\n")
        
        f.write("## Soru ve Cevaplar\n\n")
        for res in results:
            status = "✅" if res["basarili"] else "❌"
            f.write(f"### Soru {res['id']}: {res['soru']}\n")
            f.write(f"**Cevap:** {res['cevap']}\n")
            f.write(f"**Durum:** {status}\n\n")
            
    print(f"Test tamamlandı. Rapor {report_path} dosyasına kaydedildi.")

if __name__ == "__main__":
    run_eval()
