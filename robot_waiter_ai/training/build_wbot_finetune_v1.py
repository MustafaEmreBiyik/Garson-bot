"""Build the W-BOT fine-tuning JSONL dataset described in docs/FINE_TUNE_VERI_REHBERI.md.

The generated file intentionally contains only {"messages": [...]} records.
Assistant responses are authored from menu/rule templates in this module; source
datasets are not copied.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = ROOT / "docs" / "FINE_TUNE_VERI_REHBERI.md"
OUT_PATH = ROOT / "robot_waiter_ai" / "datasets" / "processed" / "wbot_finetune_v1.jsonl"

TARGET_COUNTS = {
    "A": 200,
    "B": 80,
    "C": 80,
    "D": 150,
    "E": 200,
    "F": 100,
    "G": 80,
    "H": 80,
}


ITEMS = [
    {
        "key": "mercimek",
        "name": "Mercimek Çorbası",
        "price": 85,
        "category": "Çorba",
        "aliases": ["mercimek çorbası", "mercimek"],
        "acc": "Mercimek Çorbasını",
    },
    {
        "key": "mantar",
        "name": "Kremalı Mantar Çorbası",
        "price": 95,
        "category": "Çorba",
        "aliases": ["kremalı mantar çorbası", "kremalı mantar"],
        "acc": "Kremalı Mantar Çorbasını",
    },
    {
        "key": "kofte",
        "name": "Izgara Köfte",
        "price": 240,
        "category": "Ana Yemek",
        "aliases": ["ızgara köfte", "köfte"],
        "acc": "Izgara Köfteyi",
    },
    {
        "key": "doner",
        "name": "Et Döner",
        "price": 280,
        "category": "Ana Yemek",
        "aliases": ["et döner", "döner"],
        "acc": "Et Döneri",
    },
    {
        "key": "tavuk_salata",
        "name": "Izgara Tavuk Salata",
        "price": 210,
        "category": "Ana Yemek",
        "aliases": ["ızgara tavuk salata", "tavuk salata"],
        "acc": "Izgara Tavuk Salatayı",
    },
    {
        "key": "sutlac",
        "name": "Fırın Sütlaç",
        "price": 100,
        "category": "Tatlı",
        "aliases": ["fırın sütlaç", "sütlaç"],
        "acc": "Fırın Sütlacı",
    },
    {
        "key": "kunefe",
        "name": "Künefe",
        "price": 140,
        "category": "Tatlı",
        "aliases": ["künefe"],
        "acc": "Künefeyi",
    },
    {
        "key": "ayran",
        "name": "Yayık Ayran",
        "price": 45,
        "category": "İçecek",
        "aliases": ["yayık ayran", "ayran"],
        "acc": "Yayık Ayranı",
    },
    {
        "key": "limonata",
        "name": "Limonata",
        "price": 70,
        "category": "İçecek",
        "aliases": ["limonata"],
        "acc": "Limonatayı",
    },
    {
        "key": "salgam",
        "name": "Şalgam Suyu",
        "price": 50,
        "category": "İçecek",
        "aliases": ["şalgam suyu", "şalgam"],
        "acc": "Şalgam Suyunu",
    },
]

ITEM_BY_KEY = {item["key"]: item for item in ITEMS}
CATEGORY_ITEMS = {
    category: [item for item in ITEMS if item["category"] == category]
    for category in ["Çorba", "Ana Yemek", "Tatlı", "İçecek"]
}

ACKS = ["Elbette", "Tabii ki", "Tabii efendim", "Memnuniyetle", "Harika seçim"]
FOLLOW_UPS = [
    "Başka bir şey alır mısınız?",
    "Başka ne arzu edersiniz?",
    "Başka bir şey ister misiniz?",
]
GREETING_RESPONSES = [
    "Hoş geldiniz, çorba, ana yemek, tatlı ve içeceklerimizden ne arzu edersiniz?",
    "Merhaba, çorba, ana yemek, tatlı ve içecek seçeneklerinden ne istersiniz?",
    "Buyurun, çorba, ana yemek, tatlı ve içecek arasından ne alırsınız?",
    "Hoş geldiniz, çorba, ana yemek, tatlı ve içecek için ne tercih edersiniz?",
]
CLOSING_RESPONSES = [
    "Anladım, afiyet olsun!",
    "Tabii, afiyet olsun!",
    "Peki, afiyet olsun!",
    "Tamamdır, afiyet olsun!",
    "Buyurun, afiyet olsun!",
]

ORDER_PREFIXES = [
    "",
    "Şimdilik ",
    "Bugün ",
    "Mümkünse ",
    "Bu sefer ",
    "Önce ",
    "Hızlıca ",
    "Lütfen ",
    "Rica ederim, ",
    "Masamız için ",
    "Benim için ",
    "Arkadaşım için ",
]
ORDER_TEMPLATES = [
    "{p}bir {a} alayım.",
    "{p}{A} istiyorum.",
    "{p}bir {a} istiyorum.",
    "{p}{A} getirir misiniz?",
    "{p}bir {a} getirir misiniz?",
    "{p}{A} alabilir miyim?",
    "{p}bir porsiyon {a} alayım.",
    "{p}bir adet {a} istiyorum.",
    "{p}{A} olsun, alayım.",
    "{p}{A} sipariş etmek istiyorum.",
    "{p}bana {a} getirir misiniz?",
    "{p}{A} alayım lütfen.",
    "{p}{A} istiyorum, rica ederim.",
    "{p}bir {a} alayım, rica ederim.",
]
EXTRA_TEMPLATES = [
    "Bir de {a} alayım.",
    "Yanına {a} istiyorum.",
    "{A} da getirir misiniz?",
    "Ek olarak {a} alayım.",
    "Bir {a} daha istiyorum.",
    "Ayrıca {a} getirir misiniz?",
    "Sonra {a} da alayım.",
    "Onunla birlikte {a} istiyorum.",
    "Masaya {a} da getirir misiniz?",
    "Bir de {a} istiyorum, rica ederim.",
]
MULTI_ORDER_TEMPLATES = [
    "Bir {a1} ve bir {a2} istiyorum.",
    "{A1} ile {a2} alayım.",
    "Masaya {a1} ve {a2} getirir misiniz?",
    "{A1}, yanında da {a2} istiyorum.",
    "Bir {a1}, bir de {a2} alayım.",
    "{A1} ve {a2} sipariş etmek istiyorum.",
    "Bana {a1} ve {a2} getirir misiniz?",
    "Şimdilik {a1} ile {a2} alayım.",
    "Mümkünse {a1} ve {a2} istiyorum.",
    "Hızlıca {a1} ve {a2} alabilir miyim?",
]

NUMBER_WORDS = {2: "iki", 3: "üç", 4: "dört", 5: "beş"}
QUANTITY_TEMPLATES = [
    "{N} tane {a} alayım.",
    "{N} adet {a} istiyorum.",
    "{N} kişilik {a} getirir misiniz?",
    "{N} {a} alabilir miyim?",
    "Masaya {N} tane {a} istiyorum.",
    "Lütfen {N} adet {a} getirir misiniz?",
]

CATEGORY_TEMPLATES = [
    "{cat} ne var?",
    "Hangi {plural} var?",
    "{cat_cap} çeşitleriniz neler?",
    "Bugün {loc} ne var?",
    "{cat_cap} olarak neler var?",
    "{cat_cap} kategorisini söyler misiniz?",
    "Sadece {cat} seçenekleri neler?",
    "{loc_cap} ne vardı?",
    "{cat_cap} tarafında neler var?",
    "{plural_cap} nelerdir?",
    "Menüde {cat} olarak ne bulunuyor?",
    "{cat_cap} kısmını anlatır mısınız?",
    "{loc_cap} hangileri var?",
    "{cat_cap} seçeneklerini öğrenebilir miyim?",
    "Şu an {cat} olarak ne çıkar?",
    "{cat_cap} menünüzde neler var?",
    "{cat_cap} için seçenekler nedir?",
    "{cat_cap} bölümünde ne var?",
    "Kısaca {cat} çeşitlerini söyler misiniz?",
    "{loc_cap} hangi seçenekler mevcut?",
]

CATEGORY_WORDS = {
    "Çorba": {
        "cat": "çorba",
        "cat_cap": "Çorba",
        "plural": "çorbalar",
        "plural_cap": "Çorbalar",
        "loc": "çorbada",
        "loc_cap": "Çorbada",
    },
    "Ana Yemek": {
        "cat": "ana yemek",
        "cat_cap": "Ana yemek",
        "plural": "ana yemekler",
        "plural_cap": "Ana yemekler",
        "loc": "ana yemekte",
        "loc_cap": "Ana yemekte",
    },
    "Tatlı": {
        "cat": "tatlı",
        "cat_cap": "Tatlı",
        "plural": "tatlılar",
        "plural_cap": "Tatlılar",
        "loc": "tatlıda",
        "loc_cap": "Tatlıda",
    },
    "İçecek": {
        "cat": "içecek",
        "cat_cap": "İçecek",
        "plural": "içecekler",
        "plural_cap": "İçecekler",
        "loc": "içecekte",
        "loc_cap": "İçecekte",
    },
}

CATEGORY_RESPONSES = {
    "Çorba": "Çorbada Mercimek ve Kremalı Mantar var. Hangisini tercih edersiniz?",
    "Ana Yemek": "Ana yemekte Izgara Köfte, Et Döner ve Izgara Tavuk Salata var. Hangisini arzu edersiniz?",
    "Tatlı": "Tatlıda Fırın Sütlaç ve Künefe var. Hangisini istersiniz?",
    "İçecek": "İçecekte Yayık Ayran, Limonata ve Şalgam Suyu var. Ne alırsınız?",
}

RECOMMENDATION_TEMPLATES = [
    "{cat} olarak ne önerirsiniz?",
    "{cat} tarafında ne tavsiye edersiniz?",
    "{cat} için ne alayım?",
    "Bugün {cat} olarak ne iyi?",
    "{cat} seçerken ne önerirsiniz?",
    "Bana {cat} önerir misiniz?",
    "{cat} konusunda kararsızım, ne dersiniz?",
    "En sevilen {cat} hangisi?",
    "{cat} için hafif ne var?",
    "{cat} öneriniz ne olur?",
    "Bu akşam {cat} olarak ne alsam?",
    "{cat} içinden hangisini seçeyim?",
]

RECOMMENDATION_RESPONSES = {
    "Çorba": [
        "Mercimek Çorbası çok sevilir, hafif ve doyurucu. Getireyim mi?",
        "Kremalı Mantar Çorbası sıcak ve yoğun bir seçenek. İster misiniz?",
    ],
    "Ana Yemek": [
        "Izgara Köfte çok tercih ediliyor. Getireyim mi?",
        "Izgara Tavuk Salata hafif bir ana yemek. İster misiniz?",
        "Et Döner doyurucu ve sevilen bir seçenek. Getireyim mi?",
    ],
    "Tatlı": [
        "Fırın Sütlaç hafif ve geleneksel bir tatlı. Getireyim mi?",
        "Künefe sıcak servis edilir, çok sevilir. İster misiniz?",
    ],
    "İçecek": [
        "Limonata ferahlatıcı, Şalgam Suyu da geleneksel. Hangisini istersiniz?",
        "Yayık Ayran serin ve geleneksel. Getireyim mi?",
    ],
}

GENERAL_RECOMMENDATION_USERS = [
    "Ne yesem?",
    "Ne önerirsiniz?",
    "Bugün ne güzel?",
    "Kararsız kaldım, ne alayım?",
    "En çok ne tercih ediliyor?",
    "Hafif ama doyurucu ne var?",
    "İlk kez geldim, ne tavsiye edersiniz?",
    "Kısa bir öneri verir misiniz?",
    "Bugün için iyi bir seçim ne olur?",
    "Menüden öne çıkan ne var?",
    "Sizin favori öneriniz ne?",
    "Tek ürün seçsem ne alayım?",
    "Doyurucu bir şey önerir misiniz?",
    "Başlangıç için ne iyi olur?",
    "Sıcak bir seçenek ne olur?",
    "Acele karar vermem lazım, ne önerirsiniz?",
    "Masadaki herkes kararsız, ne alalım?",
    "Güzel bir ikili önerir misiniz?",
    "Bugün en güvenli seçim ne?",
    "Lezzetli bir şey söyleyin lütfen.",
    "Çok ağır olmayan ne var?",
    "Öne çıkan ürününüz hangisi?",
    "Klasik bir şey yemek istiyorum, ne önerirsiniz?",
    "Ferahlatıcı bir şeyle birlikte ne iyi olur?",
    "Akşam için ne uygun?",
    "Bana hızlıca bir öneri yapar mısınız?",
    "Menüde ne iyi gidiyor?",
    "Bir ana seçenek önerir misiniz?",
    "Geleneksel bir şey ne olur?",
    "Çok sevilen bir ürün söyler misiniz?",
]
GENERAL_RECOMMENDATION_RESPONSES = [
    "Izgara Köfte bugün çok tercih ediliyor. Denemek ister misiniz?",
    "Kremalı Mantar Çorbası ile başlamak harika olur. Getireyim mi?",
    "Et Döner ve Limonata güzel bir ikili olur. Hangisini alırsınız?",
    "Künefe sıcak sevenler için güzel. İster misiniz?",
    "Izgara Tavuk Salata hafif bir seçim olur. Getireyim mi?",
]

UNAVAILABLE_USERS = [
    "Hamburger var mı?",
    "Pizza getirir misiniz?",
    "Dondurma istiyorum.",
    "Türk kahvesi alabilir miyim?",
    "Çay var mı?",
    "Elmalı turta?",
    "Naan ekmek var mı?",
    "Cheesecake?",
    "Tiramisu?",
    "Falafel getirir misiniz?",
    "Makarna?",
    "Lazanya var mı?",
    "Sushi yapıyor musunuz?",
    "Tavuk döner var mı?",
    "Börek?",
    "Gözleme?",
    "Tost?",
    "Kuru fasulye?",
    "Baklava alayım.",
    "Lahmacun çıkar mı?",
    "Pide sipariş edebilir miyim?",
    "İskender var mı?",
    "Adana kebap getirir misiniz?",
    "Tavuk şiş istiyorum.",
    "Pilavınız var mı?",
    "Cacık alabilir miyim?",
    "Yoğurt getirin.",
    "Su var mı?",
    "Maden suyu alayım.",
    "Kola getirir misiniz?",
    "Gazoz var mı?",
    "Portakal suyu istiyorum.",
    "Ice tea var mı?",
    "Espresso alabilir miyim?",
    "Kapuçino yapıyor musunuz?",
    "Salep var mı?",
    "Boza getirir misiniz?",
    "Kadayıf tatlısı var mı?",
    "Profiterol istiyorum.",
    "Revani alabilir miyim?",
    "Kazandibi var mı?",
    "Aşure çıkar mı?",
    "Bulgur pilavı var mı?",
    "Patates kızartması getirir misiniz?",
    "Soğan halkası alayım.",
    "Nugget var mı?",
    "Balık ekmek yapıyor musunuz?",
    "Somon var mı?",
    "Karides getirir misiniz?",
    "Mantı istiyorum.",
    "Kebap dürüm var mı?",
    "Ciğer şiş alayım.",
    "Kokoreç var mı?",
    "Midye dolma getirir misiniz?",
    "Menemen yapıyor musunuz?",
    "Omlet var mı?",
    "Kahvaltı tabağı alayım.",
    "Sucuklu yumurta var mı?",
    "Mercimek köftesi istiyorum.",
    "Zeytinyağlı sarma var mı?",
    "Çiğ köfte getirir misiniz?",
    "Humus var mı?",
    "Ezme alabilir miyim?",
    "Fava var mı?",
    "Kısır getirir misiniz?",
    "Karnıyarık var mı?",
    "Musakka alayım.",
    "Tas kebabı var mı?",
    "Hünkar beğendi istiyorum.",
    "Ali nazik var mı?",
    "Kuzu tandır getirir misiniz?",
    "İçli köfte var mı?",
    "Paçanga böreği alayım.",
    "Sigara böreği var mı?",
    "Sütlü kahve yapar mısınız?",
    "Bitki çayı var mı?",
    "Ayran aşı çorbası çıkar mı?",
    "Domates çorbası var mı?",
    "Ezogelin çorbası istiyorum.",
    "Sebzeli makarna var mı?",
]

STT_EXACT_USERS = [
    "galifon getir",
    "sanivli istiyorum",
    "kanalfon nedir",
    "minnuzda ne var",
    "hırvıştan alayım",
    "kalafoni var mı",
    "pırtlak çorba",
    "zarfon istiyorum",
    "belviren ne",
    "şırvışkan",
    "trambolin çorbası",
    "kanatolu döner",
]
STT_EXTRA_BASES = [
    "galafon",
    "zirvona",
    "salmira",
    "kelvani",
    "dımbrıs",
    "fırdaval",
    "nömbeli",
    "şalvira",
    "kandolin",
    "tarvuna",
    "mirlazon",
    "çorbanik",
    "lambiro",
    "zemberekli",
    "poyrazon",
    "mantarus",
]
STT_VERBS = ["getir", "var mı", "istiyorum", "nedir"]

OFFTOPIC_USERS = [
    "Hava nasıl bugün?",
    "Futbol sonuçlarını biliyor musun?",
    "Bana bir fıkra anlat.",
    "En iyi restoran hangisi?",
    "Nasıl pişirilir bu yemek?",
    "Kilo vermek istiyorum, ne yapmalıyım?",
    "Kaç yaşındasın?",
    "Şarkı önerir misin?",
    "Türkiye'nin başkenti neresi?",
    "Bu restoranın adresi nedir?",
    "İndirim var mı?",
    "Bugün hangi şef çalışıyor?",
    "Rezervasyon yapabilir miyim?",
    "Döviz kuru nedir?",
    "Saat kaç oldu?",
    "Bana şiir yazar mısın?",
    "Telefonum bozuldu, ne yapayım?",
    "Yol tarifi verir misin?",
    "Yakındaki eczane açık mı?",
    "Bugün maç var mı?",
    "Film tavsiye eder misin?",
    "Matematik ödevimi çözer misin?",
    "Bilgisayarım yavaşladı, yardım eder misin?",
    "Rüya tabiri yapar mısın?",
    "Burcum bugün ne diyor?",
    "Hangi araba daha iyi?",
    "Kredi faizi kaç oldu?",
    "Bana haberleri özetler misin?",
    "Bir oyun oynayalım mı?",
    "Ev kiraları neden arttı?",
    "Şehir dışına otobüs var mı?",
    "Uçak bileti bakar mısın?",
    "Kargo takip edebilir misin?",
    "Spor salonu önerir misin?",
    "Diyet listesi hazırlar mısın?",
    "Kan tahlilimi yorumlar mısın?",
    "Avukat tavsiye eder misin?",
    "Borsa ne olur?",
    "Kripto alınır mı?",
    "Bana masal anlatır mısın?",
    "Düğün salonu önerir misin?",
    "Bugün trafik yoğun mu?",
    "Otobüs saatlerini söyler misin?",
    "Bu masanın tasarımı güzel mi?",
    "Garsonlar kaçta çıkıyor?",
    "Mutfakta kaç kişi var?",
    "Restoran sahibi kim?",
    "Bu binanın tarihi nedir?",
    "Wifi şifresi nedir?",
    "Lavabo nerede?",
    "Müzik sesini açar mısın?",
    "Klimayı kapatır mısın?",
    "Fotoğrafımızı çeker misin?",
    "Şarj aleti bulabilir miyim?",
    "Sigara içilen alan var mı?",
    "Vale hizmeti var mı?",
    "Çocuk oyun alanı nerede?",
    "Canlı müzik ne zaman başlıyor?",
    "Paket servisi siz mi yapıyorsunuz?",
    "Çalışma saatleriniz nedir?",
]

ACCOUNT_BASES = [
    "Hesabı alabilir miyim",
    "Hesap lütfen",
    "Ödeyeyim artık",
    "Ödeme yapmak istiyorum",
    "Hesabı getirir misiniz",
    "Hesabı kapatalım",
    "Artık hesabı isteyeyim",
    "Hesap için yardımcı olur musunuz",
    "Hesabı rica ediyorum",
    "Ödeme alabilir misiniz",
]
ACCOUNT_SUFFIXES = [
    "",
    " masamız için",
    " lütfen",
    " hazırsa",
    " şimdi",
    " mümkünse",
    " çıkmadan önce",
    " bu masa için",
    " nazikçe",
    " teşekkür ederim",
]

SUBTOTAL_BASES = [
    "Şimdiye kadar ne kadar oldu",
    "Toplam kaça çıktı şu an",
    "Ara toplamı öğrenebilir miyim",
    "Şu ana kadar kaç TL tuttu",
    "Eklediklerimiz ne kadar etti",
    "Hesap şu an kaça geldi",
    "Siparişler şimdilik kaça çıktı",
    "Bu noktada tutar ne oldu",
    "Şu anki tutarı söyler misiniz",
    "Bunlar toplam ne yapıyor",
]
SUBTOTAL_SUFFIXES = [
    "",
    " acaba",
    " hızlıca",
    " şimdilik",
    " bu masada",
    " yaklaşık",
]

GREETING_BASES = [
    "Merhaba",
    "Selam",
    "İyi günler",
    "Kolay gelsin",
    "Evet merhaba",
    "Merhabalar",
    "Selamlar",
    "İyi akşamlar",
]
GREETING_TAILS = [
    "sipariş vermek istiyorum",
    "menüye bakabilir miyiz",
    "bir şeyler alacağız",
    "bize yardımcı olur musunuz",
    "ne var öğrenebilir miyim",
    "masaya bakar mısınız",
    "siparişe başlayalım",
    "bugün ne var",
    "menünüz ne",
    "hemen sipariş geçeceğiz",
    "birazdan karar vereceğiz",
    "önce seçenekleri duyalım",
    "kısa bilgi alabilir miyim",
    "garson beye ulaşabilir miyiz",
    "sipariş için hazırım",
    "bizi yönlendirir misiniz",
    "hızlıca başlayabilir miyiz",
    "akşam yemeği için geldik",
    "masamız sipariş verecek",
    "siparişi siz alır mısınız",
    "menüden seçmek istiyoruz",
    "bugünkü seçenekleri soracağım",
    "buradan sipariş verebilir miyim",
    "yemeğe başlayabilir miyiz",
    "ne alabileceğimi soracağım",
]

CLOSING_BASES = [
    "Yok teşekkürler, bu kadar",
    "Şimdilik bu kadar",
    "Başka istemiyorum",
    "Yeter, teşekkürler",
    "Bu kadar yeter",
    "Tamamdır, başka yok",
    "Başka almayacağım",
    "Siparişim bu kadar",
    "Hepsi bu",
    "Bu kadarı yeterli",
    "Devamı yok",
    "Daha istemiyorum",
    "Bunlar yeter",
    "Kapatabiliriz",
    "Tamam, yeterli",
    "Benden bu kadar",
    "Masamız için bu kadar",
    "Ekstra istemiyorum",
    "Son olarak bu kadar",
    "Başka bir şey yok",
]
CLOSING_SUFFIXES = [
    "",
    ", teşekkür ederim",
    ", sağ olun",
    ", şimdilik",
    ", bugünlük",
    ", masamız için",
    ", bu seferlik",
    ", efendim",
]

RUDE_PREFIXES = [
    "Hızlı olun",
    "Çabuk olun",
    "Bekletmeyin",
    "Vakit kaybetmeyin",
    "Hemen yazın",
    "Uzatmayın",
    "Acele edin",
    "Çok bekledik",
]
COMPLAINT_USERS = [
    "Çorba soğuk geldi.",
    "Çok geç getirdiniz.",
    "Bu fiyatlar çok pahalı.",
    "Servisiniz çok yavaş.",
    "Masayla kimse ilgilenmiyor.",
    "Yanlış ürün geldi.",
    "Tabağım eksik geldi.",
    "İçecek hâlâ gelmedi.",
    "Yemeğin tadını beğenmedim.",
    "Tatlı çok geç kaldı.",
    "Masamız temiz değil.",
    "Siparişimi karıştırdınız.",
    "Beklemekten sıkıldım.",
    "Bu kadar gecikme olmaz.",
    "Kimse bizi duymuyor.",
    "Çorbanın tadı iyi değil.",
    "Yemek soğumuş.",
    "İçecek yeterince soğuk değil.",
    "Porsiyon küçük geldi.",
    "Bu servis beni memnun etmedi.",
    "Sürekli bekliyoruz.",
    "Garson çağırıyorum, gelen yok.",
    "Hesap yanlış gibi.",
    "Yan masaya daha hızlı baktınız.",
    "Yemeğim eksik hazırlanmış.",
    "Tatlı beklediğim gibi değil.",
    "Sos istememiştim, koymuşsunuz.",
    "Siparişim unutuldu mu?",
    "Bu masa çok sallanıyor.",
    "Ben böyle hizmet görmedim.",
]

ALLERGY_USERS_AND_RESPONSES = [
    ("Gluten alerjim var, ne yiyebilirim?", "Izgara Tavuk Salata, Limonata ve Şalgam Suyu glutensiz. Kesin bilgi için personelimize danışabilirsiniz."),
    ("Gluten içermeyen seçenekleriniz neler?", "Izgara Tavuk Salata, Limonata ve Şalgam Suyu glutensiz. Kesin bilgi için personelimize danışabilirsiniz."),
    ("Gluten hangi ürünlerde var?", "Mercimek Çorbası, Kremalı Mantar Çorbası, Izgara Köfte, Et Döner ve Künefe gluten içeriyor. Personelimize danışabilirsiniz."),
    ("Mercimek Çorbasında gluten var mı?", "Mercimek Çorbası gluten içeriyor. Kesin bilgi için personelimize danışabilirsiniz."),
    ("Kremalı Mantar Çorbası gluten içerir mi?", "Kremalı Mantar Çorbası gluten içeriyor. Kesin bilgi için personelimize danışabilirsiniz."),
    ("Izgara Köfte glutensiz mi?", "Izgara Köfte gluten içeriyor. Kesin bilgi için personelimize danışabilirsiniz."),
    ("Et Dönerde gluten var mı?", "Et Döner gluten içeriyor. Kesin bilgi için personelimize danışabilirsiniz."),
    ("Künefe gluten içeriyor mu?", "Künefe gluten içeriyor. Kesin bilgi için personelimize danışabilirsiniz."),
    ("Süt ürünü alerjim var.", "Izgara Köfte, Et Döner, Izgara Tavuk Salata, Limonata ve Şalgam Suyu süt içermez. Personelimize danışabilirsiniz."),
    ("Süt ürünü içermeyen ne var?", "Izgara Köfte, Et Döner, Izgara Tavuk Salata, Limonata ve Şalgam Suyu süt içermez. Personelimize danışabilirsiniz."),
    ("Kremalı Mantar Çorbasında süt var mı?", "Kremalı Mantar Çorbası süt ürünü içeriyor. Kesin bilgi için personelimize danışabilirsiniz."),
    ("Fırın Sütlaç süt içeriyor mu?", "Fırın Sütlaç süt ürünü içeriyor. Kesin bilgi için personelimize danışabilirsiniz."),
    ("Künefede süt ürünü var mı?", "Künefe süt ürünü içeriyor. Kesin bilgi için personelimize danışabilirsiniz."),
    ("Yayık Ayran süt içerir mi?", "Yayık Ayran süt ürünü içeriyor. Kesin bilgi için personelimize danışabilirsiniz."),
    ("Kuruyemiş alerjim var, neye dikkat edeyim?", "Künefe kuruyemiş içeriyor. Kesin bilgi için personelimize danışabilirsiniz."),
    ("Künefede fındık var mı?", "Künefe kuruyemiş içeriyor. Kesin bilgi için personelimize danışabilirsiniz."),
    ("Kuruyemiş içeren tatlı hangisi?", "Künefe kuruyemiş içeriyor. Kesin bilgi için personelimize danışabilirsiniz."),
    ("Alerjen içermeyen seçenek var mı?", "Izgara Tavuk Salata, Limonata ve Şalgam Suyu alerjen içermiyor. Personelimize danışabilirsiniz."),
    ("Izgara Tavuk Salata alerjen açısından nasıl?", "Izgara Tavuk Salata alerjen içermiyor görünüyor. Kesin bilgi için personelimize danışabilirsiniz."),
    ("Limonatada alerjen var mı?", "Limonata alerjen içermiyor görünüyor. Kesin bilgi için personelimize danışabilirsiniz."),
]

VEGETARIAN_USERS = [
    "Vejetaryen seçenekleriniz var mı?",
    "Et yemiyorum, ne yiyebilirim?",
    "Etsiz ne alabilirim?",
    "Vejetaryen çorba var mı?",
    "Menüde et olmayan ne var?",
    "Ben vejetaryenim, ne önerirsiniz?",
    "Etsiz seçenekleri söyler misiniz?",
    "Vejetaryen olarak ne yiyebilirim?",
    "İçinde et olmayan ürünler hangileri?",
    "Vejetaryen gelen misafir için ne var?",
    "Ana yemek dışında etsiz seçenek var mı?",
    "Et istemiyorum, hangi ürün uygun?",
    "Sebze ağırlıklı ne var?",
    "Vejetaryen menünüzü duymak istiyorum.",
    "Etsiz hafif bir şey var mı?",
    "Vejetaryen dostu ürün söyler misiniz?",
    "Et ürünü içermeyen seçenekleri öğrenebilir miyim?",
    "Vejetaryen biri için hangi ürünler uygun?",
    "Kırmızı et yemiyorum, ne var?",
    "Tavuk da yemiyorum, ne alayım?",
]


def extract_system_prompt() -> str:
    text = DOC_PATH.read_text(encoding="utf-8")
    section = text.split("## 3. Sistem Promptu", 1)[1].split("## 4. Menü Özeti", 1)[0]
    match = re.search(r"```(.*?)```", section, flags=re.S)
    if not match:
        raise ValueError("Could not find the section 3 system prompt code block.")
    return match.group(1).strip("\n")


def cap_first(text: str) -> str:
    return text[:1].upper() + text[1:]


def item_at(index: int) -> dict[str, object]:
    return ITEMS[index % len(ITEMS)]


def alias_for(item: dict[str, object], index: int) -> str:
    aliases = item["aliases"]
    assert isinstance(aliases, list)
    return str(aliases[index % len(aliases)])


def line_item(item: dict[str, object], quantity: int = 1) -> str:
    name = str(item["name"])
    price = int(item["price"]) * quantity
    if quantity == 1:
        return f"{name} {price} TL"
    return f"{quantity} adet {name} {price} TL"


def confirm(item: dict[str, object], ack_index: int, follow_index: int = 0, quantity: int = 1) -> str:
    ack = ACKS[ack_index % len(ACKS)]
    follow = FOLLOW_UPS[follow_index % len(FOLLOW_UPS)]
    return f"{ack}, {line_item(item, quantity)}. {follow}"


def confirm_multi(items: Sequence[dict[str, object]], ack_index: int, follow_index: int = 0) -> str:
    if len(items) != 2:
        raise ValueError("confirm_multi expects exactly two items.")
    ack = ACKS[ack_index % len(ACKS)]
    follow = FOLLOW_UPS[follow_index % len(FOLLOW_UPS)].replace("Başka", "başka", 1)
    return f"{ack}, {line_item(items[0])}. {line_item(items[1])}, {follow}"


def account_response(total: int) -> str:
    return f"Toplam {total} TL. Afiyet olsun, iyi günler!"


def greeting_user(index: int) -> str:
    base = GREETING_BASES[index % len(GREETING_BASES)]
    tail = GREETING_TAILS[(index // len(GREETING_BASES)) % len(GREETING_TAILS)]
    return f"{base}, {tail}."


def closing_user(index: int) -> str:
    base = CLOSING_BASES[index % len(CLOSING_BASES)]
    suffix = CLOSING_SUFFIXES[(index // len(CLOSING_BASES)) % len(CLOSING_SUFFIXES)]
    return f"{base}{suffix}."


def order_user(item: dict[str, object], index: int) -> str:
    prefix = ORDER_PREFIXES[index % len(ORDER_PREFIXES)]
    template = ORDER_TEMPLATES[(index // len(ORDER_PREFIXES)) % len(ORDER_TEMPLATES)]
    alias = alias_for(item, index // (len(ORDER_PREFIXES) * len(ORDER_TEMPLATES)))
    return template.format(p=prefix, a=alias, A=cap_first(alias))


def extra_order_user(item: dict[str, object], index: int) -> str:
    template = EXTRA_TEMPLATES[index % len(EXTRA_TEMPLATES)]
    alias = alias_for(item, index // len(EXTRA_TEMPLATES))
    return template.format(a=alias, A=cap_first(alias))


def quantity_order_user(item: dict[str, object], quantity: int, index: int) -> str:
    template = QUANTITY_TEMPLATES[index % len(QUANTITY_TEMPLATES)]
    alias = alias_for(item, index // len(QUANTITY_TEMPLATES))
    word = NUMBER_WORDS[quantity]
    return template.format(N=cap_first(word), a=alias)


def category_question(category: str, index: int) -> str:
    words = CATEGORY_WORDS[category]
    template = CATEGORY_TEMPLATES[index % len(CATEGORY_TEMPLATES)]
    return template.format(**words)


def recommendation_question(category: str, index: int) -> str:
    words = CATEGORY_WORDS[category]
    template = RECOMMENDATION_TEMPLATES[index % len(RECOMMENDATION_TEMPLATES)]
    return template.format(cat=words["cat"])


def recommendation_response(category: str, index: int) -> str:
    responses = RECOMMENDATION_RESPONSES[category]
    return responses[index % len(responses)]


def account_user(index: int) -> str:
    base = ACCOUNT_BASES[index % len(ACCOUNT_BASES)]
    suffix = ACCOUNT_SUFFIXES[(index // len(ACCOUNT_BASES)) % len(ACCOUNT_SUFFIXES)]
    return f"{base}{suffix}?"


def subtotal_user(index: int) -> str:
    base = SUBTOTAL_BASES[index % len(SUBTOTAL_BASES)]
    suffix = SUBTOTAL_SUFFIXES[(index // len(SUBTOTAL_BASES)) % len(SUBTOTAL_SUFFIXES)]
    return f"{base}{suffix}?"


def stt_users() -> list[str]:
    users = list(STT_EXACT_USERS)
    for base in STT_EXTRA_BASES:
        for verb in STT_VERBS:
            text = f"{base} {verb}"
            if text not in users:
                users.append(text)
            if len(users) == 60:
                return users
    raise AssertionError("Not enough STT users generated.")


def unavailable_response() -> str:
    return "Bu konuda bilgim yok, personelimize sorabilirsiniz."


def offtopic_response(index: int) -> str:
    options = [
        "Bu konuda yardımcı olamam, menü veya sipariş için buradayım.",
        "Benim alanım sipariş ve menü, bu konuda personelimize sorabilirsiniz.",
    ]
    return options[index % len(options)]


def cancel_user(item: dict[str, object], index: int) -> str:
    acc = str(item["acc"])
    alias = alias_for(item, index)
    templates = [
        "{acc} çıkarır mısınız?",
        "{acc} iptal edin lütfen.",
        "{acc} istemiyorum artık.",
        "{acc} siler misiniz?",
        "{acc} kaldırın lütfen.",
        "{alias} olmasın, çıkarın.",
        "{alias} siparişini iptal edelim.",
        "{alias} vazgeçtim, istemiyorum.",
    ]
    return templates[index % len(templates)].format(acc=acc, alias=alias)


def cancel_response(item: dict[str, object], index: int) -> str:
    name = str(item["name"])
    options = [
        f"Anlıyorum, {name} çıkarıldı. Başka bir şey alır mısınız?",
        f"Tabii, {name} çıkarıldı. Başka ne arzu edersiniz?",
        f"Peki, {name} iptal edildi. Başka bir şey ister misiniz?",
        f"Elbette, {name} kaldırıldı. Başka bir şey alır mısınız?",
    ]
    return options[index % len(options)]


def change_user(old: dict[str, object], new: dict[str, object], index: int) -> str:
    old_acc = str(old["acc"])
    old_alias = alias_for(old, index)
    new_alias = alias_for(new, index)
    templates = [
        "{old_acc} yerine {new_alias} istiyorum.",
        "Aslında {old_alias} olmasın, {new_alias} alayım.",
        "{old_acc} çıkarın, yerine {new_alias} getirir misiniz?",
        "{old_alias} vazgeçtim, {new_alias} istiyorum.",
        "{old_acc} değiştirip {new_alias} alabilir miyim?",
        "Bunu {new_alias} ile değiştirir misiniz?",
        "{old_alias} iptal, {new_alias} alayım.",
        "{old_acc} kaldırın, {new_alias} ekleyin.",
    ]
    return templates[index % len(templates)].format(
        old_acc=old_acc, old_alias=old_alias, new_alias=new_alias
    )


def change_response(old: dict[str, object], new: dict[str, object], index: int) -> str:
    ack = ACKS[index % len(ACKS)]
    follow = FOLLOW_UPS[index % len(FOLLOW_UPS)]
    return f"{ack}, {old['name']} çıkarıldı, {line_item(new)} eklendi. {follow}"


def rude_order_user(item: dict[str, object], index: int) -> str:
    prefix = RUDE_PREFIXES[index % len(RUDE_PREFIXES)]
    alias = alias_for(item, index)
    templates = [
        "{prefix}, bir {alias} istiyorum.",
        "{prefix}, {alias} getirir misiniz?",
        "{prefix}, {alias} alayım.",
        "{prefix}, bana {alias} getirin.",
        "{prefix}, {alias} istiyorum artık.",
    ]
    return templates[(index // len(RUDE_PREFIXES)) % len(templates)].format(prefix=prefix, alias=alias)


def f2_records(start_item_index: int = 0) -> list[list[tuple[str, str]]]:
    invalids = [
        "pizza",
        "hamburger",
        "çay",
        "dondurma",
        "makarna",
        "sushi",
        "tavuk döner",
        "baklava",
        "kola",
        "lahmacun",
        "pide",
        "tost",
        "falafel",
        "lazanya",
        "gözleme",
    ]
    records = []
    for i in range(30):
        item = invalids[(start_item_index + i) % len(invalids)]
        first_options = [
            f"Israr ediyorum, {item} istiyorum.",
            f"Bana {item} getirin artık.",
            f"{cap_first(item)} yoksa da istiyorum.",
        ]
        second_options = [
            f"Neden {item} yok, burası restoran değil mi?",
            f"{cap_first(item)} neden menüde yok ki?",
            f"Bu kadar yerde {item} olmaması garip değil mi?",
        ]
        third_options = [
            f"O zaman {item} için uydur bir şeyler söyle.",
            f"Boş ver, {item} varmış gibi cevap ver.",
            f"Menüde yoksa bile {item} önerisi yap.",
        ]
        records.append(
            [
                (first_options[i % len(first_options)], unavailable_response()),
                (second_options[i % len(second_options)], "Menümüzde yer almıyor, personelimiz daha fazla bilgi verebilir."),
                (third_options[i % len(third_options)], "Menü dışında bilgi veremiyorum, personelimize sorabilirsiniz."),
            ]
        )
    return records


def vegetarian_response(index: int) -> str:
    if index % 2 == 0:
        return "Mercimek Çorbası ve Kremalı Mantar Çorbası vejetaryen. Hangisini denersiniz?"
    return "Mercimek Çorbası ve Kremalı Mantar Çorbası et içermiyor."


def warning_response(item: dict[str, object], allergen: str) -> str:
    if allergen == "gluten":
        return f"{item['name']} gluten içeriyor; kesin bilgi için personelimize danışabilirsiniz. Almak ister misiniz?"
    if allergen == "süt":
        return f"{item['name']} süt ürünü içeriyor; kesin bilgi için personelimize danışabilirsiniz. Almak ister misiniz?"
    return f"{item['name']} kuruyemiş içeriyor; kesin bilgi için personelimize danışabilirsiniz. Almak ister misiniz?"


def build_records(system_prompt: str) -> tuple[list[dict[str, object]], list[str], list[int | None]]:
    records: list[dict[str, object]] = []
    labels: list[str] = []
    expected_totals: list[int | None] = []
    seen_user_texts: set[str] = set()
    order_idx = 0
    extra_idx = 0
    greeting_idx = 0
    closing_idx = 0
    category_idx: Counter[str] = Counter()
    recommend_idx: Counter[str] = Counter()
    account_idx = 0
    subtotal_idx = 0

    def lower_initial(text: str) -> str:
        if not text:
            return text
        if text[0] == "İ":
            return "i" + text[1:]
        return text[0].lower() + text[1:]

    def unique_user(text: str) -> str:
        if text not in seen_user_texts:
            seen_user_texts.add(text)
            return text
        prefixes = [
            "Bu turda ",
            "Bu sefer ",
            "Şimdi ",
            "Masamız için ",
            "Benim için ",
            "Kısaca ",
            "Tekrar sorayım, ",
            "Rica ederim, ",
            "Mümkünse ",
            "Bugün özellikle ",
            "Son karar olarak ",
            "Ayrıca ",
            "Hızlıca ",
            "Nazikçe ",
            "Efendim, ",
            "Arkadaşım için ",
        ]
        lowered = lower_initial(text)
        for prefix in prefixes:
            candidate = prefix + lowered
            if candidate not in seen_user_texts:
                seen_user_texts.add(candidate)
                return candidate
        suffixes = [", lütfen", ", rica ederim", ", bu kez", ", masamız için", ", şimdilik"]
        stem = text[:-1] if text[-1:] in ".?!" else text
        end = text[-1:] if text[-1:] in ".?!" else "."
        for suffix in suffixes:
            candidate = f"{stem}{suffix}{end}"
            if candidate not in seen_user_texts:
                seen_user_texts.add(candidate)
                return candidate
        raise ValueError(f"Could not make user text unique: {text}")

    def add(label: str, pairs: Sequence[tuple[str, str]], expected_total: int | None = None) -> None:
        messages = [{"role": "system", "content": system_prompt}]
        for user, assistant in pairs:
            messages.append({"role": "user", "content": unique_user(user)})
            messages.append({"role": "assistant", "content": assistant})
        records.append({"messages": messages})
        labels.append(label)
        expected_totals.append(expected_total)

    # A1: short greeting -> order -> close
    for i in range(80):
        item = item_at(i)
        pairs = [
            (greeting_user(greeting_idx), GREETING_RESPONSES[i % len(GREETING_RESPONSES)]),
            (order_user(item, order_idx), confirm(item, i, i)),
            (closing_user(closing_idx), CLOSING_RESPONSES[i % len(CLOSING_RESPONSES)]),
        ]
        add("A1", pairs)
        greeting_idx += 1
        order_idx += 1
        closing_idx += 1

    # A2: greeting -> category -> order -> extra order -> close
    categories = ["Çorba", "Ana Yemek", "Tatlı", "İçecek"]
    for i in range(80):
        category = categories[i % len(categories)]
        item = CATEGORY_ITEMS[category][i % len(CATEGORY_ITEMS[category])]
        extra_item = item_at(i + 5)
        if extra_item["key"] == item["key"]:
            extra_item = item_at(i + 6)
        pairs = [
            (greeting_user(greeting_idx), GREETING_RESPONSES[i % len(GREETING_RESPONSES)]),
            (category_question(category, category_idx[category]), CATEGORY_RESPONSES[category]),
            (order_user(item, order_idx), confirm(item, i, i)),
            (extra_order_user(extra_item, extra_idx), confirm(extra_item, i + 1, i + 1)),
            (closing_user(closing_idx), CLOSING_RESPONSES[i % len(CLOSING_RESPONSES)]),
        ]
        add("A2", pairs)
        greeting_idx += 1
        category_idx[category] += 1
        order_idx += 1
        extra_idx += 1
        closing_idx += 1

    # A3: full flow with account and subtotal deflection
    for i in range(40):
        first = item_at(i)
        second = item_at(i + 3)
        if second["key"] == first["key"]:
            second = item_at(i + 4)
        total = int(first["price"]) + int(second["price"])
        pairs = [
            (greeting_user(greeting_idx), GREETING_RESPONSES[i % len(GREETING_RESPONSES)]),
            (order_user(first, order_idx), confirm(first, i, i)),
            (extra_order_user(second, extra_idx), confirm(second, i + 1, i + 1)),
            (subtotal_user(subtotal_idx), unavailable_response()),
            (account_user(account_idx), account_response(total)),
        ]
        add("A3", pairs, expected_total=total)
        greeting_idx += 1
        order_idx += 1
        extra_idx += 1
        subtotal_idx += 1
        account_idx += 1

    # B1: one-turn category listing
    for i in range(40):
        category = categories[i % len(categories)]
        add("B1", [(category_question(category, category_idx[category]), CATEGORY_RESPONSES[category])])
        category_idx[category] += 1

    # B2: category listing -> order confirmation
    for i in range(40):
        category = categories[i % len(categories)]
        item = CATEGORY_ITEMS[category][i % len(CATEGORY_ITEMS[category])]
        pairs = [
            (category_question(category, category_idx[category]), CATEGORY_RESPONSES[category]),
            (order_user(item, order_idx), confirm(item, i, i)),
        ]
        add("B2", pairs)
        category_idx[category] += 1
        order_idx += 1

    # C1: category-specific recommendations
    for i in range(50):
        category = categories[i % len(categories)]
        pairs = [
            (
                recommendation_question(category, recommend_idx[category]),
                recommendation_response(category, recommend_idx[category]),
            )
        ]
        add("C1", pairs)
        recommend_idx[category] += 1

    # C2: general recommendations
    for i in range(30):
        add(
            "C2",
            [
                (
                    GENERAL_RECOMMENDATION_USERS[i],
                    GENERAL_RECOMMENDATION_RESPONSES[i % len(GENERAL_RECOMMENDATION_RESPONSES)],
                )
            ],
        )

    # D1: single item orders
    for i in range(30):
        item = item_at(i + 2)
        add("D1", [(order_user(item, order_idx), confirm(item, i, i))])
        order_idx += 1

    # D2: two products in one user turn
    for i in range(30):
        first = item_at(i)
        second = item_at(i + 7)
        if first["key"] == second["key"]:
            second = item_at(i + 8)
        first_alias = alias_for(first, i)
        second_alias = alias_for(second, i)
        user = MULTI_ORDER_TEMPLATES[i % len(MULTI_ORDER_TEMPLATES)].format(
            a1=first_alias,
            A1=cap_first(first_alias),
            a2=second_alias,
        )
        add("D2", [(user, confirm_multi([first, second], i, i))])
        order_idx += 1

    # D3: explicit quantities
    quantities = [2, 3, 4, 5]
    for i in range(20):
        item = item_at(i + 8)
        qty = quantities[i % len(quantities)]
        add("D3", [(quantity_order_user(item, qty, i), confirm(item, i, i, quantity=qty))])

    # D4: subtotal questions during ordering
    for i in range(20):
        item = item_at(i + 4)
        pairs = [
            (order_user(item, order_idx), confirm(item, i, i)),
            (subtotal_user(subtotal_idx), unavailable_response()),
        ]
        add("D4", pairs)
        order_idx += 1
        subtotal_idx += 1

    # D5: account flows, all 45 item pairs plus 5 triples
    for i, pair in enumerate(combinations(ITEMS, 2)):
        first, second = pair
        total = int(first["price"]) + int(second["price"])
        pairs = [
            (order_user(first, order_idx), confirm(first, i, i)),
            (extra_order_user(second, extra_idx), confirm(second, i + 1, i + 1)),
            (account_user(account_idx), account_response(total)),
        ]
        add("D5", pairs, expected_total=total)
        order_idx += 1
        extra_idx += 1
        account_idx += 1

    triples = [
        [ITEM_BY_KEY["doner"], ITEM_BY_KEY["salgam"], ITEM_BY_KEY["kunefe"]],
        [ITEM_BY_KEY["kofte"], ITEM_BY_KEY["sutlac"], ITEM_BY_KEY["ayran"]],
        [ITEM_BY_KEY["mercimek"], ITEM_BY_KEY["tavuk_salata"], ITEM_BY_KEY["limonata"]],
        [ITEM_BY_KEY["mantar"], ITEM_BY_KEY["doner"], ITEM_BY_KEY["sutlac"]],
        [ITEM_BY_KEY["tavuk_salata"], ITEM_BY_KEY["kunefe"], ITEM_BY_KEY["salgam"]],
    ]
    for i, triple in enumerate(triples):
        total = sum(int(item["price"]) for item in triple)
        pairs = [
            (order_user(triple[0], order_idx), confirm(triple[0], i, i)),
            (extra_order_user(triple[1], extra_idx), confirm(triple[1], i + 1, i + 1)),
            (extra_order_user(triple[2], extra_idx + 1), confirm(triple[2], i + 2, i + 2)),
            (account_user(account_idx), account_response(total)),
        ]
        add("D5", pairs, expected_total=total)
        order_idx += 1
        extra_idx += 2
        account_idx += 1

    # E1: unavailable products
    for user in UNAVAILABLE_USERS:
        add("E1", [(user, unavailable_response())])

    # E2: malformed STT inputs
    for i, user in enumerate(stt_users()):
        response = unavailable_response() if i % 2 == 0 else "Anlayamadım, tekrar edebilir misiniz?"
        add("E2", [(user, response)])

    # E3: off-topic
    for i, user in enumerate(OFFTOPIC_USERS):
        add("E3", [(user, offtopic_response(i))])

    # F1: rude ordering, still polite and rule-bound
    for i in range(40):
        item = item_at(i + 1)
        add("F1", [(rude_order_user(item, i), confirm(item, i, i))])

    # F2: insistence after unavailable item refusal
    for pairs in f2_records():
        add("F2", pairs)

    # F3: complaints and dissatisfaction
    complaint_responses = [
        "Özür dilerim, personelimizi bilgilendirebilirsiniz.",
        "Özür dilerim, size nasıl yardımcı olabilirim?",
        "Anlıyorum, size yardımcı olmaya çalışırım.",
    ]
    for i, user in enumerate(COMPLAINT_USERS):
        add("F3", [(user, complaint_responses[i % len(complaint_responses)])])

    # G1: allergy questions
    for i in range(40):
        user, response = ALLERGY_USERS_AND_RESPONSES[i % len(ALLERGY_USERS_AND_RESPONSES)]
        if i >= len(ALLERGY_USERS_AND_RESPONSES):
            user = user[:-1] + f" bugün?"
        add("G1", [(user, response)])

    # G2: vegetarian questions
    for i, user in enumerate(VEGETARIAN_USERS):
        add("G2", [(user, vegetarian_response(i))])

    # G3: allergy plus order combinations
    unsafe_cases = [
        (ITEM_BY_KEY["mercimek"], "gluten", "Glutenim var ama mercimek çorbası alayım."),
        (ITEM_BY_KEY["mantar"], "gluten", "Glutene hassasım ama kremalı mantar istiyorum."),
        (ITEM_BY_KEY["kofte"], "gluten", "Gluten alerjim var, yine de köfte alayım."),
        (ITEM_BY_KEY["doner"], "gluten", "Glutenim var ama et döner istiyorum."),
        (ITEM_BY_KEY["kunefe"], "gluten", "Gluten hassasiyetim var, künefe alabilir miyim?"),
        (ITEM_BY_KEY["mantar"], "süt", "Süt alerjim var ama kremalı mantar çorbası istiyorum."),
        (ITEM_BY_KEY["sutlac"], "süt", "Süt ürünü alerjim var, fırın sütlaç alayım."),
        (ITEM_BY_KEY["kunefe"], "süt", "Süte hassasım ama künefe istiyorum."),
        (ITEM_BY_KEY["ayran"], "süt", "Süt alerjim var ama yayık ayran alayım."),
        (ITEM_BY_KEY["kunefe"], "kuruyemiş", "Kuruyemiş alerjim var ama künefe istiyorum."),
    ]
    confirm_variants = [
        "Yine de alayım.",
        "Tamam, yine de istiyorum.",
        "Riskini biliyorum, alayım.",
        "Personelle de sorarım, alayım.",
        "Bilerek istiyorum.",
        "Uygunsa yine de getirir misiniz?",
        "Kararım değişmedi, alayım.",
        "Yine de sipariş etmek istiyorum.",
        "Bunu kabul edip alayım.",
        "Tamam, getirir misiniz?",
    ]
    for i, (item, allergen, user) in enumerate(unsafe_cases):
        pairs = [
            (user, warning_response(item, allergen)),
            (confirm_variants[i], confirm(item, i, i)),
        ]
        add("G3", pairs)

    safe_questions = [
        ("Glutensiz ne var?", "Izgara Tavuk Salata, Limonata ve Şalgam Suyu glutensiz. Personelimize danışabilirsiniz.", ITEM_BY_KEY["tavuk_salata"]),
        ("Gluten olmadan ne alabilirim?", "Izgara Tavuk Salata, Limonata ve Şalgam Suyu glutensiz. Personelimize danışabilirsiniz.", ITEM_BY_KEY["limonata"]),
        ("Süt ürünü olmadan ne seçebilirim?", "Izgara Köfte, Et Döner, Izgara Tavuk Salata, Limonata ve Şalgam Suyu süt içermez. Personelimize danışabilirsiniz.", ITEM_BY_KEY["doner"]),
        ("Sütsüz içecek ne var?", "Limonata ve Şalgam Suyu süt içermez. Personelimize danışabilirsiniz.", ITEM_BY_KEY["salgam"]),
        ("Kuruyemişsiz tatlı var mı?", "Fırın Sütlaç kuruyemiş içermez görünüyor. Kesin bilgi için personelimize danışabilirsiniz.", ITEM_BY_KEY["sutlac"]),
        ("Alerjen içermeyen ne alabilirim?", "Izgara Tavuk Salata, Limonata ve Şalgam Suyu alerjen içermiyor. Personelimize danışabilirsiniz.", ITEM_BY_KEY["tavuk_salata"]),
        ("Glutensiz içecek söyler misiniz?", "Limonata ve Şalgam Suyu glutensiz. Personelimize danışabilirsiniz.", ITEM_BY_KEY["limonata"]),
        ("Süt alerjim var, güvenli içecek ne?", "Limonata ve Şalgam Suyu süt içermez. Personelimize danışabilirsiniz.", ITEM_BY_KEY["salgam"]),
        ("Glutensiz hafif yemek ne var?", "Izgara Tavuk Salata glutensiz görünüyor. Kesin bilgi için personelimize danışabilirsiniz.", ITEM_BY_KEY["tavuk_salata"]),
        ("Süt ürünü olmayan ana yemek var mı?", "Izgara Köfte, Et Döner ve Izgara Tavuk Salata süt içermez. Personelimize danışabilirsiniz.", ITEM_BY_KEY["kofte"]),
    ]
    for i, (question, response, item) in enumerate(safe_questions):
        pairs = [
            (question, response),
            (order_user(item, order_idx), confirm(item, i, i)),
        ]
        add("G3", pairs)
        order_idx += 1

    # H1: cancellations
    for i in range(40):
        item = item_at(i)
        pairs = [
            (order_user(item, order_idx), confirm(item, i, i)),
            (cancel_user(item, i), cancel_response(item, i)),
        ]
        add("H1", pairs)
        order_idx += 1

    # H2: changes
    for i in range(40):
        old = item_at(i + 3)
        new = item_at(i + 8)
        if old["key"] == new["key"]:
            new = item_at(i + 9)
        pairs = [
            (order_user(old, order_idx), confirm(old, i, i)),
            (change_user(old, new, i), change_response(old, new, i)),
        ]
        add("H2", pairs)
        order_idx += 1

    return records, labels, expected_totals


def sentence_count(text: str) -> int:
    return len(re.findall(r"[.!?]", text))


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def iter_assistant_messages(record: dict[str, object]) -> Iterable[str]:
    messages = record["messages"]
    assert isinstance(messages, list)
    for message in messages:
        if message["role"] == "assistant":
            yield str(message["content"])


def validate(records: Sequence[dict[str, object]], labels: Sequence[str], expected_totals: Sequence[int | None], system_prompt: str) -> None:
    errors: list[str] = []
    scenario_counts = Counter(label[0] for label in labels)
    if scenario_counts != TARGET_COUNTS:
        errors.append(f"Scenario counts mismatch: {dict(scenario_counts)}")
    if len(records) != sum(TARGET_COUNTS.values()):
        errors.append(f"Expected 970 records, got {len(records)}")

    user_texts: list[str] = []
    item_name_pattern = "|".join(re.escape(str(item["name"])) for item in ITEMS)
    price_pattern = re.compile(rf"(?:(\d+) adet )?({item_name_pattern}) (\d+) TL")
    item_prices = {str(item["name"]): int(item["price"]) for item in ITEMS}
    forbidden_assistant_patterns = [
        r"\bmusun\b",
        r"\bmısın\b",
        r"\bmisin\b",
        r"\bistiyorsun\b",
        r"\balır musunuz\b",
        r"Siparişiniz onaylandı",
        r"onaylanıyor",
        r"kaydedildi",
        r"Kuneffe",
    ]
    invalid_foods_in_assistant = [
        "Hamburger",
        "Pizza",
        "Galifon",
        "Çay",
        "Kahve",
        "Makarna",
        "Lazanya",
        "Sushi",
        "Baklava",
        "Domates Çorbası",
        "Sebzeli Makarna",
        "Etli Güveç",
    ]

    for rec_idx, (record, label, expected_total) in enumerate(zip(records, labels, expected_totals)):
        messages = record.get("messages")
        if not isinstance(messages, list) or not messages:
            errors.append(f"{rec_idx}: messages missing")
            continue
        if messages[0] != {"role": "system", "content": system_prompt}:
            errors.append(f"{rec_idx}: system prompt mismatch")
        expected_role = "user"
        for msg_idx, message in enumerate(messages[1:], start=1):
            if message.get("role") != expected_role:
                errors.append(f"{rec_idx}:{msg_idx}: expected role {expected_role}, got {message.get('role')}")
            expected_role = "assistant" if expected_role == "user" else "user"
            if message.get("role") == "user":
                user_texts.append(str(message.get("content")))

        assistants = list(iter_assistant_messages(record))
        for assistant in assistants:
            if word_count(assistant) > 25:
                errors.append(f"{rec_idx}: assistant too long ({word_count(assistant)}): {assistant}")
            if sentence_count(assistant) > 2:
                errors.append(f"{rec_idx}: assistant has >2 sentences: {assistant}")
            lowered = assistant.lower()
            for pattern in forbidden_assistant_patterns:
                if re.search(pattern, lowered if pattern.startswith("\\b") else assistant, flags=re.I):
                    errors.append(f"{rec_idx}: forbidden assistant pattern {pattern}: {assistant}")
            for invalid in invalid_foods_in_assistant:
                if invalid in assistant:
                    errors.append(f"{rec_idx}: invalid food in assistant: {assistant}")
            if "TL" in assistant and "Getireyim mi" in assistant:
                errors.append(f"{rec_idx}: order confirmation asks Getireyim mi: {assistant}")
            if assistant.startswith(("Çorbada", "Ana yemekte", "Tatlıda", "İçecekte")) and "TL" in assistant:
                errors.append(f"{rec_idx}: category response contains price: {assistant}")
            if label.startswith("C") and "TL" in assistant:
                errors.append(f"{rec_idx}: recommendation contains price: {assistant}")
            if label == "E1" and assistant != unavailable_response():
                errors.append(f"{rec_idx}: E1 response must be exact: {assistant}")
            if label == "E2" and assistant not in {unavailable_response(), "Anlayamadım, tekrar edebilir misiniz?"}:
                errors.append(f"{rec_idx}: E2 response invalid: {assistant}")
            if label == "E3" and assistant not in {
                "Bu konuda yardımcı olamam, menü veya sipariş için buradayım.",
                "Benim alanım sipariş ve menü, bu konuda personelimize sorabilirsiniz.",
            }:
                errors.append(f"{rec_idx}: E3 response invalid: {assistant}")

            matches = list(price_pattern.finditer(assistant))
            for match in matches:
                quantity = int(match.group(1) or 1)
                name = match.group(2)
                price = int(match.group(3))
                expected_price = item_prices[name] * quantity
                if price != expected_price:
                    errors.append(f"{rec_idx}: price mismatch for {name}: {price} != {expected_price}")
            if "TL" in assistant and not matches and not assistant.startswith("Toplam "):
                errors.append(f"{rec_idx}: TL without item/account pattern: {assistant}")

        if label in {"A3", "D5"}:
            account = assistants[-1]
            if expected_total is None or account != account_response(expected_total):
                errors.append(f"{rec_idx}: bad account total, expected {expected_total}: {account}")
        elif any(assistant.startswith("Toplam ") for assistant in assistants):
            errors.append(f"{rec_idx}: unexpected account response outside account flow")

        if label.startswith("A"):
            greeting = assistants[0].lower()
            required = ["çorba", "ana yemek", "tatlı", "içecek"]
            if not all(word in greeting for word in required):
                errors.append(f"{rec_idx}: greeting missing category words: {assistants[0]}")
            if any(str(item["name"]) in assistants[0] for item in ITEMS):
                errors.append(f"{rec_idx}: greeting mentions product: {assistants[0]}")

    duplicate_users = [text for text, count in Counter(user_texts).items() if count > 1]
    if duplicate_users:
        errors.append(f"Duplicate user messages: {duplicate_users[:20]}")

    if errors:
        raise ValueError("\n".join(errors[:100]))


def write_jsonl(records: Sequence[dict[str, object]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> None:
    system_prompt = extract_system_prompt()
    records, labels, expected_totals = build_records(system_prompt)
    validate(records, labels, expected_totals, system_prompt)
    write_jsonl(records, OUT_PATH)
    counts = Counter(label[0] for label in labels)
    print(f"Wrote {len(records)} records -> {OUT_PATH}")
    print("Scenario counts:", dict(sorted(counts.items())))


if __name__ == "__main__":
    main()
