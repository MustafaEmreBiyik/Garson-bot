#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v3 — Karşılama-4kategori eğitim verisi üreticisi
Hedef: 200 yeni, kural-uyumlu, çeşitli multi-turn örnek
Çalıştır: python scripts/gen_karsilama.py
"""
import json, sys, random, itertools
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

random.seed(42)
_rng = random.Random(99)

# ── System prompt (v1 datasetten alındı, değişmemeli) ──────────────────────────
SYSTEM = open(
    "robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl",
    encoding="utf-8",
).readline()
SYSTEM = json.loads(SYSTEM)["messages"][0]["content"]

# ── Kullanıcı selamlama mesajları ──────────────────────────────────────────────
# Her kategori ~50 örnek → toplam 200

U_SALT_SELAM = [
    "Merhaba.",
    "Selam.",
    "Günaydın.",
    "İyi günler.",
    "İyi akşamlar.",
    "Merhaba!",
    "Selam!",
    "Merhaba, buyurun.",
    "Selamlar.",
    "Günaydınlar.",
    "İyi günler dilerim.",
    "Merhaba efendim.",
    "Buyurun.",
    "Evet buyurun.",
    "Hoş geldiniz.",
    "Merhaba, iyimisiniz?",
    "Selam, nasılsınız?",
    "Kolay gelsin.",
    "Kolay gelsin size.",
    "İyi çalışmalar.",
    "Merhaba, efendim.",
    "Selam, efendim.",
    "Merhaba canım.",
    "Günaydın efendim.",
    "İyi akşamlar efendim.",
    "Merhaba, güzel bir yer burası.",
    "Selam, hoş bir mekan.",
    "Merhaba, yeni geldik.",
    "İyi günler, arkadaşımla geldim.",
    "Merhaba, bugün burayı denemeye karar verdik.",
    "Selam, ilk kez geliyoruz buraya.",
    "Günaydın, kahvaltı da var mı?",
    "Merhaba, buraya ilk defa geliyoruz.",
    "İyi akşamlar, rezervasyonumuz vardı.",
    "Merhaba, masaya yeni oturduk.",
    "Selam, içeriden bir masa boş mu?",
    "İyi günler, az önce oturduk.",
    "Merhaba, iki kişilik geldik.",
    "Selam, masa ayarlayabilir misiniz?",
    "Günaydın, yakın bir arkadaşımla geldim.",
    "Merhaba, ne zamandır açıksınız?",
    "İyi akşamlar, bugün çok yorgunduk.",
    "Selam, biraz soluklanmak istedik.",
    "Merhaba, çevre sakinleri tarafından çok beğeniliyorsunuz.",
    "İyi günler, yemek zamanı oldu sanırım.",
    "Merhaba, tam zamanında geldik.",
    "Selam, karnımız açtı.",
    "İyi akşamlar, güzel koku geliyor.",
    "Günaydın, öğle yemeği için geldik.",
    "Merhaba, yemek yemek istiyoruz.",
]

U_SELAM_NIYET = [
    "Merhaba, sipariş verebilir miyiz?",
    "Selam, sipariş alır mısınız?",
    "İyi günler, sipariş vermek istiyoruz.",
    "Merhaba, yemek siparişi alır mısınız?",
    "Selam, masaya bakabilir misiniz?",
    "Günaydın, hazırız sipariş için.",
    "İyi akşamlar, sipariş vermek istiyorum.",
    "Merhaba, hazır olduğumuzda sipariş verebilir miyiz?",
    "Selam, yemek seçmeye karar verdik.",
    "İyi günler, ne ısmarlamak istediğimize karar verebilmek için biraz yardım lazım.",
    "Merhaba, yiyecek bir şeyler seçmek istiyoruz.",
    "Selam, acıktık sipariş vermek istiyoruz.",
    "Günaydın, masaya yeni oturduk ne yapabiliriz?",
    "İyi akşamlar, ilk kez geldik biraz bilgi alabilir miyiz?",
    "Merhaba, buraya arkadaşım tavsiye etti, ne var ne yok öğrenmek istiyorum.",
    "Selam, yemek zamanı ne yapabiliriz?",
    "İyi günler, müsait misiniz birkaç dakika?",
    "Merhaba, karnımız epey açtı, ne yapabiliriz?",
    "Selam, uzun bir yoldan geldik ne yerdiniriz diyoruz.",
    "Günaydın, biraz yiyecek bir şeyler alabilir miyiz?",
    "İyi akşamlar, çocuğumla geldim, seçenekleri öğrenmek istiyorum.",
    "Merhaba, birkaç kişi geldik, hepsinin sipariş vermesi gerekecek.",
    "Selam, daha önce buraya gelmiştim, yeniden deneyeceğim.",
    "İyi günler, ofisimizden çıktım, burada öğle yemeği yiyebilir miyim?",
    "Merhaba, sizi ilk kez deniyorum, ne önerirsiniz genel olarak?",
    "Selam, çok acıktım bir an önce sipariş vermek istiyorum.",
    "Günaydın, kahvaltı gibi bir şeyler var mı yoksa tam yemek mi var?",
    "İyi akşamlar, burası güzel görünüyor, ne var?",
    "Merhaba, yeni açıldınız mı? Sizi ilk kez görüyorum.",
    "Selam, ailecek geldik, ne yapabiliriz?",
    "İyi günler, bugün özel bir gün ne yiyebiliriz?",
    "Merhaba, gezmek yordu bizi biraz oturmak ve yemek yemek istiyoruz.",
    "Selam, merak ettiğimiz bir yer olarak geldik, ne var ne yok?",
    "Günaydın, sabah kahvaltısı için mi yoksa yemek için mi burdayız, seçenekler neler?",
    "İyi akşamlar, bizim için iyi bir yer miydi? Merak ediyoruz ne var?",
    "Merhaba, çalışma aralarında geldim, ne yiyebilirim?",
    "Selam, masaya oturdum, ne var?",
    "İyi günler, geleli biraz oldu, sipariş almaz mısınız?",
    "Merhaba, sabahtan beri gezdik çok yorulduk, ne yedirebilirsiniz?",
    "Selam, müşteriniz olalım, ne yapabiliriz?",
    "Günaydın, sabah erken geldik, hizmetiniz hazır mı?",
    "İyi akşamlar, yorgun düştük, hızlı bir şeyler ister misiniz?",
    "Merhaba, hem yemek hem de içecek istiyoruz, seçenekler neler?",
    "Selam, garson beğendik sizi, ne var?",
    "İyi günler, buraya ilk kez geliyoruz, bize yardım eder misiniz?",
    "Merhaba, hizmetinize başlamaya hazır mısınız?",
    "Selam, çok güzel bir yer burası, ne yiyebiliriz?",
    "Günaydın, erken açılıyorsunuz, iyi ki geldik. Ne var?",
    "İyi akşamlar, bu saatte hâlâ açıksınız, iyi ki. Ne alabiliriyiz?",
    "Merhaba, yorgun ve aç geldim, ne var?",
]

U_MENU_SORUSU = [
    "Bugün ne var?",
    "Bu akşam neler var?",
    "Bu öğle neler var?",
    "Bugün menüde ne var?",
    "Neler var sizde?",
    "Neler sunuyorsunuz?",
    "Menünüzde neler var?",
    "Menünüzü öğrenebilir miyim?",
    "Menünüzü söyler misiniz?",
    "Menüye bir göz atabilir miyim?",
    "Menü var mı burada?",
    "Hangi yemekler var?",
    "Yemek seçenekleri neler?",
    "Ne yiyebilirim burada?",
    "Ne alabilirim sizden?",
    "Ne yedireceğinizi söyler misiniz?",
    "Neler yediriyorsunuz?",
    "Ne sunuyorsunuz?",
    "Sunduğunuz yemekler neler?",
    "Hangi seçenekler var?",
    "Menü seçeneklerini öğrenebilir miyim?",
    "Listede neler var?",
    "Yemek listenize bakabilir miyim?",
    "Ne çıkarsınız?",
    "Ne hazırlanıyor?",
    "Bugün ne pişiyor?",
    "Nasıl bir menünüz var?",
    "Menünüz geniş mi?",
    "Neler yapıyorsunuz?",
    "Kısaca menünüzü anlatır mısınız?",
    "Yemek kategorileriniz neler?",
    "Hangi kategoriler var?",
    "Genel olarak ne sunuyorsunuz?",
    "Yiyecekleriniz neler?",
    "Seçenekleriniz neler?",
    "Ne çeşit yemek var?",
    "Menü hakkında bilgi alabilir miyim?",
    "Genel menünüz ne durumda?",
    "Tam menü nedir?",
    "Kısa kısaca ne var?",
    "Menünüzdeki kategoriler?",
    "Ne sunabilirsiniz bize?",
    "Genel olarak ne yapıyorsunuz?",
    "Sizin uzmanlık ne?",
    "Tam menünüz neler?",
    "İçecek dahil ne var?",
    "Yemeklerinizi anlatır mısınız?",
    "Günlük menünüz nedir?",
    "Bugünkü menü ne?",
    "Sizden ne alabiliriz?",
]

U_SELAM_MENU = [
    "Merhaba, bugün ne var?",
    "Selam, ne var yemek olarak?",
    "İyi günler, menüde ne var?",
    "Merhaba, menünüzü söyler misiniz?",
    "Selam, neler sunuyorsunuz?",
    "Günaydın, bugün ne pişiyor?",
    "İyi akşamlar, menüye bakabilir miyim?",
    "Merhaba, ne yiyebiliriz?",
    "Selam, bu akşam ne var?",
    "İyi günler, ne çıkarsınız?",
    "Merhaba, hangi yemekler var?",
    "Selam, ne yedireceğinizi öğrenebilir miyim?",
    "Günaydın, kısaca menüden bahseder misiniz?",
    "İyi akşamlar, burada ne sunuyorsunuz?",
    "Merhaba, yemek seçenekleri neler?",
    "Selam, menüye bir bakayım ne var?",
    "İyi günler, menü seçeneklerini söyler misiniz?",
    "Merhaba, ne alabilirim sizden?",
    "Selam, menünüzü anlatır mısınız kısaca?",
    "Günaydın, neler var bu sabah?",
    "İyi akşamlar, ne gibi yemekler var?",
    "Merhaba, ne çeşit yemek sunuyorsunuz?",
    "Selam, genel menünüz ne?",
    "İyi günler, menünüzde neler var?",
    "Merhaba, hangi kategoriler var sizde?",
    "Selam, ne sunabilirsiniz?",
    "Günaydın, menünüz var mı?",
    "İyi akşamlar, sizin menü neler içeriyor?",
    "Merhaba, ne yiyebiliriyiz burada?",
    "Selam, ne alabiliriz?",
    "İyi günler, bugün neler yapılıyor?",
    "Merhaba, yemek listenizi öğrenebilir miyim?",
    "Selam, ne hazırlıyorsunuz?",
    "Günaydın, menü seçeneği var mı?",
    "İyi akşamlar, menünüzü anlatabilir misiniz?",
    "Merhaba, kısaca ne var ne yok?",
    "Selam, ne çıkarsınız bu akşam?",
    "İyi günler, ne yerdiniriz?",
    "Merhaba, ne sunarsınız?",
    "Selam, seçeneklerinizi öğrenebilir miyim?",
    "Günaydın, sabah menüsü var mı?",
    "İyi akşamlar, ne var burada?",
    "Merhaba, yiyecek içecek olarak ne var?",
    "Selam, tatlı dahil ne sunuyorsunuz?",
    "İyi günler, ne yedireceğiniz konusunda fikir verir misiniz?",
    "Merhaba, mutfağınız ne yapıyor?",
    "Selam, tam menünüz neler?",
    "Günaydın, menüdeki seçenekler neler?",
    "İyi akşamlar, bugün ne var acaba?",
    "Merhaba, şöyle bir göz atalım, ne var?",
]

# Tüm kullanıcı mesajlarını birleştir (200 = 50+50+50+50)
ALL_USER = U_SALT_SELAM + U_SELAM_NIYET + U_MENU_SORUSU + U_SELAM_MENU
random.shuffle(ALL_USER)
ALL_USER = ALL_USER[:200]

# ── Bot karşılama yanıtları — 4 kategori zorunlu, ≤15 kelime ─────────────────
BOT_GREET = [
    "Hoş geldiniz, çorba, ana yemek, tatlı ve içeceklerimizden ne arzu edersiniz?",
    "Merhaba, çorba, ana yemek, tatlı ve içecek seçeneklerinden ne istersiniz?",
    "Buyurun, çorba, ana yemek, tatlı ve içecek arasından ne alırsınız?",
    "Hoş geldiniz, çorba, ana yemek, tatlı ve içecek sunuyoruz, ne tercih edersiniz?",
    "Çorba, ana yemek, tatlı ve içeceklerimizden ne seçersiniz?",
    "Menümüzde çorba, ana yemek, tatlı ve içecek var, ne alırsınız?",
    "Size çorba, ana yemek, tatlı ve içecek sunabilirim, ne istersiniz?",
    "Çorba, ana yemek, tatlı ve içeceklerimizden dilediğinizi seçebilirsiniz.",
    "Tabii, çorba, ana yemek, tatlı ve içecek seçeneklerimize bakabilirsiniz.",
    "Buyurun, çorba, ana yemek, tatlı ve içecek var, ne arzu edersiniz?",
    "Çorba, ana yemek, tatlı ve içecek sunuyoruz, ne alayım?",
    "Hoş geldiniz! Çorba, ana yemek, tatlı ve içecek var, ne istersiniz?",
    "Memnuniyetle, çorba, ana yemek, tatlı ve içecek seçeneklerimiz mevcut.",
    "Hemen yardımcı olayım: çorba, ana yemek, tatlı ve içecek sunuyoruz, ne tercih edersiniz?",
    "Elbette, çorba, ana yemek, tatlı ve içeceklerimizden ne arzu edersiniz?",
    "Çorba, ana yemek, tatlı ve içecek kategorilerimizden ne seçmek istersiniz?",
    "Güzel geldiniz, çorba, ana yemek, tatlı ve içecek var, ne alırsınız?",
    "Hoş geldiniz, çorba, ana yemek, tatlı ve içeceklerimiz hazır, ne istersiniz?",
    "Buyurun efendim, çorba, ana yemek, tatlı ve içecekten ne alayım?",
    "Çorba, ana yemek, tatlı ve içecek sunuyoruz, hangisini tercih edersiniz?",
]

# ── Sipariş devamı kombinasyonları ────────────────────────────────────────────
# Basit tek-ürün siparişi + kapanış (audit kurallarını karşılıyor)
ORDER_FLOWS = [
    {
        "order": "Bir mercimek çorbası alayım.",
        "confirm": "Elbette, Mercimek Çorbası 85 TL. Başka bir şey alır mısınız?",
        "close_user": "Yok teşekkürler.",
        "close_bot": "Peki, afiyet olsun!",
    },
    {
        "order": "Kremalı mantar çorbası istiyorum.",
        "confirm": "Tabii ki, Kremalı Mantar Çorbası 95 TL. Başka ne arzu edersiniz?",
        "close_user": "Bu kadar yeterli.",
        "close_bot": "Anladım, afiyet olsun!",
    },
    {
        "order": "Izgara köfte alayım.",
        "confirm": "Tabii efendim, Izgara Köfte 240 TL. Başka bir şey ister misiniz?",
        "close_user": "Başka istemiyorum.",
        "close_bot": "Harika, afiyet olsun!",
    },
    {
        "order": "Et döner istiyorum.",
        "confirm": "Memnuniyetle, Et Döner 280 TL. Başka ne alırsınız?",
        "close_user": "Bu kadar.",
        "close_bot": "Tabii, afiyet olsun!",
    },
    {
        "order": "Izgara tavuk salata alayım.",
        "confirm": "Elbette, Izgara Tavuk Salata 210 TL. Başka bir şey alır mısınız?",
        "close_user": "Hayır teşekkürler.",
        "close_bot": "Peki, afiyet olsun!",
    },
    {
        "order": "Fırın sütlaç alayım.",
        "confirm": "Tabii ki, Fırın Sütlaç 100 TL. Başka ne arzu edersiniz?",
        "close_user": "Yeterli, teşekkürler.",
        "close_bot": "Anladım, afiyet olsun!",
    },
    {
        "order": "Künefe istiyorum.",
        "confirm": "Harika seçim! Künefe 140 TL. Başka ne alırsınız?",
        "close_user": "Başka bir şey istemiyorum.",
        "close_bot": "Tabii, afiyet olsun!",
    },
    {
        "order": "Bir ayran alayım.",
        "confirm": "Elbette, Yayık Ayran 45 TL. Başka bir şey ister misiniz?",
        "close_user": "Hayır bu kadar.",
        "close_bot": "Peki, afiyet olsun!",
    },
    {
        "order": "Limonata istiyorum.",
        "confirm": "Tabii efendim, Limonata 70 TL. Başka ne arzu edersiniz?",
        "close_user": "Yok, teşekkür ederim.",
        "close_bot": "Anladım, afiyet olsun!",
    },
    {
        "order": "Şalgam suyu alayım.",
        "confirm": "Memnuniyetle, Şalgam Suyu 50 TL. Başka bir şey alır mısınız?",
        "close_user": "Bu kadar yeterli, teşekkürler.",
        "close_bot": "Tabii, afiyet olsun!",
    },
    {
        "order": "Izgara köfte ve bir ayran alayım.",
        "confirm": "Elbette, Izgara Köfte 240 TL. Yayık Ayran 45 TL. Başka ne alırsınız?",
        "close_user": "Bu kadar.",
        "close_bot": "Peki, afiyet olsun!",
    },
    {
        "order": "Mercimek çorbası ve et döner istiyorum.",
        "confirm": "Tabii ki, Mercimek Çorbası 85 TL. Et Döner 280 TL. Başka bir şey ister misiniz?",
        "close_user": "Hayır bu kadar.",
        "close_bot": "Anladım, afiyet olsun!",
    },
    {
        "order": "Künefe ve limonata alayım.",
        "confirm": "Harika seçim! Künefe 140 TL. Limonata 70 TL. Başka ne arzu edersiniz?",
        "close_user": "Yok teşekkürler.",
        "close_bot": "Tabii, afiyet olsun!",
    },
    {
        "order": "Izgara tavuk salata ve şalgam suyu alayım.",
        "confirm": "Elbette, Izgara Tavuk Salata 210 TL. Şalgam Suyu 50 TL. Başka bir şey alır mısınız?",
        "close_user": "Bu kadar.",
        "close_bot": "Peki, afiyet olsun!",
    },
    {
        "order": "Fırın sütlaç ve bir ayran istiyorum.",
        "confirm": "Tabii efendim, Fırın Sütlaç 100 TL. Yayık Ayran 45 TL. Başka ne alırsınız?",
        "close_user": "Yeterli teşekkürler.",
        "close_bot": "Anladım, afiyet olsun!",
    },
    {
        "order": "Kremalı mantar çorbası ve künefe alayım.",
        "confirm": "Memnuniyetle, Kremalı Mantar Çorbası 95 TL. Künefe 140 TL. Başka bir şey ister misiniz?",
        "close_user": "Hayır teşekkürler.",
        "close_bot": "Tabii, afiyet olsun!",
    },
    {
        "order": "Et döner ve limonata istiyorum.",
        "confirm": "Tabii ki, Et Döner 280 TL. Limonata 70 TL. Başka ne arzu edersiniz?",
        "close_user": "Bu kadar yeter.",
        "close_bot": "Peki, afiyet olsun!",
    },
    {
        "order": "Mercimek çorbası, ızgara köfte ve ayran alayım.",
        "confirm": "Elbette, Mercimek Çorbası 85 TL. Izgara Köfte 240 TL. Yayık Ayran 45 TL. Başka bir şey alır mısınız?",
        "close_user": "Hayır yeter.",
        "close_bot": "Anladım, afiyet olsun!",
    },
    {
        "order": "Bir mercimek çorbası alayım, sonra bakarız.",
        "confirm": "Tabii efendim, Mercimek Çorbası 85 TL. Başka ne alırsınız?",
        "close_user": "Şimdilik bu kadar.",
        "close_bot": "Harika, afiyet olsun!",
    },
    {
        "order": "Izgara tavuk salata ve fırın sütlaç alayım.",
        "confirm": "Memnuniyetle, Izgara Tavuk Salata 210 TL. Fırın Sütlaç 100 TL. Başka ne arzu edersiniz?",
        "close_user": "Yok bu kadar.",
        "close_bot": "Tabii, afiyet olsun!",
    },
]

# ── JSONL üretimi ──────────────────────────────────────────────────────────────
records = []
order_flow_indices = list(range(len(ORDER_FLOWS))) * (200 // len(ORDER_FLOWS) + 1)
_rng.shuffle(order_flow_indices)

for i, user_msg in enumerate(ALL_USER):
    bot_greet  = BOT_GREET[i % len(BOT_GREET)]
    order_flow = ORDER_FLOWS[order_flow_indices[i]]

    messages = [
        {"role": "system",    "content": SYSTEM},
        {"role": "user",      "content": user_msg},
        {"role": "assistant", "content": bot_greet},
        {"role": "user",      "content": order_flow["order"]},
        {"role": "assistant", "content": order_flow["confirm"]},
        {"role": "user",      "content": order_flow["close_user"]},
        {"role": "assistant", "content": order_flow["close_bot"]},
    ]
    records.append({"messages": messages})

# ── Audit doğrulaması ──────────────────────────────────────────────────────────
cats = ["çorba", "ana yemek", "tatlı", "içecek"]
pass_count = 0
fail_items = []

for rec in records:
    msgs = rec["messages"]
    # Turn 1 (index 2): bot karşılama
    bot_first = msgs[2]["content"].lower().replace("i̇", "i").replace("İ", "i")
    missing = [c for c in cats if c not in bot_first]
    if not missing:
        pass_count += 1
    else:
        fail_items.append({"user": msgs[1]["content"], "bot": msgs[2]["content"], "missing": missing})

    # Başka kontrolü: sipariş onayında "başka" geçmeli
    order_confirm = msgs[4]["content"].lower()
    if "başka" not in order_confirm:
        fail_items.append({"note": "başka eksik", "confirm": msgs[4]["content"]})

print(f"Toplam: {len(records)} kayıt")
print(f"Karşılama geçer: {pass_count}")
print(f"Başarısız: {len(fail_items)}")

if fail_items:
    print("\nHatalı örnekler:")
    for f in fail_items[:5]:
        print(f)
else:
    print("✓ Tüm örnekler geçti.")

# ── Çıktı ──────────────────────────────────────────────────────────────────────
out_path = Path("robot_waiter_ai/datasets/processed/wbot_v3_karsilama.jsonl")
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"\n✓ {len(records)} kayıt → {out_path}")
