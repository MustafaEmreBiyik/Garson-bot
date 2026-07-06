"""
scripts/demo_usb.py — W-BOT USB mikrofon + hoparlör demo.

Kullanım:
    python3 scripts/demo_usb.py

Çıkmak için Ctrl+C.

Akış:
    "hey garson" → USB mikrofondan 6 sn kayıt → Whisper STT →
    Qwen3-4B → Piper TTS → USB hoparlörden çal → tekrar

    hey_garson.onnx yoksa otomatik olarak ENTER tuşu moduna geçer.
"""
from __future__ import annotations

import asyncio
import collections
from typing import Any
import io
import logging
import random
import re
import sys
import threading
import wave

import yaml
from pathlib import Path

# ALSA underrun uyarılarını bastır — callback module-level'da tutulmalı (GC koruması)
try:
    import ctypes
    _asound = ctypes.cdll.LoadLibrary("libasound.so.2")
    _ALSA_ERROR_HANDLER = ctypes.CFUNCTYPE(
        None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p
    )
    _alsa_error_handler_ref = _ALSA_ERROR_HANDLER(lambda *_: None)  # GC'den koru
    _asound.snd_lib_error_set_handler(_alsa_error_handler_ref)
except Exception:
    pass

import numpy as np
import sounddevice as sd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("demo_usb")

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

SAMPLE_RATE    = 16_000
CHANNELS       = 1

# VAD kayıt parametreleri
VAD_AGGRESSIVENESS = 3     # webrtcvad sertliği 0-3 (3 = en agresif, gürültülü ortam)
VAD_CHUNK_MS       = 30    # webrtcvad geçerli değerleri: 10, 20, 30
VAD_SILENCE_S      = 1.8   # konuşma bittikten sonra bu kadar sessizlik → kaydı bitir (1.5→1.8: cümle ortasında kesme azalır)
VAD_PRE_ROLL       = 5     # konuşma başlamadan önce tutulacak chunk (5×30ms = 150ms)
VAD_MAX_S          = 12    # güvenlik kapağı — en fazla bu kadar kayıt yap
VAD_ENERGY_THRESH  = 300   # webrtcvad yoksa enerji eşiği (0–32767 arası int16 RMS)
VAD_MIN_SPEECH_MS  = 400   # bu kadardan kısa kayıt STT'ye gönderilmez (gürültü/nefes)
CONVO_HOLD_S       = 60    # bot yanıtından sonra wake word'süz dinleme penceresi (müşteri menüye bakıyor olabilir)

WHISPER_MODEL = "medium"  # Jetson 16GB CUDA — 1.7s latency, small'dan daha iyi Türkçe kalitesi
PIPER_MODEL   = None  # None → otomatik bul

# Whisper'a Türkçe restoran bağlamı ver → menü kelimelerini daha iyi tanır
STT_INITIAL_PROMPT = (
    "Türkçe restoran siparişi. Menü: mercimek çorbası, mantar çorbası, "
    "ızgara köfte, et döner, tavuk salata, sütlaç, künefe, ayran, limonata, şalgam. "
    "Yaygın ifadeler: bir tane, iki tane, porsiyon, ana yemek olarak ne var, "
    "hesabı alabilir miyim, toplam ne kadar, iptal etmek istiyorum."
)

WAKEWORD_MODEL_PATH = (
    Path(__file__).resolve().parent.parent / "robot_waiter_ai" / "models" / "hey_garson.onnx"
)
WAKEWORD_THRESHOLD = 0.90  # 0.85'de TTS echo false positive görüldü — yükseltildi
WAKEWORD_CHUNK     = 1280   # 80 ms @ 16 kHz — openWakeWord beklentisi

# ALSA çıkış cihazı — None → sistem varsayılanı, "plughw:2,0" → Jetson APE jack çıkışı
ALSA_OUTPUT_DEVICE: str | None = "plughw:3,0"  # Jetson USB Audio Device (card 3)

# Cümle sonu tespiti: nokta/ünlem/soru işaretinden sonra boşluk veya newline
_SENT_RE = re.compile(r'(?<=[.!?])[ \t\n]')


_MENU_YAML_PATH = Path(__file__).resolve().parent.parent / "robot_waiter_ai" / "data" / "menu.yaml"

_ORDER_VERBS  = {
    # iste- gövdesi
    "istiyorum", "istiyor", "isterim", "istiyom",
    "istiyoruz", "istiyorlar", "isteriz", "isterler",
    # al- gövdesi
    "alayım", "alabilir", "alalım", "alın", "alıyorum", "alıyoruz", "alınız",
    # getir- gövdesi
    "getir", "getirir", "getirin", "getireyim", "getirelim",
    # diğer
    "lütfen", "ver", "verin",
}
_CANCEL_VERBS = {"istemiyorum", "istemiyom", "iptal", "çıkar", "çıkarın", "kaldır"}
# "başka (bir şey) istemiyorum/istemem" kapanış kalıbıdır, ürün iptali değil —
# cancel tespitinden önce metinden çıkarılır ("Bir de ayran, başka istemiyorum."
# cümlesinde ayranın cancel dalına düşüp hiç eklenmemesini önler)
_CLOSING_NEG_RE = re.compile(r"başka\s+(bir\s*şey\w*\s+)?(de\s+)?istem\w+")
# Sipariş fiili içermeyen ekleme kalıpları (gen_karmasik.py ekle+kapat cümleleri):
# "bir de X", "ayrıca bir X", "son olarak bir X", "bir X daha", "X daha olsun".
# "olsun" tek başına ekleme DEĞİL — "Et Döner soğansız olsun." bir modifikasyon
# isteğidir (S34/V02), ürünü ikinci kez eklememeli; yalnızca "daha" ile birlikte
# ("bir künefe daha olsun") miktar artışı sayılır.
_ADD_MARKERS_RE = re.compile(
    r"\bbir\s?de\b|\bayrıca\b|\bson olarak\b|\bdaha\s+olsun\b|\bbir\s+\w+(\s+\w+){0,2}\s+daha\b"
)
_QUANTITIES   = {"iki": 2, "üç": 3, "dört": 4, "2": 2, "3": 3, "4": 4}
# Guard 1 short-word check'ten muaf tek kelimeler — gerçek intent, VAD hatası değil
_KNOWN_VALID_SINGLE = frozenset({
    "merhaba", "selam", "hey", "günaydın", "iyi",      # selamlar
    "evet", "hayır", "tamam", "peki", "olur", "olmaz",  # onaylar
    "teşekkürler", "teşekkür", "eyvallah", "sağol",     # vedalar
    "hesap",                                             # eylem
})
_DESCRIPTION_TRIGGERS = {"nasıl", "nedir", "ne gibi", "tarif", "anlat", "hakkında"}

_STT_LANG_PROB_MIN   = 0.50   # Guard 1: Whisper dil güven eşiği
_STT_MIN_WORDS_FRESH = 2      # Guard 1: Fresh turn'de ≤ bu kadar kelime → VAD kesimi şüpheli
_VAGUE_TERMS         = {"şey", "şeyler", "birşey", "birşeyler"}
_CONFIRM_STARTS      = {"evet", "hayır", "tabii", "tamam", "olur", "olmaz", "peki", "kesinlikle"}
# Guard 3 (V04/S29) küfür/hakaret listesi — SUBSTRING eşleşir (_is_offensive).
# Genişletme kuralı (C paketi 4-b): yalnızca TEK ANLAMLI kaba/küfür terimleri;
# menü-sipariş sözlüğüyle substring örtüşebilecek sınır kelimeler bilinçli
# DIŞARIDA: "hıyar" (sebze), "adi" ("adisyon" içinde), "sus" ("susam(lı)"
# içinde), "lan"/"ulan" ("olan/planlı" içinde), "mal" ("malzeme/normal"
# içinde — yalnız "mal mısın" kalıbı alındı), "hayvan" ("hayvan gibi
# acıktım" meşru), "rezalet/berbat" (şikâyet dili, S29 değil şikâyet akışı).
_OFFENSIVE_TERMS     = {
    # hakaret — zeka/kişilik
    "salak", "gerizekalı", "geri zekalı", "aptal", "ahmak",
    "mankafa", "embesil", "gerzek", "dangalak", "budala",
    "beyinsiz", "hödük", "avanak", "denyo", "mal mısın",
    "beceriksiz", "işe yaramaz",
    # hakaret — ağır
    "şerefsiz", "piç", "orospu", "kahpe", "kaltak", "sürtük",
    "yavşak", "puşt", "pezevenk", "gavat", "ibne",
    "terbiyesiz", "ahlaksız",
    # küfür — cinsel/argo
    "siktir", "sikerim", "sikeyim", "sikiyor", "sikik",
    "amk", "amına", "amcık", "yarrak", "yarak", "oç", "göt", "bok",
    # kaba emir / kovma
    "defol", "kes sesini", "kapa çeneni", "çeneni kapa",
}


def _load_menu_lookup() -> list[tuple[list[str], str, int]]:
    """(aliases, name, price) listesi döndür."""
    if not _MENU_YAML_PATH.exists():
        return []
    with open(_MENU_YAML_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    result = []
    for item in data.get("menu", []):
        aliases = sorted(
            [a.lower() for a in item.get("aliases", [])] + [item["name"].lower()],
            key=len, reverse=True,
        )
        result.append((aliases, item["name"], item["price"]))
    return result


def _match_items(t: str, lookup: list) -> list[tuple[str, int, int]]:
    """t içindeki menü öğelerini bul; [(name, price, qty)] döndür."""
    matches = []
    for aliases, name, price in lookup:
        for alias in aliases:
            if alias not in t:
                continue
            # Alias'dan önce gelen 1-2 kelimeye bak — miktar olabilir
            # "iki köfte" → 1 kelime; "iki tane köfte" → 2 kelime
            m1 = re.search(r'(\w+)\s+' + re.escape(alias), t)
            m2 = re.search(r'(\w+)\s+\w+\s+' + re.escape(alias), t)
            qty = 1
            if m1:
                qty = _QUANTITIES.get(m1.group(1), 1)
            if qty == 1 and m2:
                qty = _QUANTITIES.get(m2.group(1), 1)
            matches.append((name, price, qty))
            break  # Bu ürün için ilk eşleşen alias yeterli
    return matches


class OrderTracker:
    """Kullanıcı metninden menü ürünü tespit eder, siparişi yapısal tutar."""

    def __init__(self) -> None:
        self._items: dict[str, dict] = {}  # name → {"price": int, "qty": int}
        self._lookup = _load_menu_lookup()

    def _add_item(self, name: str, price: int, qty: int) -> None:
        if name in self._items:
            self._items[name]["qty"] += qty
        else:
            self._items[name] = {"price": price, "qty": qty}

    def _remove_item(self, name: str, price: int, qty: int) -> None:
        if name not in self._items:
            return
        self._items[name]["qty"] = max(0, self._items[name]["qty"] - qty)
        if self._items[name]["qty"] == 0:
            del self._items[name]

    def detect_order(self, user_text: str) -> None:
        """Sipariş/iptal/takas niyetini tespit et ve sepeti güncelle.

        Dört durum:
          - "X yerine Y": X'i çıkar, Y'yi ekle.
          - "X iptal / X istemiyorum": X'i çıkar.
          - "X alayım / Y istiyorum": X'i ekle.
          - "Bir de X, başka istemiyorum": X'i ekle (ekle+kapat —
            "başka istemiyorum" kapanış kalıbıdır, X'in iptali değil).
        """
        # "İ".lower() → "i̇" (birleştirme noktası) → regex kopar; temizle
        t = user_text.lower().replace('̇', '')
        # Kapanış kalıbını çıkar — kalıptaki "istemiyorum" iptal sayılmasın
        t = _CLOSING_NEG_RE.sub(" ", t)

        is_cancel = any(v in t for v in _CANCEL_VERBS)
        is_swap   = "yerine" in t or "değiştir" in t

        if is_swap:
            if "yerine" in t:
                before, after = t.split("yerine", 1)
                remove_matches = _match_items(before, self._lookup)
                add_matches    = _match_items(after, self._lookup)
            else:
                # "X, Y ile değiştir" → content önce "ile"ye kadar, X=ilk, Y=son ürün
                content = t[:t.rfind(" ile ")] if " ile " in t else t.replace("değiştir", "")
                all_m = _match_items(content, self._lookup)
                if len(all_m) >= 2:
                    remove_matches = [all_m[0]]
                    add_matches    = [all_m[-1]]
                else:
                    remove_matches, add_matches = [], all_m
            for name, price, qty in remove_matches:
                self._remove_item(name, price, qty)
            for name, price, qty in add_matches:
                self._add_item(name, price, qty)
            return

        if is_cancel:
            all_qty = any(w in t for w in {"hepsini", "hepsi", "tümünü", "tamamını"})
            for name, price, qty in _match_items(t, self._lookup):
                if all_qty:
                    self._items.pop(name, None)
                else:
                    self._remove_item(name, price, qty)
            return

        # Sipariş fiili YOKSA ekleme kalıbı da ("bir de X", "bir X daha"...) ekleme sayılır
        if not any(v in t for v in _ORDER_VERBS) and not _ADD_MARKERS_RE.search(t):
            return
        polite_mod = _is_polite_modification(t)
        for name, price, qty in _match_items(t, self._lookup):
            if polite_mod and name in self._items:
                continue  # "Köfte acısız olsun lütfen" — mevcut ürünün modifikasyonu, ikileme yok
            self._add_item(name, price, qty)

    @property
    def items(self) -> list[tuple[str, int, int]]:
        """Aktif siparişler: [(name, price, qty)]."""
        return [(name, d["price"], d["qty"]) for name, d in self._items.items()]

    @property
    def total(self) -> int:
        return sum(d["price"] * d["qty"] for d in self._items.values())

    def reset(self) -> None:
        self._items = {}


_BILL_KEYWORDS = ["hesab", "hesap", "ödeyeyim", "ödüyorum", "parayı öde",
                  "toplam", "tutar", "ne kadar tut", "kaç tl", "kaç lira"]


def _is_bill_request(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in _BILL_KEYWORDS)


def _is_description_question(user_text: str, lookup: list) -> bool:
    """Kullanıcı menüdeki bir ürün hakkında açıklama soruyor mu? (E19 fix)"""
    t = user_text.lower().replace('̇', '')
    if not any(w in t for w in _DESCRIPTION_TRIGGERS):
        return False
    for aliases, _, _ in lookup:
        for alias in aliases:
            if alias in t:
                return True
    return False


# --- V01: modifikasyon onayında TL fiyat enjeksiyonu (S33, C paketi) ---
# Sipariş + modifikasyon aynı cümlede ("Bir şalgam alayım, acılı olsun.")
# geldiğinde onay yanıtı ürünün TL fiyatını içermeli; ham model bunu bazen
# atlıyor (V01). Hesap toplamı override'ı ve E19 ekleme mekanizmasıyla aynı
# desen: LLM yanıtı üretildikten SONRA post-processing katmanında çalışır,
# Guard 1/2/3 → detect_order → S12 → fast-path sıralamasına dokunmaz.
# "X olsun" burada modifikasyon SİNYALİdir, ekleme değil (görev #21) — sepet
# yalnızca OKUNUR; added_items main loop'taki detect_order deltasından gelir,
# ürün ikinci kez eklenmez. S34 (ürün önceki turda alınmış, yalnızca not
# değişiyor) turlarında delta boş kalır → enjeksiyon tetiklenmez (tasarım
# gereği: modifikasyon güncellemesinde yeni fiyat söylenmez).
_MODIFICATION_TERMS = {
    "soğansız", "soğanlı", "acılı", "acısız", "pişmiş",
    "buzsuz", "buzlu", "şekersiz", "şekerli", "tuzsuz", "tuzlu",
    "sossuz", "soslu", "sarımsaksız", "sarımsaklı", "limonsuz",
    "naneli", "nanesiz", "ketçapsız", "mayonezsiz",
}
_MOD_OLSUN_RE = re.compile(r"\bolsun\b")


def _has_modification_request(user_text: str) -> bool:
    """Cümlede modifikasyon sinyali var mı? ("soğansız", "acılı", "X olsun"...)"""
    t = user_text.lower().replace('̇', '')
    return any(term in t for term in _MODIFICATION_TERMS) or bool(_MOD_OLSUN_RE.search(t))


def _is_polite_modification(user_text_lower: str) -> bool:
    """Görev #25 yan bulgu (b): "Köfte acısız olsun lütfen" tarzı cümleler
    ekleme değildir — tek sipariş tetikleyicisi "lütfen" ve cümlede
    modifikasyon sinyali var ("olsun ekleme değildir" kararının devamı,
    görev #21). detect_order() bu durumda SEPETTE ZATEN OLAN ürünü ikilemez;
    ürün sepette yoksa yine eklenir ("Bir köfte lütfen, acısız olsun" gibi
    modifikasyonlu YENİ sipariş bozulmaz).

    user_text_lower: lower() + i̇-fix uygulanmış metin (detect_order içindeki t).
    """
    verbs = {v for v in _ORDER_VERBS if v in user_text_lower}
    if verbs != {"lütfen"}:
        return False
    if _ADD_MARKERS_RE.search(user_text_lower):  # "bir X daha ... lütfen" miktar artışıdır
        return False
    return _has_modification_request(user_text_lower)


def _modification_price_addition(user_text: str, reply: str,
                                 added_items: list[tuple[str, int, int]]) -> str | None:
    """V01: bu turda eklenen ürün + modifikasyon sinyali varsa ve LLM yanıtı
    ürünün TL fiyatını içermiyorsa söylenecek fiyat cümlesini döndür.

    added_items: bu turda sepete EKLENEN ürünler [(name, unit_price, added_qty)]
    — detect_order() öncesi/sonrası sepet farkı. Gerekmiyorsa None.
    """
    if not added_items:
        return None
    if not _has_modification_request(user_text):
        return None
    parts = []
    for name, price, qty in added_items:
        line_total = price * qty
        # Fiyat zaten söylendiyse (birim veya satır toplamı) tekrarlanmaz.
        # \b sınırı "150" içindeki "50"ye yanlış eşleşmeyi önler.
        if re.search(rf"\b{price}\b", reply) or re.search(rf"\b{line_total}\b", reply):
            continue
        parts.append(f"{qty} {name} {line_total} TL" if qty > 1 else f"{name} {price} TL")
    if not parts:
        return None
    return ", ".join(parts) + "."


def _stt_low_confidence(result: dict, text: str, *, in_convo: bool) -> bool:
    """Guard 1: STT güvensizse True döndür.

    (a) language_probability eşiğin altındaysa — Whisper Türkçe'den emin değil.
    (b) Fresh turn (in_convo=False) VE çok kısa metin — VAD erken kesti.
    (c) Unique kelime oranı < %15 — Whisper hallüsinasyon döngüsü ("al, al, al...").
    Conversation hold'da kelime sayısı koşulu uygulanmaz: "evet", "tamam" geçerli.
    """
    lang_prob = result.get("language_probability", 1.0)
    if lang_prob < _STT_LANG_PROB_MIN:
        return True
    words = text.split()
    if len(words) >= 3:
        unique_ratio = len(set(words)) / len(words)
        # Tekrar döngüsü: az unique kelime (al,al,al...) VEYA tek kelime 3+ kez
        if unique_ratio < 0.15 or (len(set(words)) == 1 and len(words) >= 3):
            return True
    if not in_convo and len(words) <= _STT_MIN_WORDS_FRESH:
        t_clean = text.lower().replace('̇', '').strip()
        if t_clean not in _KNOWN_VALID_SINGLE:
            return True
    return False


def _is_off_menu_order(text: str, lookup: list, *, in_convo: bool) -> bool:
    """Guard 2: Sipariş fiili var ama menü eşleşmiyorsa True döndür.

    Tüm koşullar aynı anda doğru olmalı:
      1. _ORDER_VERBS metinde var
      2. _match_items() boş döndü
      3. _VAGUE_TERMS yok ("birşey istiyorum" → LLM'e bırak)
      4. İlk kelime _CONFIRM_STARTS'ta değil ("evet, alayım" → LLM'e bırak)
      5. Fiil/miktar/stopword çıktıktan sonra en az 1 içerik kelimesi kalıyor
    """
    t = text.lower().replace('̇', '')
    # Kelime sınırı ile eşleştir — "verdim" içindeki "ver" substring'i tetiklemesin
    if not any(re.search(r'\b' + re.escape(v) + r'\b', t) for v in _ORDER_VERBS):
        return False
    if _match_items(t, lookup):
        return False
    if any(vague in t for vague in _VAGUE_TERMS):
        return False
    words = t.split()
    if not words or words[0] in _CONFIRM_STARTS:
        return False
    _STOPWORDS = {"bir", "de", "da", "ile", "ve", "mi", "mı", "mu", "mü",
                  "lütfen", "acaba", "bana", "bize", "buraya",
                  "sipariş", "siparişi", "siparişim", "siparişimi",
                  "bitirmek", "bitir", "bitsin", "tamamlamak", "tamamla",
                  "kapatmak", "kapat", "yeter", "bırak", "bırakın"}
    noise = _ORDER_VERBS | set(_QUANTITIES.keys()) | _STOPWORDS
    content_words = [w for w in words if w not in noise]
    return len(content_words) >= 1


def _is_offensive(text: str) -> bool:
    """Guard 3: Hakaret veya küfür içeriyorsa True döndür."""
    t = text.lower().replace('̇', '')
    return any(term in t for term in _OFFENSIVE_TERMS)


_FAREWELL_TRIGGERS = {
    "güle güle", "görüşürüz", "hoşça kal", "elveda",
    "teşekkürler", "teşekkür ederim", "teşekkür", "sağ olun", "sağ ol",
    "iyi günler", "iyi akşamlar", "iyi geceler",
    "eyvallah", "sağlıcakla", "kolay gelsin",
}
_FAREWELL_TEMPLATES = [
    "Güle güle! Tekrar bekleriz.",
    "Teşekkürler, iyi günler! Tekrar görüşmek üzere.",
    "Kolay gelsin, tekrar bekleriz!",
]

# Selam / açılış — müşteri konuşmayı başlatıyor
_GREETING_TRIGGERS = {"merhaba", "selam", "hey", "iyi günler", "iyi akşamlar", "günaydın"}
_GREETING_TEMPLATES = [
    "Merhaba! Nasıl yardımcı olabilirim?",
    "Hoş geldiniz! Siparişinizi alabilir miyim?",
    "Merhaba, buyurun!",
]

# Onay / teşekkür — müşteri sadece onay veriyor
_CONFIRM_PHRASES = {"evet", "tamam", "olur", "peki", "anladım", "tamamdır", "süper", "harika", "güzel"}
_CONFIRM_TEMPLATES = [
    "Tabii efendim. Başka bir isteğiniz var mı?",
    "Anlıyorum. Başka bir şey alır mısınız?",
    "Peki efendim. Başka?",
]

# --- S12/E24 kapanış guard'ı (görev #22) — deterministik, LLM'e sorulmaz ---
# TUR 1: kapanış sinyali + dolu sepet → özet + toplam + onay sorusu.
# TUR 2: onay bekleniyorken onay kelimesi → toplamsız sabit kapanış.
# Hesap toplamı override'ıyla aynı güven düzeyi; model S12'yi eğitilmiş
# kalıpta bile atlıyor (4 Temmuz 2026 manuel test), bu yüzden kod katmanı.
_CLOSING_TRIGGERS = {
    "bu kadar", "o kadar yeter", "yeter artık", "yeterli",
    "hepsi bu", "başka bir şey yok", "başka yok",
}
_S12_CONFIRM_WORDS = {"evet", "tamam", "tamamdır", "olur", "tabii", "peki", "onaylıyorum", "aynen"}
_S12_REJECT_HINTS  = {"hayır", "olmaz", "iptal", "istemiyorum", "değil", "yanlış", "eksik", "dur", "bekle"}
_S12_CLOSING_REPLY = "Afiyet olsun!"


def _is_closing_signal(text: str) -> bool:
    """Kapanış kalıbı var mı? Ürün eşleşmesi YÜRÜTMEZ — bu fonksiyon
    çağrılmadan önce detect_order() çalışmış, order_tracker.items güncellenmiş
    olmalı (ilk guard taslağındaki ürün-eşleşme mantık hatasının düzeltilmiş hali).

    Saf veda ("Teşekkürler.") da kapanış sayılır — S12 koşulsuz özet kararı:
    dolu sepet özet+toplam+onay duyulmadan kapanmamalı (loglama/hukuki koruma,
    görev #12, açısından da gerekli). Sepet boşken TUR 1 koşulu zaten
    tetiklenmez, veda normal fast-path'e düşer.
    """
    t = text.lower().replace('̇', '')
    if _CLOSING_NEG_RE.search(t):  # "başka (bir şey) istemiyorum/istemem"
        return True
    if any(fw in t for fw in _FAREWELL_TRIGGERS):
        return True
    return any(trigger in t for trigger in _CLOSING_TRIGGERS)


def _is_order_confirmation(text: str) -> bool:
    """TUR 2: kullanıcı sipariş özetini onaylıyor mu?

    Kısa (≤3 kelime), onay kelimesiyle başlayan ve ret iması içermeyen
    yanıt onay sayılır; gerisi normal akışa düşer. "Evet, başka istemiyorum."
    da onaydır — kapanış kalıbı ret iması sayılmadan önce metinden çıkarılır.
    """
    t = text.lower().replace('̇', '')
    t = _CLOSING_NEG_RE.sub(" ", t)
    if any(r in t for r in _S12_REJECT_HINTS):
        return False
    words = [w.strip(".,!?") for w in t.split()]
    words = [w for w in words if w]
    if not words or len(words) > 3:
        return False
    return words[0] in _S12_CONFIRM_WORDS


def _closing_summary(items: list, total: int) -> str:
    """TUR 1 yanıtı: özet + toplam + onay sorusu (S12 koşulsuz özet kararı)."""
    parts = ", ".join(f"{qty} {name}" for name, _price, qty in items)
    return f"Siparişinizi özetliyorum: {parts}. Toplam {total} TL. Onaylıyor musunuz?"


# "İyi günler"/"iyi akşamlar" hem _FAREWELL_TRIGGERS hem _GREETING_TRIGGERS
# üyesi — bağlamsız çözülemez (görev #25 yan bulgu a)
_AMBIGUOUS_SALUTATIONS = _FAREWELL_TRIGGERS & _GREETING_TRIGGERS


def _salutation_intent(text: str, in_convo: bool) -> str | None:
    """Selam mı veda mı? "greeting" / "farewell" / None döndürür (görev #25 a).

    Çift anlamlı kalıplar ("iyi günler", "iyi akşamlar") oturum bağlamıyla
    ayrışır: taze açılışta (in_convo=False) selam, yerleşik konuşmada veda.
    Tek anlamlı vedalar ("görüşürüz", "güle güle"...) her bağlamda vedadır —
    "İyi günler, görüşürüz" açılışta bile veda kalır.
    """
    t = text.lower().strip().replace('̇', '')
    farewell_hits = {fw for fw in _FAREWELL_TRIGGERS if fw in t}
    if farewell_hits - _AMBIGUOUS_SALUTATIONS:
        return "farewell"
    if farewell_hits:  # yalnızca çift anlamlı kalıp eşleşti
        return "greeting" if not in_convo else "farewell"
    if len(t.split()) <= 2 and any(g in t for g in _GREETING_TRIGGERS):
        return "greeting"
    return None


def _fast_path_reply(text: str, in_convo: bool = False) -> str | None:
    """Veda/selam/onay intentleri için LLM'i atlayıp şablon yanıt döndür.

    Yalnızca kısa (≤5 kelime) ve tek intent içeren girişlerde tetiklenir.
    Sipariş fiili, menü kelimesi veya soru işareti varsa LLM'e bırakılır.
    in_convo: "iyi günler" gibi çift anlamlı kalıpların selam/veda ayrımı
    oturum bağlamına göre yapılır (görev #25 a).
    """
    t = text.lower().strip().replace('̇', '')
    words = t.split()
    if len(words) > 5:
        return None
    if any(v in t for v in _ORDER_VERBS):
        return None
    if "?" in t:
        return None

    intent = _salutation_intent(text, in_convo)
    if intent == "farewell":
        return random.choice(_FAREWELL_TEMPLATES)
    if intent == "greeting":
        return random.choice(_GREETING_TEMPLATES)

    # Tek kelime onay — sepet boş değilse veya sohbet aktifse anlamlı
    if len(words) == 1 and words[0] in _CONFIRM_PHRASES:
        return random.choice(_CONFIRM_TEMPLATES)

    return None


def _greet() -> str:
    """Karşılama cümlesi — wake word ve ROS 'geldim' sinyali için tek nokta."""
    return "Merhaba, hoş geldiniz! Ben W-BOT. Nasıl yardımcı olabilirim?"


def _find_input_device() -> int | None:
    """USB ses giriş cihazının sounddevice index'ini döndür, bulamazsa None.

    "USB PnP" / "PnP Sound" cihazını önceliklendir — Jetson'da bu genellikle
    gerçek mikrofondur; USB Audio Device ise hoparlör+mikrofon adapttörü olup
    giriş kalitesi daha düşük olabilir.
    """
    devices = list(enumerate(sd.query_devices()))
    # Önce USB PnP / standalone mic ara
    for i, d in devices:
        if "USB" in d["name"] and "PnP" in d["name"] and d["max_input_channels"] > 0:
            return i
    # Bulamazsa ilk USB giriş cihazına dön
    for i, d in devices:
        if "USB" in d["name"] and d["max_input_channels"] > 0:
            return i
    return None


def _find_output_device() -> str | None:
    """USB hoparlörün ALSA cihaz string'ini ('plughw:X,Y') döndür.

    sounddevice cihaz isimlerindeki '(hw:KART,CİHAZ)' ifadesini ayrıştırır.
    "USB Audio" içeren ama "PnP" içermeyen (= hoparlör) ve çıkış kanalı olan
    cihazı bulur. Kart numarası replug/boot'ta değişse de isim sabit kalır.
    Bulamazsa None (ALSA_OUTPUT_DEVICE sabiti fallback olarak kalır).
    """
    for d in sd.query_devices():
        name = d["name"]
        if "USB Audio" in name and "PnP" not in name and d["max_output_channels"] > 0:
            m = re.search(r"hw:(\d+),(\d+)", name)
            if m:
                return f"plughw:{m.group(1)},{m.group(2)}"
    return None


class _OpenAIWhisperSTT:
    """openai-whisper CPU fallback — faster-whisper/CTranslate2 SGEMM yoksa kullan."""

    def __init__(self, model_size: str = "small") -> None:
        import whisper as _ow
        print(f"  STT: openai-whisper '{model_size}' yükleniyor (CPU)...")
        self._model = _ow.load_model(model_size)

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        language: str = "tr",
        initial_prompt: str | None = None,
        use_vad: bool = True,
    ) -> dict:
        import os as _os, tempfile as _tmp
        if not audio_bytes:
            return {"text": "", "segments": [], "language": language,
                    "language_probability": 0.0, "low_confidence": True}
        fd, tmp = _tmp.mkstemp(suffix=".wav")
        _os.close(fd)
        try:
            Path(tmp).write_bytes(audio_bytes)
            kw: dict = {"language": language, "fp16": False}
            if initial_prompt:
                kw["initial_prompt"] = initial_prompt
            result = await asyncio.to_thread(self._model.transcribe, tmp, **kw)
        finally:
            try:
                _os.unlink(tmp)
            except OSError:
                pass
        return {
            "text": result.get("text", ""),
            "segments": [{"start": s["start"], "end": s["end"], "text": s["text"]}
                         for s in result.get("segments", [])],
            "language": result.get("language", language),
            "language_probability": 1.0,
            "low_confidence": False,
        }


# ---------------------------------------------------------------------------
# Ses yardımcıları
# ---------------------------------------------------------------------------

def _numpy_to_wav(audio: np.ndarray, rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(audio.astype(np.int16).tobytes())
    return buf.getvalue()


def _play_wav(wav_bytes: bytes) -> None:
    import os, subprocess, tempfile
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        Path(tmp).write_bytes(wav_bytes)
        cmd = ["aplay", "-q"]
        if ALSA_OUTPUT_DEVICE:
            cmd += ["-D", ALSA_OUTPUT_DEVICE]
        cmd.append(tmp)
        subprocess.run(cmd, check=True)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _play_mp3(mp3_bytes: bytes) -> None:
    import os, subprocess, tempfile
    fd, tmp = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        Path(tmp).write_bytes(mp3_bytes)
        subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp],
                       check=True)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


async def _speak(tts, text: str, tts_active: threading.Event | None = None) -> None:
    """TTS ile seslendir. tts_active set iken wake word algılaması durur."""
    if tts_active is not None:
        tts_active.set()
    try:
        audio_bytes  = await tts.synthesize(text)
        content_type = getattr(tts, "AUDIO_CONTENT_TYPE", "audio/wav")
        if "wav" in content_type:
            await asyncio.to_thread(_play_wav, audio_bytes)
        else:
            await asyncio.to_thread(_play_mp3, audio_bytes)
    finally:
        if tts_active is not None:
            tts_active.clear()


async def _speak_streaming(tts, llm, user_text: str,
                            tts_active: "threading.Event | None" = None) -> str:
    """LLM token akışını cümle cümle TTS'e ver; ilk sesi hızla başlat.

    Pipeline: LLM thread → sentence_q → tts_worker → audio_q → play_worker
    tts_worker ve play_worker eş zamanlı çalışır: biri sentezlerken diğeri çalar.
    """
    loop = asyncio.get_event_loop()
    sentence_q: asyncio.Queue = asyncio.Queue()
    audio_q: asyncio.Queue = asyncio.Queue(maxsize=2)
    spoken: list[str] = []

    def _run_llm():
        buf = ""
        try:
            for token in llm.stream_reply(user_text):
                buf += token
                while True:
                    m = _SENT_RE.search(buf)
                    if not m:
                        break
                    sentence = buf[:m.start()].strip()
                    buf = buf[m.end():]
                    if sentence:
                        loop.call_soon_threadsafe(sentence_q.put_nowait, sentence)
        except Exception as exc:
            logger.error("LLM stream hatası: %s", exc)
        finally:
            if buf.strip():
                loop.call_soon_threadsafe(sentence_q.put_nowait, buf.strip())
            loop.call_soon_threadsafe(sentence_q.put_nowait, None)

    async def _tts_worker():
        ctype = getattr(tts, "AUDIO_CONTENT_TYPE", "audio/wav")
        while True:
            sentence = await sentence_q.get()
            if sentence is None:
                await audio_q.put(None)
                break
            spoken.append(sentence)
            clean = re.sub(r'\*+', '', sentence).strip()
            if not clean:
                continue
            wav = await tts.synthesize(clean)
            await audio_q.put((wav, ctype))

    async def _play_worker():
        while True:
            item = await audio_q.get()
            if item is None:
                break
            wav, ctype = item
            if "wav" in ctype:
                await asyncio.to_thread(_play_wav, wav)
            else:
                await asyncio.to_thread(_play_mp3, wav)

    if tts_active is not None:
        tts_active.set()
    llm_thread = threading.Thread(target=_run_llm, daemon=True)
    llm_thread.start()
    try:
        await asyncio.gather(_tts_worker(), _play_worker())
    finally:
        if tts_active is not None:
            tts_active.clear()
        llm_thread.join(timeout=5)

    return " ".join(spoken)


def _beep() -> None:
    """Kısa onay bip tonu — wake word algılandığında çal."""
    t = np.linspace(0, 0.15, int(SAMPLE_RATE * 0.15), dtype=np.float32)
    tone = (np.sin(2 * np.pi * 880 * t) * 0.3).astype(np.float32)
    sd.play(tone, samplerate=SAMPLE_RATE)
    sd.wait()


def _resample_to_16k(audio: np.ndarray, from_sr: int) -> np.ndarray:
    """audio'yu from_sr'den SAMPLE_RATE'e düşür — numpy lineer interpolasyon."""
    if from_sr == SAMPLE_RATE:
        return audio
    target_len = int(len(audio) * SAMPLE_RATE / from_sr)
    return np.interp(
        np.linspace(0, len(audio) - 1, target_len),
        np.arange(len(audio)),
        audio.astype(np.float32),
    ).astype(np.int16)


def _record(input_device: int | None = None, *,
            initial_wait_s: float | None = None) -> bytes:
    """VAD tabanlı kayıt — sessizlik sonrası durur, maks VAD_MAX_S saniye.

    webrtcvad kuruluysa kullanır; yoksa enerji eşiğine döner.

    initial_wait_s: konuşma başlamadan beklenecek max süre. None ise VAD_MAX_S
    (mevcut davranış). Süre dolduğunda konuşma başlamadıysa boş bytes (b"")
    döndürülür — çağıran "kullanıcı konuşmadı" diye anlayabilir.
    """
    CHUNK_SAMPLES = SAMPLE_RATE * VAD_CHUNK_MS // 1000  # 16000*30//1000 = 480

    # webrtcvad veya enerji tabanlı fallback
    try:
        import webrtcvad as _wvad
        _v = _wvad.Vad(VAD_AGGRESSIVENESS)
        def _is_speech(pcm: bytes) -> bool:
            try:
                return _v.is_speech(pcm, SAMPLE_RATE)
            except Exception:
                return False
    except ImportError:
        def _is_speech(pcm: bytes) -> bool:
            arr = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
            return float(np.sqrt(np.mean(arr ** 2))) > VAD_ENERGY_THRESH

    # Native sample rate (USB mikler genelde 48 kHz)
    if input_device is not None:
        native_sr = int(sd.query_devices(input_device)["default_samplerate"])
    else:
        native_sr = SAMPLE_RATE
    native_chunk = int(native_sr * VAD_CHUNK_MS / 1000)

    silence_limit = int(VAD_SILENCE_S * 1000 / VAD_CHUNK_MS)
    max_chunks    = int(VAD_MAX_S    * 1000 / VAD_CHUNK_MS)
    # Konuşma başlamadan beklenecek max chunk; initial_wait_s verilmediyse max_chunks
    initial_max  = int(initial_wait_s * 1000 / VAD_CHUNK_MS) if initial_wait_s else max_chunks

    ring_buf    = collections.deque(maxlen=VAD_PRE_ROLL)
    voiced_16k: list[bytes] = []
    in_speech   = False
    silence_cnt = 0
    total       = 0

    print("  🎙  Dinliyorum...", flush=True)

    with sd.InputStream(samplerate=native_sr, channels=CHANNELS,
                        dtype="int16", blocksize=native_chunk,
                        device=input_device) as stream:
        while total < max_chunks:
            indata, _ = stream.read(native_chunk)
            total += 1
            chunk = indata[:, 0] if indata.ndim > 1 else indata.flatten()

            # 16 kHz'e dönüştür
            if native_sr != SAMPLE_RATE:
                chunk = _resample_to_16k(chunk, native_sr)

            # webrtcvad tam boyut ister — kırp ya da pad uygula
            if len(chunk) > CHUNK_SAMPLES:
                chunk = chunk[:CHUNK_SAMPLES]
            elif len(chunk) < CHUNK_SAMPLES:
                chunk = np.pad(chunk, (0, CHUNK_SAMPLES - len(chunk)))

            pcm    = chunk.astype(np.int16).tobytes()
            speech = _is_speech(pcm)

            if not in_speech:
                ring_buf.append(pcm)
                if speech:
                    in_speech = True
                    voiced_16k.extend(ring_buf)
                    ring_buf.clear()
                    silence_cnt = 0
                elif total >= initial_max:
                    # Konuşma başlamadan timeout — çağıran sessizlik diye anlasın
                    break
            else:
                voiced_16k.append(pcm)
                if speech:
                    silence_cnt = 0
                else:
                    silence_cnt += 1
                    if silence_cnt >= silence_limit:
                        elapsed = total * VAD_CHUNK_MS / 1000
                        print(f"  ✓  Alındı ({elapsed:.1f}s)", flush=True)
                        break

    if not voiced_16k:
        return b""  # konuşma yoktu — çağıran "sessizlik / timeout" diye değerlendirir

    # Çok kısa kayıtları (gürültü/nefes/kazara gürültü) STT'ye gönderme
    if len(voiced_16k) * VAD_CHUNK_MS < VAD_MIN_SPEECH_MS:
        return b""

    audio = np.frombuffer(b"".join(voiced_16k), dtype=np.int16)
    return _numpy_to_wav(audio, SAMPLE_RATE)


# ---------------------------------------------------------------------------
# Wake word
# ---------------------------------------------------------------------------

def _load_wakeword():
    """hey_garson.onnx modelini yükle. Hata varsa None döner."""
    if not WAKEWORD_MODEL_PATH.exists():
        return None
    try:
        oww_dir = str(Path(__file__).resolve().parent.parent / "openWakeWord")
        if oww_dir not in sys.path:
            sys.path.insert(0, oww_dir)
        from openwakeword.model import Model
        m = Model(wakeword_models=[str(WAKEWORD_MODEL_PATH)], inference_framework="onnx")
        logger.info("Wake word modeli yüklendi.")
        return m
    except Exception as e:
        logger.warning("Wake word modeli yüklenemedi: %s", e)
        return None


async def _detect_wakeword(ww_model, tts_active: threading.Event,
                           input_device: int | None = None) -> None:
    """'hey garson' algılanana kadar mikrofonu dinle (tek kullanımlık coroutine)."""
    loop     = asyncio.get_event_loop()
    detected = asyncio.Event()

    # USB mikler genelde 48kHz native — 16kHz'i reddedebilirler
    if input_device is not None:
        native_sr = int(sd.query_devices(input_device)["default_samplerate"])
    else:
        native_sr = SAMPLE_RATE
    native_chunk = int(native_sr * WAKEWORD_CHUNK / SAMPLE_RATE)

    # Stream açılırken buffer'da kalan ses kalıntısı ilk chunk'larda false positive yapar;
    # 25 chunk (25×80ms = 2000ms) atla — TTS echo odada ~1-2s sürebilir.
    _warm_up = [25]

    def _cb(indata, frames, time_info, status):
        if _warm_up[0] > 0:
            _warm_up[0] -= 1
            return
        if tts_active.is_set():
            return  # TTS çalarken tetikleme yapma (feedback engeli)
        if detected.is_set():
            return
        audio = (indata[:, 0] * 32768).astype(np.int16)
        if native_sr != SAMPLE_RATE:
            audio = _resample_to_16k(audio, native_sr)
        scores = ww_model.predict(audio)
        score  = float(list(scores.values())[0])
        if score > WAKEWORD_THRESHOLD:
            loop.call_soon_threadsafe(detected.set)

    with sd.InputStream(samplerate=native_sr, channels=1, dtype="float32",
                        blocksize=native_chunk, callback=_cb,
                        device=input_device):
        await detected.wait()


# ---------------------------------------------------------------------------
# Ana döngü
# ---------------------------------------------------------------------------

async def run_demo(adapter_dir: str | None = None) -> None:
    print("\n" + "=" * 55)
    print("  W-BOT USB Demo  —  Ctrl+C ile çıkış")
    print("=" * 55)
    print("\nModeller yükleniyor, lütfen bekleyin...\n")

    from robot_waiter_ai.speech.stt import SpeechToText
    from robot_waiter_ai.speech.tts import PiperTTS

    # TTS
    try:
        tts = PiperTTS(model=PIPER_MODEL)
        print("TTS: Piper (offline)")
    except RuntimeError:
        from robot_waiter_ai.speech.tts import TextToSpeech
        tts = TextToSpeech()
        print("TTS: edge-tts (fallback, internet gerekli)")

    # LLM — llama-cpp-python (Jetson/GGUF) önce dene, yoksa transformers (PC)
    try:
        from robot_waiter_ai.inference.llama_cpp_backend import LlamaCppBackend
        llm = LlamaCppBackend()
        print("LLM: llama-cpp-python GGUF (GPU)")
    except Exception as _llama_err:
        from robot_waiter_ai.inference.qwen3_backend import Qwen3Backend
        llm = Qwen3Backend(adapter_dir=adapter_dir)
        label = f"Qwen3Backend + adapter ({adapter_dir})" if adapter_dir else "Qwen3Backend (base)"
        print(f"LLM: {label}")

    # KV cache ön ısıtma — sistem promptu (944 tok) bir kez işle, tüm müşterilerin
    # ilk turn'ü soğuk start yerine sıcak (~0.25s TTFT) olsun.
    print("LLM KV cache ısıtılıyor…")
    await asyncio.to_thread(llm.generate_reply, "Merhaba.")
    llm.reset_history()
    try:
        import torch as _torch
        if _torch.cuda.is_available():
            _torch.cuda.empty_cache()
    except Exception:
        pass
    print("LLM: KV cache hazır")

    # STT cihaz seçimi — LLM ile aynı GPU'da çakışmasını önler.
    #   * Total VRAM < 8 GB ise CUDA'da Qwen3-4B + Whisper birlikte sığmaz (OOM)
    #     → CPU int8. Bu host (RTX 4050 6 GB) bu kategoride.
    #   * Total VRAM ≥ 8 GB (örn. Jetson Orin NX 16 GB) → CUDA float16.
    #   * W_BOT_STT_DEVICE env değişkeni ("cpu"/"cuda") ile manuel override.
    _STT_VRAM_THRESHOLD_GB = 8.0

    def _stt_backend():
        import os as _os
        override = _os.environ.get("W_BOT_STT_DEVICE", "").lower()
        if override != "cpu":
            # CTranslate2 CUDA'yı PyTorch'tan bağımsız sorgula (Jetson driver uyumu için)
            try:
                import ctranslate2 as _ct2
                if _ct2.get_supported_compute_types("cuda"):
                    print("  STT: CTranslate2 CUDA seçildi")
                    return "cuda", "float16"
            except Exception:
                pass
        try:
            import ctranslate2 as _ct2
            if "int8" in _ct2.get_supported_compute_types("cpu"):
                return "cpu", "int8"
        except Exception:
            pass
        return "cpu", "float32"

    _stt_dev, _stt_ct = _stt_backend()
    print(f"STT modeli yükleniyor... ({_stt_dev})")
    stt: Any = SpeechToText(model_size=WHISPER_MODEL, device=_stt_dev, compute_type=_stt_ct)
    silence_wav = _numpy_to_wav(np.zeros(SAMPLE_RATE, dtype=np.int16), SAMPLE_RATE)
    # SGEMM testi: gerçek ses benzeri küçük gürültüyle CTranslate2'yi doğrula
    _test_wav = _numpy_to_wav(
        (np.random.rand(SAMPLE_RATE // 4) * 200 - 100).astype(np.int16), SAMPLE_RATE
    )
    try:
        await stt.transcribe(_test_wav, language="tr")
        await stt.transcribe(silence_wav, language="tr", initial_prompt=STT_INITIAL_PROMPT)
        print("STT: hazır\n")
    except Exception as _stt_err:
        if "SGEMM" in str(_stt_err) or "backend" in str(_stt_err).lower() or "cuda" in str(_stt_err).lower():
            print(f"  ⚠ CTranslate2 hatası ({_stt_err}) → openai-whisper fallback")
            stt = _OpenAIWhisperSTT(model_size=WHISPER_MODEL)
            await stt.transcribe(silence_wav, language="tr")
            print("STT: openai-whisper hazır\n")
        else:
            raise

    # USB mikrofon cihazını otomatik bul
    input_device = _find_input_device()
    if input_device is not None:
        print(f"Mikrofon: device {input_device} ({sd.query_devices(input_device)['name'].strip()})")
    else:
        print("Mikrofon: varsayılan cihaz")

    # USB hoparlörü isimle oto-tespit — kart numarası replug/boot'ta kayabilir
    global ALSA_OUTPUT_DEVICE
    _detected_out = _find_output_device()
    if _detected_out:
        ALSA_OUTPUT_DEVICE = _detected_out
        print(f"Hoparlör: {_detected_out} (oto-tespit)")
    else:
        print(f"Hoparlör: {ALSA_OUTPUT_DEVICE} (sabit fallback)")

    order_tracker = OrderTracker()

    # Wake word
    ww_model   = _load_wakeword()
    tts_active = threading.Event()  # TTS çalarken set, dinlerken clear
    if ww_model:
        print("Wake word: hey_garson.onnx yüklendi")
    else:
        print("Wake word: model bulunamadı → ENTER tuşu modu")

    print("\n✓ Tüm modeller hazır!\n")

    # Wake word modunda karşılamayı ilk seslenişe bırak
    ww_task: "asyncio.Task | None" = None
    if ww_model:
        print("\n  👂 'hey garson' bekleniyor...", flush=True)
        ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))
    else:
        # ENTER modunda karşılamayı hemen söyle
        _greeting = _greet()
        print(f"W-BOT: {_greeting}")
        try:
            await _speak(tts, _greeting, tts_active)
        except Exception as e:
            logger.warning("Karşılama TTS hatası: %s", e)

    # --- Ana döngü ---
    first_wakeword     = True
    new_customer       = True   # Her oturum başında karşıla
    conversation_active = False  # Yanıttan sonra wake word'süz dinleme penceresi açık mı?
    pending_reset      = False  # Farewell tespit edildi mi (10s sessizlik sonrası uygulanır)
    awaiting_confirmation = False  # S12 TUR 1 özeti söylendi, onay bekleniyor
    while True:
        # Tetikleyici: conversation hold | wake word | ENTER
        if conversation_active:
            # Yanıttan hemen sonra 10s pencere — wake word beklenmez
            wav_bytes = await asyncio.to_thread(
                _record, input_device, initial_wait_s=CONVO_HOLD_S)
            if not wav_bytes:
                # Sessizlik — wake word moduna geri dön
                print(f"  ⏰ {CONVO_HOLD_S}s sessizlik — 'hey garson' bekleniyor...", flush=True)
                conversation_active = False
                if pending_reset:
                    llm.reset_history()
                    order_tracker.reset()
                    new_customer = True
                    pending_reset = False
                    print("--- Yeni müşteri oturumu hazır ---", flush=True)
                if ww_model:
                    ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))
                continue
            # Konuşma geldi — farewell beklemesini iptal et, tur devam etsin
            pending_reset = False
        else:
            if ww_model:
                await ww_task
                print("  ✔  Wake word algılandı!", flush=True)
                if first_wakeword:
                    await asyncio.to_thread(_beep)
                    first_wakeword = False
            else:
                try:
                    print("\n" + "-" * 40)
                    input("  ENTER'a bas ve konuş → ")
                except EOFError:
                    break

            # Yeni müşteri oturumunda karşıla, ardından direkt kayda geç
            if new_customer and ww_model:
                new_customer = False
                _greeting = _greet()
                print(f"W-BOT: {_greeting}")
                try:
                    await _speak(tts, _greeting, tts_active)
                except Exception as e:
                    logger.warning("Karşılama TTS hatası: %s", e)

            # Kayıt — mevcut davranış (VAD_MAX_S güvenlik kapağı)
            wav_bytes = await asyncio.to_thread(_record, input_device)
            if not wav_bytes:
                # Wake word algılandı ama konuşma gelmedi — tekrar wake word'e dön
                if ww_model:
                    ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))
                    print("\n  👂 'hey garson' bekleniyor...", flush=True)
                continue

        # STT
        import time as _time
        print("  ⏳ Anlıyorum...", flush=True)
        _t_stt = _time.perf_counter()
        try:
            result    = await stt.transcribe(wav_bytes, language="tr",
                                             initial_prompt=STT_INITIAL_PROMPT)
            user_text = result["text"].strip()
        except Exception as e:
            print(f"  ✗ STT hatası: {e}")
            conversation_active = False
            if ww_model:
                ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))
            continue
        _stt_ms = (_time.perf_counter() - _t_stt) * 1000

        if not user_text:
            print("  (Ses algılanamadı, tekrar dene)")
            conversation_active = False
            if ww_model:
                ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))
            continue

        print(f"\nMüşteri: {user_text}")
        print(f"  ⏱  STT: {_stt_ms:.0f}ms", flush=True)

        # --- Guard 1: STT düşük güven ---
        if _stt_low_confidence(result, user_text, in_convo=conversation_active):
            print("  ⚠  STT güven düşük — tekrar dinleniyor", flush=True)
            _guard1_msg = "Özür dilerim, tam anlayamadım. Tekrar söyler misiniz?"
            try:
                await _speak(tts, _guard1_msg, tts_active)
            except Exception as _g1e:
                logger.warning("Guard1 TTS hatası: %s", _g1e)
            conversation_active = True
            continue

        # --- Guard 2: Menü-dışı sipariş (hesap isteklerini atla) ---
        if not _is_bill_request(user_text) and _is_off_menu_order(user_text, order_tracker._lookup, in_convo=conversation_active):
            print("  ⚠  Menü-dışı ürün tespit edildi", flush=True)
            _guard2_msg = "Maalesef bu ürün menümüzde yok. Başka bir şey söyleyebilir miyim?"
            try:
                await _speak(tts, _guard2_msg, tts_active)
            except Exception as _g2e:
                logger.warning("Guard2 TTS hatası: %s", _g2e)
            conversation_active = True
            continue

        # --- Guard 3: Hakaret / küfür ---
        if _is_offensive(user_text):
            print("  ⚠  Uygunsuz dil tespit edildi", flush=True)
            _guard3_msg = "Yalnızca sipariş ve menü konularında yardımcı olabilirim. Başka bir şey söyleyebilir misiniz?"
            try:
                await _speak(tts, _guard3_msg, tts_active)
            except Exception as _g3e:
                logger.warning("Guard3 TTS hatası: %s", _g3e)
            conversation_active = True
            continue

        # Siparişi ÖNCE işle — S12 guard'ı ve hesap toplamı güncel sepete güvenir.
        # Fast-path'ten de önce: "Teşekkürler, bu kadar." gibi ≤5 kelimelik
        # kapanışlar veda fast-path'ine düşmeden sepet/özet burada ele alınmalı.
        _items_before_turn = {name: qty for name, _p, qty in order_tracker.items}
        order_tracker.detect_order(user_text)
        # Bu turda eklenenler — V01 fiyat enjeksiyonu (post-processing) kullanır
        _added_this_turn = [
            (name, price, qty - _items_before_turn.get(name, 0))
            for name, price, qty in order_tracker.items
            if qty > _items_before_turn.get(name, 0)
        ]
        if order_tracker.items:
            _cart = ", ".join(f"{qty}× {name}" for name, _, qty in order_tracker.items)
            print(f"  🛒 Sepet: {_cart} → {order_tracker.total} TL", flush=True)

        # --- S12 guard TUR 2: özet onayı bekleniyor ---
        if awaiting_confirmation:
            awaiting_confirmation = False
            if _is_order_confirmation(user_text):
                print(f"W-BOT:   {_S12_CLOSING_REPLY}", flush=True)
                try:
                    await _speak(tts, _S12_CLOSING_REPLY, tts_active)
                except Exception as _s12e:
                    logger.warning("S12 TUR2 TTS hatası: %s", _s12e)
                order_tracker.reset()
                pending_reset = True        # sessizlikte LLM history + oturum sıfırlanır
                conversation_active = True  # müşteri hâlâ konuşabilir (fikir değişikliği)
                continue
            # Onay gelmedi — normal akışa düş (kapanış sinyali aşağıda yeniden değerlendirilir)

        # --- S12 guard TUR 1: kapanış sinyali + dolu sepet → deterministik özet ---
        # Hesap istekleri hariç — onları mevcut deterministik hesap şablonu karşılar.
        if order_tracker.items and not _is_bill_request(user_text) and _is_closing_signal(user_text):
            _s12_reply = _closing_summary(order_tracker.items, order_tracker.total)
            print(f"W-BOT:   {_s12_reply}", flush=True)
            try:
                await _speak(tts, _s12_reply, tts_active)
            except Exception as _s12e:
                logger.warning("S12 TUR1 TTS hatası: %s", _s12e)
            awaiting_confirmation = True
            conversation_active = True
            continue

        # --- Fast-path: Veda / selam / onay şablonu (LLM'i atlar) ---
        _fp = _fast_path_reply(user_text, in_convo=conversation_active)
        if _fp:
            print(f"W-BOT:   {_fp}", flush=True)
            try:
                await _speak(tts, _fp, tts_active)
            except Exception as _fpe:
                logger.warning("Fast-path TTS hatası: %s", _fpe)
            # Veda → oturumu kapat; selam/onay → 10s pencere açık kalsın.
            # "İyi günler" açılışta selam sayılır, oturum KAPANMAZ (görev #25 a)
            _is_farewell_fp = _salutation_intent(user_text, conversation_active) == "farewell"
            if _is_farewell_fp:
                pending_reset = True
                conversation_active = False
                if ww_model:
                    ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))
            else:
                conversation_active = True  # selam/onay → sohbet devam eder
            continue

        # 3+5. Streaming: LLM üretim + TTS sentez + oynatma paralel pipeline
        # (detect_order() yukarıda, S12 guard'ından önce çalıştı — sepet güncel)
        print("  ⏳ Yanıt üretiliyor...", flush=True)
        llm_input = user_text
        # Sipariş niyeti varsa güncel sepeti LLM'e ver — menü dışı ürün uydurmayı önler
        _t_lower = user_text.lower().replace('̇', '')
        _has_order_intent = any(v in _t_lower for v in _ORDER_VERBS) or any(v in _t_lower for v in _CANCEL_VERBS)
        if order_tracker.items and _has_order_intent and not _is_bill_request(user_text):
            _cart_ctx = ", ".join(f"{qty}× {name}" for name, _, qty in order_tracker.items)
            llm_input = (f"{user_text} [Güncel sepet: {_cart_ctx}. "
                         f"SADECE sepetteki ürünleri teyit et. "
                         f"Menüde olmayan ürün varsa 'menümüzde bulunmuyor' de, "
                         f"fiyat veya adet uydurma.]")
        if _is_bill_request(user_text) and order_tracker.total > 0:
            t_lower = user_text.lower()
            has_new_order = any(v in t_lower for v in _ORDER_VERBS)
            _item_lines = ", ".join(
                f"{qty}× {name} ({d_price * qty} TL)"
                for name, d_price, qty in order_tracker.items
            )
            if has_new_order:
                llm_input = (f"{user_text} [Yanıtın sonu şöyle bitmeli: "
                             f"Toplam {order_tracker.total} TL. Afiyet olsun!]")
            else:
                llm_input = (f"{user_text} [Sepeti sesli oku: {_item_lines}. "
                             f"Toplam {order_tracker.total} TL — bu rakamı değiştirme.]")
        _t_llm = _time.perf_counter()
        try:
            if _is_bill_request(user_text) and order_tracker.total > 0:
                # Hesap: LLM'e güvenme — deterministik template (liste + toplam)
                _parts = [f"{qty} {name}, {d_price * qty} TL"
                          for name, d_price, qty in order_tracker.items]
                reply = "Siparişiniz: " + "; ".join(_parts) + f". Toplam {order_tracker.total} TL. Afiyet olsun!"
                await _speak(tts, reply, tts_active)
            else:
                reply = await _speak_streaming(tts, llm, llm_input, tts_active)
                # E19 "?" kontrolü modelin KENDİ yanıt sonuna bakmalı — V01
                # fiyat eki sonu kaydırıp gereksiz ikinci soru eklettirmesin
                _model_reply = reply
                # V01: modifikasyonlu siparişte eksik TL fiyatını enjekte et
                _price_add = _modification_price_addition(
                    user_text, reply, _added_this_turn)
                if _price_add:
                    await _speak(tts, _price_add, tts_active)
                    reply = reply.rstrip() + " " + _price_add
                # Post-processing: "?" ile bitmeyen yanıtlara soru ekle
                # (veda, fallback ve "bilgim yok" yanıtları hariç)
                if not _model_reply.rstrip().endswith("?"):
                    _rl = _model_reply.lower()
                    _is_farewell_reply = any(fw in _rl for fw in (
                        "afiyet", "güle güle", "iyi günler", "görüşürüz",
                        "hoşça kal", "tekrar bekle",
                    ))
                    _is_fallback_reply = any(fb in _rl for fb in (
                        "bilgim yok", "personelimize",
                    ))
                    if not _is_farewell_reply and not _is_fallback_reply:
                        if _is_description_question(user_text, order_tracker._lookup):
                            addition = "Getireyim mi?"
                        else:
                            addition = "Ne istersiniz?"
                        await _speak(tts, addition, tts_active)
                        reply = reply.rstrip() + " " + addition
        except Exception as e:
            print(f"  ✗ LLM/TTS hatası: {e}")
            if ww_model:
                ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))
            continue
        _llm_ms = (_time.perf_counter() - _t_llm) * 1000

        print(f"W-BOT:   {reply}")
        print(f"  ⏱  LLM+TTS: {_llm_ms:.0f}ms  |  Toplam: {_stt_ms + _llm_ms:.0f}ms")

        # Oturum sonu tespiti — müşteri veya bot veda ediyorsa 10s sonra sıfırla
        farewell_phrases = ["güle güle", "görüşürüz", "hoşça kal", "iyi günler", "tekrar bekleriz"]
        short_user = user_text.strip().lower()
        reply_lower = reply.lower()
        is_farewell = (
            any(p in reply_lower for p in farewell_phrases)   # bot veda etti
            or any(p in short_user for p in farewell_phrases)  # müşteri veda etti
            or (len(short_user) < 40 and "teşekkür" in short_user
                and not any(q in short_user for q in ["alabilir", "istiyorum", "verir", "?", "mı", "mi"]))
        )
        if is_farewell:
            pending_reset = True
            print(f"  💤 Veda algılandı — {CONVO_HOLD_S}s sessizlik sonrası yeni müşteri için hazır")

        # Conversation hold penceresini aç; sessizlikte wake word'e dönülür
        conversation_active = True
        print(f"  ⏳ Devam etmek için konuşabilirsiniz ({CONVO_HOLD_S}s)...", flush=True)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="W-BOT demo")
    parser.add_argument("--adapter-dir", default=None,
                        help="LoRA adapter dizini (opsiyonel, sadece PC/transformers backend)")
    args = parser.parse_args()
    try:
        asyncio.run(run_demo(adapter_dir=args.adapter_dir))
    except KeyboardInterrupt:
        print("\n\nDemo sonlandırıldı.")


if __name__ == "__main__":
    main()
