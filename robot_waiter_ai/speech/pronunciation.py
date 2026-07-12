r"""
speech/pronunciation.py — yabancı-yazımlı kelimeler için Türkçe TTS telaffuz haritası.

Sorun
-----
Piper'ın fonemizasyon katmanı (espeak-ng, Türkçe ses) İngilizce/yabancı YAZIMLI
kelimeleri Türkçe harf kurallarıyla okur. Örnek (piper --debug ile doğrulandı):

    cheesecake  → dʒheesedʒakˈɛ   ("cihiyseceyke")   —  c→dʒ
    cappuccino  → dʒapːudʒːinˈɔ    ("capuçːino")      —  c→dʒ, çift ünsüz gemine
    latte       → ɫatːˈɛ           ("latːe")          —  tt gemine
    croissant   → dʒroɪssˈant      ("croissant")      —  düz harf okuması

Bu bir MODEL/eğitim sorunu DEĞİL: VITS metni hiç görmez, yalnız fonem alır.
Çözüm deterministik metin ön-işleme — sentezden hemen önce yabancı yazımı
Türkçe fonetik yazıma çevirmek (cheesecake→çizkeyk → tʃɪzkˈɛjk). Her hedef
yazım piper --debug ile doğrulandı (doğru espeak-tr fonemi ürettiği teyit edildi).

Kapsam
------
menu.yaml'daki ürünlerin HEPSİ Türkçe yazımlı (mercimek çorbası, künefe, lazanya,
tiramisu, somon) ve espeak-tr'de sorunsuz — haritaya menü ürünü GİRMEZ. Değer,
menüde olmayan ama garson sohbetinde/önerisinde (LLM serbest metni, fast-path
şablonu, guard yanıtı) geçebilecek yaygın kafe/restoran terimlerinde.

Yalnız TTS girdisini etkiler; ekrana/loglara/OrderTracker'a giden metin değişmez
(tek çağrı yeri: PiperTTS._run_piper_blocking, sentezden hemen önce).

Kelime-sınırı güvenliği
-----------------------
Regex `(?<!\w) ... (?!\w)` ile YALNIZ tam kelime eşleşir — kelime içinde değil
(ör. "cola", "çikolata" veya "chocolate" içinde tetiklenmez). Bu, geçmişteki
_OFFENSIVE_TERMS "göt" substring hatasının (götürür → yanlış eşleşme) tekrarını
önler. Türkçe ekler kesme işaretiyle tolere edilir: cheesecake'i, cola'lar,
cappuccino'yu → kök çevrilir, ek korunur.
"""
from __future__ import annotations

import re

__all__ = ["PRONUNCIATION_MAP", "apply_pronunciation"]


# İngilizce/yabancı yazım → Türkçe fonetik yazım. Anahtarlar küçük harf.
# Hepsi piper (espeak-tr) --debug çıktısıyla doğrulandı.
PRONUNCIATION_MAP: dict[str, str] = {
    # ── kahveler ──
    "cappuccino": "kapuçino",
    "americano": "amerikano",
    "espresso": "espreso",
    "macchiato": "makiyato",
    "latte": "late",
    "mocha": "moka",
    "frappe": "frape",
    "nescafé": "neskafe",
    "nescafe": "neskafe",
    # ── soğuk içecekler ──
    "smoothie": "ismuti",
    "milkshake": "milkşeyk",
    "coca-cola": "koka kola",
    "cola": "kola",
    "sprite": "sprayt",
    "ice tea": "ays ti",
    # ── tatlılar ──
    "cheesecake": "çizkeyk",
    "brownie": "brauni",
    "waffle": "vofıl",
    "cookie": "kuki",
    "muffin": "mafin",
    "pancake": "pankek",
    "sundae": "sanday",
    "croissant": "kruvasan",
    # ── tuzlular / diğer ──
    "club sandwich": "klap sendviç",
    "sandwich": "sendviç",
    "steak": "steyk",
    "nugget": "naget",
    "ketchup": "keçap",
    "wrap": "vırap",
    "sushi": "suşi",
}


def _norm(word: str) -> str:
    """Arama için normalize et. Türkçe İ-fix: "İ".lower() → "i̇" (i + U+0307
    birleşik nokta); noktayı temizle ki harita anahtarıyla eşleşsin."""
    return word.lower().replace("̇", "")


# Anahtarları uzunluk-azalan sırala: çok-kelimeli/uzun olan önce eşleşsin
# ("club sandwich" → "sandwich"ten, "coca-cola" → "cola"dan önce). Aksi hâlde
# "Coca-Cola" içindeki "cola" yanlış çevrilirdi.
_KEYS = sorted(PRONUNCIATION_MAP, key=len, reverse=True)

# (?<!\w)  : kelime içinde başlama (substring eşleşmesini engelle)
# (KEY)    : yabancı yazım (büyük/küçük harf duyarsız)
# (['’]\w+)?: opsiyonel Türkçe ek — kesme işareti (' veya ’) + ek harfleri
# (?!\w)   : kelime içinde bitme (ekten sonra da sınır olmalı)
_PATTERN = re.compile(
    r"(?<!\w)(" + "|".join(re.escape(k) for k in _KEYS) + r")(['’]\w+)?(?!\w)",
    re.IGNORECASE | re.UNICODE,
)


def _match_case(replacement: str, original: str) -> str:
    """Cümle-başı / özel-ad büyük harfini koru (fonemi etkilemez, kozmetik)."""
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def apply_pronunciation(text: str) -> str:
    """Yabancı-yazımlı kelimeleri Türkçe fonetik yazıma çevir.

    YALNIZ TTS girdisi için — kaynağı ne olursa olsun (LLM, fast-path şablonu,
    guard yanıtı) sentezden hemen önce çağrılır. Sözlükte olmayan kelimeler ve
    Türkçe metin aynen geçer.
    """
    def _sub(m: "re.Match[str]") -> str:
        word = m.group(1)
        suffix = m.group(2) or ""
        replacement = PRONUNCIATION_MAP[_norm(word)]
        return _match_case(replacement, word) + suffix

    return _PATTERN.sub(_sub, text)
