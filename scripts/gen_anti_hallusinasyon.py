#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wbot_v5 (C paketi) — Madde 3: Anti-Hallüsinasyon (Ürün Açıklaması)
Hedef: 100 yeni, menu.yaml-dayalı örnek (E34 bilinen zayıflığı).
Çalıştır: python scripts/gen_anti_hallusinasyon.py

Bu, LLM-API kaleminin script'e sabitlenmiş halidir (görev #27 deseni):
kayıtların doğal-dil içeriği elle yazılmıştır; script kanonik sistem
promptunu programatik ekler, JSONL yazar, menu.yaml'a KARŞI self-check
koşar. Harici API çağrısı yoktur — reprodüksiyonu mümkün statik artefakt.

KRİTİK KISIT (doküman madde 3): Her asistan yanıtı YALNIZCA menu.yaml'da
gerçekten yazılı alanlara (description, allergens, price, tags) dayanır;
menüde olmayan hiçbir detay UYDURULMAZ. İki mod:
  - "grounded": yanıt yalnız menu.yaml'daki gerçek description/allergen
    bilgisini tekrarlar (self-check: yanıttaki her malzeme sözcüğü ilgili
    ürünün menu.yaml alanlarında GEÇMELİ — canlı çapraz kontrol).
  - "honest": bilgi menüde yok → uydurma yapmaz, "menümüzde belirtilmemiş"
    / "bilgim yok" + personel yönlendirmesi (self-check: dürüstlük ifadesi).

3 alt tip (doküman madde 3):
  1. Açıklamada olmayan ekstra detay istemi (~34)
  2. Malzeme türü/ayrıntısı menüde yok — "künefede fındık mı ceviz mi" (~33)
  3. Porsiyon/pişirme nicel detayı — "kaç gram", "kaç dakika" (~33)

Self-check (script sonunda):
  - Hiçbir yanıt UYDURMA nicel detay içermez → hiçbir rakam (digit) YOK.
  - grounded: malzeme sözcükleri menu.yaml çapraz kontrolünden geçer.
  - honest: dürüstlük/yönlendirme ifadesi içerir.
  - Her yanıt ilgili ürünün kanonik adını içerir (grounding çıpası).
  - BENZERSİZLİK guard'ı (görev #28): tüm sorular ve tüm yanıtlar benzersiz
    — kalıp-tekrarı anti-hallüsinasyonda en zararlı hata.
"""
import json
import sys
from pathlib import Path

import yaml

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SYSTEM = json.loads(
    open(
        "robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl",
        encoding="utf-8",
    ).readline()
)["messages"][0]["content"]

# ── menu.yaml canlı yükleme (YALNIZCA OKU) ──────────────────────────────────
_MENU = yaml.safe_load(open("robot_waiter_ai/data/menu.yaml", encoding="utf-8"))["menu"]
_ITEM = {it["name"]: it for it in _MENU}
_ALLERGEN_TR = {"gluten": "gluten", "dairy": "süt", "nuts": "kuruyemiş"}

NAME = {
    "mercimek": "Mercimek Çorbası",
    "mantar":   "Kremalı Mantar Çorbası",
    "kofte":    "Izgara Köfte",
    "doner":    "Et Döner",
    "salata":   "Izgara Tavuk Salata",
    "sutlac":   "Fırın Sütlaç",
    "kunefe":   "Künefe",
    "ayran":    "Yayık Ayran",
    "limonata": "Limonata",
    "salgam":   "Şalgam Suyu",
}

# Ürünün menu.yaml'da GERÇEKTEN yazılı, izin verilen bilgi metni:
# description + Türkçe alerjen sözcükleri. grounded yanıtlar bunun dışına çıkamaz.
def _allowed_text(name):
    it = _ITEM[name]
    parts = [it["description"]]
    parts += [_ALLERGEN_TR[a] for a in it["allergens"]]
    return " ".join(parts).lower()

# Hallüsinasyona en açık malzeme/tür sözcükleri — grounded yanıtta geçen her
# biri ilgili ürünün izin verilen metninde bulunmalı (uydurma malzeme yakalar).
FAB_VOCAB = [
    "soğan", "sarımsak", "biber", "domates", "patates", "pirinç", "bulgur",
    "tereyağı", "zeytinyağı", "zeytin", "fındık", "ceviz", "fıstık", "badem",
    "antep", "krema", "peynir", "kadayıf", "mercimek", "havuç", "mantar",
    "tavuk", "dana", "roka", "nane", "limon", "şerbet", "lavaş", "sumak",
    "köz", "marine", "kuzu", "hindi", "balık", "karides", "yumurta",
    "çikolata", "vanilya", "tarçın", "susam", "sirke", "dondurma",
]

# ── Alt tip 1: açıklamada olmayan ekstra detay istemi (34) ───────────────────
# (ürün, soru, yanıt, mod)
S1 = [
    # ── grounded: sorulan detay açıklamada VAR → yalnız yazılı olanı söyle (17) ──
    ("kofte",    "Köftenin yanında garnitür var mı?",
     "Izgara Köfte, elma dilim patates ve köz biber ile servis ediliyor.", "grounded"),
    ("salata",   "Salatada domates kullanıyor musunuz?",
     "Evet, Izgara Tavuk Salata taze roka, domates ve zeytinyağı sosuyla hazırlanıyor.", "grounded"),
    ("doner",    "Döner neyle servis ediliyor?",
     "Et Döner, özel soslu lavaş ve sumaklı soğan ile servis ediliyor.", "grounded"),
    ("mercimek", "Mercimek çorbasında havuç var mı?",
     "Evet, Mercimek Çorbası kırmızı mercimek, soğan ve havuç ile günlük hazırlanıyor.", "grounded"),
    ("limonata", "Limonatada nane kullanıyor musunuz?",
     "Evet, Limonata taze nane yaprakları ve limon ile hazırlanıyor.", "grounded"),
    ("sutlac",   "Sütlaç fırında mı hazırlanıyor?",
     "Evet, Fırın Sütlaç fırında üzeri kızarmış şekilde, günlük taze sütle hazırlanıyor.", "grounded"),
    ("mantar",   "Mantar çorbası kremalı mı?",
     "Evet, Kremalı Mantar Çorbası taze dağ mantarları ve krema ile hazırlanıyor.", "grounded"),
    ("kunefe",   "Künefe peynirli mi?",
     "Evet, Künefe özel Hatay peyniri ve ince tel kadayıfla, şerbetle sıcak servis ediliyor.", "grounded"),
    ("ayran",    "Ayran soğuk mu servis ediliyor?",
     "Evet, Yayık Ayran köpüklü ve soğuk şekilde servis ediliyor.", "grounded"),
    ("salgam",   "Şalgamın acılı seçeneği var mı?",
     "Evet, Şalgam Suyu acılı veya acısız olarak sunuluyor.", "grounded"),
    ("kofte",    "Köftede köz biber oluyor mu?",
     "Evet, Izgara Köfte köz biber ile birlikte servis ediliyor.", "grounded"),
    ("salata",   "Salatada roka var mı?",
     "Evet, Izgara Tavuk Salata taze roka içeriyor.", "grounded"),
    ("doner",    "Dönerin eti dana eti mi?",
     "Et Döner ince dilimlenmiş dana eti ile hazırlanıyor.", "grounded"),
    ("mercimek", "Mercimek çorbası günlük mü yapılıyor?",
     "Evet, Mercimek Çorbası her gün günlük olarak hazırlanıyor.", "grounded"),
    ("sutlac",   "Sütlaç geleneksel usulde mi?",
     "Evet, Fırın Sütlaç geleneksel usulde, fırında üzeri kızarmış şekilde hazırlanıyor.", "grounded"),
    ("limonata", "Limonata soğuk mu geliyor?",
     "Evet, Limonata soğuk olarak servis ediliyor, taze nane ve limonla hazırlanıyor.", "grounded"),
    ("kunefe",   "Künefe sıcak mı geliyor?",
     "Evet, Künefe şerbetle sıcak olarak servis ediliyor.", "grounded"),
    # ── honest: sorulan detay açıklamada YOK → uydurma, yönlendir (17) ──
    ("kofte",    "Köftenin sosu var mı, nasıl bir sos?",
     "Izgara Köfte'nin sos detayı menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("salata",   "Salatanın sosunda sirke var mı?",
     "Izgara Tavuk Salata'nın sos içeriğinde sirke olup olmadığı menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("doner",    "Dönerle beraber içecek geliyor mu?",
     "Et Döner'in yanında içecek verilip verilmediği menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("mercimek", "Mercimek çorbasının yanında ekmek veriyor musunuz?",
     "Mercimek Çorbası'nın yanında ekmek verilip verilmediği menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("limonata", "Limonata şekersiz olabiliyor mu?",
     "Limonata'nın şekersiz seçeneği olup olmadığı menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("sutlac",   "Sütlacın üzerinde tarçın var mı?",
     "Fırın Sütlaç'ın üzerinde tarçın olup olmadığı menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("mantar",   "Mantar çorbasının yanında ekmek kızartması geliyor mu?",
     "Kremalı Mantar Çorbası'nın yanında ekmek kızartması olup olmadığı menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("kunefe",   "Künefenin yanında dondurma geliyor mu?",
     "Künefe'nin yanında dondurma verilip verilmediği menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("ayran",    "Ayranı sürahiyle alabilir miyiz?",
     "Yayık Ayran'ın sürahiyle sunulup sunulmadığı menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("salgam",   "Şalgamın yanında limon veriyor musunuz?",
     "Şalgam Suyu'nun yanında limon verilip verilmediği menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("kofte",    "Köfteyi az pişmiş yaptırabilir miyim?",
     "Izgara Köfte'nin pişirme derecesi seçeneği menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("salata",   "Salataya ekstra tavuk ekletebilir miyim?",
     "Izgara Tavuk Salata'ya ekstra ekleme yapılıp yapılamayacağı menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("doner",    "Döneri dürüm olarak alabilir miyim?",
     "Et Döner'in dürüm olarak sunulup sunulmadığı menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("mercimek", "Çorbayı ekstra acılı yaptırabilir miyim?",
     "Mercimek Çorbası'nın acılı seçeneği olup olmadığı menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("kunefe",   "Künefeyi az şerbetli yaptırabilir miyim?",
     "Künefe'nin az şerbetli hazırlanıp hazırlanamayacağı menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("sutlac",   "Sütlaç sıcak mı soğuk mu servis ediliyor?",
     "Fırın Sütlaç'ın sıcak mı soğuk mu servis edildiği menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("ayran",    "Ayranın yağ oranı düşük mü?",
     "Yayık Ayran'ın yağ oranı menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
]

# ── Alt tip 2: malzeme türü/ayrıntısı menüde yok (33) ────────────────────────
S2 = [
    ("kunefe",   "Künefede fındık mı ceviz mi var?",
     "Künefe'de kuruyemiş bulunuyor ancak fındık mı ceviz mi olduğu menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("kunefe",   "Künefedeki kuruyemiş antep fıstığı mı?",
     "Künefe kuruyemiş içeriyor fakat türü menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("kofte",    "Köftede hangi baharatlar var?",
     "Izgara Köfte'nin baharat içeriği menümüzde ayrıntılı belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("kofte",    "Köftenin eti dana mı kuzu mu?",
     "Izgara Köfte'nin et türü menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("doner",    "Dönerin özel sosunda neler var?",
     "Et Döner'in özel sos içeriği menümüzde ayrıntılı yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("salata",   "Salatanın sosu limonlu mu sirkeli mi?",
     "Izgara Tavuk Salata zeytinyağı sosuyla hazırlanıyor; sosun diğer içerikleri menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("salata",   "Salatadaki tavuk hangi baharatlarla marine ediliyor?",
     "Izgara Tavuk Salata marineli tavuk göğsü içeriyor ancak marinasyondaki baharatlar menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("mercimek", "Mercimek çorbasında tereyağı mı sıvı yağ mı var?",
     "Mercimek Çorbası'nda kullanılan yağ türü menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("mantar",   "Mantar çorbasındaki mantar kültür mü yabani mi?",
     "Kremalı Mantar Çorbası taze dağ mantarlarıyla yapılıyor; mantarın türü menümüzde ayrıntılı yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("sutlac",   "Sütlaçta pirinç mi nişasta mı kullanılıyor?",
     "Fırın Sütlaç'ın içindeki nişasta türü menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("kunefe",   "Künefenin peyniri hangi peynir?",
     "Künefe özel Hatay peyniriyle yapılıyor; bunun dışındaki peynir ayrıntısı menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("ayran",    "Ayran inek sütünden mi keçi sütünden mi?",
     "Yayık Ayran'ın süt kaynağı menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("limonata", "Limonatada şeker mi bal mı kullanılıyor?",
     "Limonata taze nane ve limonla hazırlanıyor; tatlandırıcı detayı menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("salgam",   "Şalgamda havuç var mı, hangi tür?",
     "Şalgam Suyu'nun içerik ayrıntıları menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("doner",    "Dönerin lavaşı tam buğday mı?",
     "Et Döner lavaşla servis ediliyor ancak lavaşın türü menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("kofte",    "Köftenin yanındaki biber acı mı?",
     "Izgara Köfte köz biberle geliyor; biberin acılık durumu menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("kunefe",   "Künefenin şerbeti glikozlu mu?",
     "Künefe şerbetle servis ediliyor; şerbetin içeriği menümüzde ayrıntılı yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("mercimek", "Mercimek kırmızı mercimek mi yeşil mercimek mi?",
     "Mercimek Çorbası kırmızı mercimekle hazırlanıyor.", "grounded"),
    ("salata",   "Salatada tane zeytin var mı?",
     "Izgara Tavuk Salata zeytinyağı sosuyla hazırlanıyor; tane zeytin olup olmadığı menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("doner",    "Dönerin soğanı kuru soğan mı?",
     "Et Döner sumaklı soğanla geliyor; soğanın türü menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("sutlac",   "Sütlaç inek sütüyle mi yapılıyor?",
     "Fırın Sütlaç taze sütle hazırlanıyor ancak sütün kaynağı menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("kunefe",   "Künefede tereyağı kullanılıyor mu?",
     "Künefe'de tereyağı kullanılıp kullanılmadığı menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("mantar",   "Mantar çorbasında un var mı?",
     "Kremalı Mantar Çorbası gluten içeriyor; içinde un olup olmadığı menümüzde ayrıntılı yazmıyor, kesin bilgi için personelimize sorabilirsiniz.", "honest"),
    ("limonata", "Limonatanın nanesi taze mi kuru mu?",
     "Limonata taze nane yapraklarıyla hazırlanıyor.", "grounded"),
    ("ayran",    "Ayranın tuz oranı yüksek mi?",
     "Yayık Ayran'ın tuz içeriği menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("salgam",   "Şalgamda gerçek şalgam mı kullanılıyor?",
     "Şalgam Suyu'nun üretim ayrıntıları menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("kofte",    "Köftede ekmek içi kullanılıyor mu?",
     "Izgara Köfte gluten içeriyor; ekmek içi olup olmadığı menümüzde ayrıntılı belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("salata",   "Salatanın domatesi kiraz domates mi?",
     "Izgara Tavuk Salata domatesle hazırlanıyor ancak domates türü menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("doner",    "Dönerin etinde yağ oranı yüksek mi?",
     "Et Döner'in yağ oranı menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("mercimek", "Çorbadaki havuç doğranmış mı ezilmiş mi?",
     "Mercimek Çorbası havuçla hazırlanıyor; havucun hazırlanış şekli menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("kunefe",   "Künefenin kadayıfı el açması mı?",
     "Künefe ince tel kadayıfla yapılıyor ancak hazırlanış detayı menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("sutlac",   "Sütlaçta vanilya var mı?",
     "Fırın Sütlaç'ta vanilya kullanılıp kullanılmadığı menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("mantar",   "Mantar çorbası krema ile mi yapılıyor?",
     "Kremalı Mantar Çorbası krema ile hazırlanıyor.", "grounded"),
]

# ── Alt tip 3: porsiyon/pişirme nicel detayı — uydurma YOK (33) ──────────────
S3 = [
    ("doner",    "Et dönerde kaç gram et var?",
     "Et Döner'in gramajı menümüzde yer almıyor, personelimize sorabilirsiniz.", "honest"),
    ("kofte",    "Bir köfte porsiyonunda kaç köfte oluyor?",
     "Izgara Köfte porsiyonundaki adet menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("mercimek", "Mercimek çorbası kaç dakikada pişiyor?",
     "Mercimek Çorbası'nın pişirme süresi hakkında net bilgim yok, personelimize sorabilirsiniz.", "honest"),
    ("mantar",   "Mantar çorbası porsiyonu kaç mililitre?",
     "Kremalı Mantar Çorbası'nın porsiyon ölçüsü menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("salata",   "Tavuk salatada kaç gram tavuk var?",
     "Izgara Tavuk Salata'daki tavuk gramajı menümüzde belirtilmemiş, personelimize danışabilirsiniz.", "honest"),
    ("kunefe",   "Künefe kaç kişilik?",
     "Künefe'nin kaç kişilik olduğu menümüzde yer almıyor, personelimize sorabilirsiniz.", "honest"),
    ("sutlac",   "Sütlaç kaç dakika fırında kalıyor?",
     "Fırın Sütlaç'ın fırın süresi hakkında bilgim yok, personelimize sorabilirsiniz.", "honest"),
    ("ayran",    "Ayran kaç mililitrelik bardakta geliyor?",
     "Yayık Ayran'ın bardak ölçüsü menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("limonata", "Limonata porsiyonu kaç mililitre?",
     "Limonata'nın porsiyon miktarı menümüzde yer almıyor, personelimize danışabilirsiniz.", "honest"),
    ("salgam",   "Şalgam kaç mililitrelik şişede?",
     "Şalgam Suyu'nun ölçüsü hakkında net bilgim yok, personelimize sorabilirsiniz.", "honest"),
    ("doner",    "Döner kaç dakikada hazırlanıyor?",
     "Et Döner'in hazırlanma süresi menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("kofte",    "Köfte toplam kaç gram geliyor?",
     "Izgara Köfte'nin toplam gramajı menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("kunefe",   "Künefe kaç dakikada geliyor?",
     "Künefe'nin hazırlanma süresi hakkında bilgim yok, personelimize sorabilirsiniz.", "honest"),
    ("salata",   "Salata kaç kişilik bir porsiyon?",
     "Izgara Tavuk Salata'nın porsiyon büyüklüğü menümüzde yer almıyor, personelimize danışabilirsiniz.", "honest"),
    ("mercimek", "Mercimek çorbası büyük mü küçük porsiyon mu?",
     "Mercimek Çorbası'nın porsiyon büyüklüğü menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("mantar",   "Mantar çorbası kaç dakikada pişer?",
     "Kremalı Mantar Çorbası'nın pişme süresi hakkında net bilgim yok, personelimize sorabilirsiniz.", "honest"),
    ("sutlac",   "Sütlaçta kaç gram şeker var?",
     "Fırın Sütlaç'ın şeker miktarı menümüzde yer almıyor, personelimize sorabilirsiniz.", "honest"),
    ("doner",    "Dönerde kaç dilim et oluyor?",
     "Et Döner'deki dilim sayısı menümüzde belirtilmemiş, personelimize danışabilirsiniz.", "honest"),
    ("kofte",    "Köfte kaç santimetre büyüklükte?",
     "Izgara Köfte'nin boyutu menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("ayran",    "Ayran kaç dakikada mayalanıyor?",
     "Yayık Ayran'ın hazırlanma süresi hakkında bilgim yok, personelimize sorabilirsiniz.", "honest"),
    ("limonata", "Limonatada kaç adet limon kullanılıyor?",
     "Limonata'da kullanılan limon miktarı menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("salgam",   "Şalgam kaç günde hazırlanıyor?",
     "Şalgam Suyu'nun hazırlanma süresi menümüzde yer almıyor, personelimize sorabilirsiniz.", "honest"),
    ("kunefe",   "Künefede kaç gram peynir var?",
     "Künefe'deki peynir gramajı menümüzde belirtilmemiş, personelimize danışabilirsiniz.", "honest"),
    ("salata",   "Salatada kaç çeşit sebze var?",
     "Izgara Tavuk Salata'daki sebze çeşidi sayısı menümüzde net yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("mercimek", "Çorba kaç derece sıcaklıkta geliyor?",
     "Mercimek Çorbası'nın servis sıcaklığı menümüzde yer almıyor, personelimize sorabilirsiniz.", "honest"),
    ("doner",    "Döner kaç kişilik porsiyon?",
     "Et Döner'in kaç kişilik olduğu menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("kofte",    "Köfte yanındaki patates kaç gram?",
     "Izgara Köfte yanındaki patates gramajı menümüzde yazmıyor, personelimize sorabilirsiniz.", "honest"),
    ("sutlac",   "Sütlaç kaç dakikada soğuyor?",
     "Fırın Sütlaç'ın servis süresi hakkında net bilgim yok, personelimize sorabilirsiniz.", "honest"),
    ("mantar",   "Mantar çorbasında kaç gram mantar var?",
     "Kremalı Mantar Çorbası'ndaki mantar gramajı menümüzde belirtilmemiş, personelimize danışabilirsiniz.", "honest"),
    ("limonata", "Limonata kaç derece soğuklukta servis ediliyor?",
     "Limonata'nın servis sıcaklığı menümüzde yer almıyor, personelimize sorabilirsiniz.", "honest"),
    ("kunefe",   "Künefe kaç dilim geliyor?",
     "Künefe'nin dilim sayısı menümüzde belirtilmemiş, personelimize sorabilirsiniz.", "honest"),
    ("ayran",    "Ayran kaç günlük tazelikte?",
     "Yayık Ayran'ın tazelik süresi hakkında bilgim yok, personelimize sorabilirsiniz.", "honest"),
    ("salgam",   "Şalgamın acılık derecesi kaç?",
     "Şalgam Suyu'nun acılık derecesi menümüzde sayısal olarak yer almıyor, personelimize sorabilirsiniz.", "honest"),
]

ALL = [("s1", *r) for r in S1] + [("s2", *r) for r in S2] + [("s3", *r) for r in S3]

records = []
for subtype, key, question, reply, mode in ALL:
    records.append({
        "messages": [
            {"role": "system",    "content": SYSTEM},
            {"role": "user",      "content": question},
            {"role": "assistant", "content": reply},
        ]
    })

# ── Self-check ──────────────────────────────────────────────────────────────
_HONESTY = ["personel", "bilgim yok"]
for subtype, key, question, reply, mode in ALL:
    name = NAME[key]
    low = reply.lower()

    # (A) UYDURMA nicel detay yasağı — hiçbir rakam yok
    assert not any(ch.isdigit() for ch in reply), f"rakam/uydurma nicel: {reply!r}"

    # (B) yanıt ürünün kanonik adını içerir (grounding çıpası)
    assert name.lower() in low, f"ürün adı yok: {name} — {reply!r}"

    if mode == "honest":
        # (C) dürüstlük/yönlendirme ifadesi
        assert any(h in low for h in _HONESTY), f"dürüstlük ifadesi yok: {reply!r}"
    else:  # grounded — menu.yaml canlı çapraz kontrolü
        # (D) yanıt dürüstlük ifadesine kaçmamalı (gerçek cevabı vermeli)
        assert not any(h in low for h in _HONESTY), f"grounded yanıt yönlendiriyor: {reply!r}"
        # (E) yanıttaki her malzeme sözcüğü menu.yaml'da GEÇMELİ
        allowed = _allowed_text(name)
        for w in FAB_VOCAB:
            if w in low:
                assert w in allowed, (
                    f"UYDURMA malzeme! '{w}' menu.yaml'da yok ({name}): {reply!r}")

# ── BENZERSİZLİK guard'ı (görev #28) — kalıp-tekrarı yakalar ─────────────────
replies = [r for (_, _, _, r, _) in ALL]
questions = [q for (_, _, q, _, _) in ALL]
assert len(set(replies)) == len(replies), (
    f"yanıt tekrarı: {len(replies)-len(set(replies))} mükerrer")
assert len(set(questions)) == len(questions), (
    f"soru tekrarı: {len(questions)-len(set(questions))} mükerrer")

n_grounded = sum(1 for r in ALL if r[4] == "grounded")
n_honest = sum(1 for r in ALL if r[4] == "honest")
print(f"Sistem promptu: {len(SYSTEM)} karakter")
print(f"Toplam: {len(records)} kayıt (S1={len(S1)}, S2={len(S2)}, S3={len(S3)})")
print(f"Mod: grounded={n_grounded}, honest={n_honest}")
print(f"Benzersiz yanıt: {len(set(replies))}/{len(replies)}, benzersiz soru: {len(set(questions))}/{len(questions)}")

out_path = Path("robot_waiter_ai/datasets/processed/wbot_c_anti_hallusinasyon.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"✓ {len(records)} kayıt → {out_path}")
