"""
inference/llama_cpp_backend.py — Qwen3-4B GGUF backend for Jetson (llama-cpp-python).

Drop-in replacement for qwen3_backend.Qwen3Backend.
Uses llama-cpp-python with full CUDA offload (SM87, Jetson Orin NX).
"""
from __future__ import annotations

import logging
import re
import threading
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_GGUF_FILENAME = "Qwen3-4B-wbot_v5-Q4_K_M.gguf"
_JETSON_GGUF   = Path("/home/emk/models") / _GGUF_FILENAME
_REPO_GGUF     = Path(__file__).resolve().parent.parent / "models" / _GGUF_FILENAME

GGUF_4B  = _JETSON_GGUF if _JETSON_GGUF.exists() else _REPO_GGUF
GGUF_17B = Path("/home/emk/llama.cpp/Qwen3-1.7B-Q8_0.gguf")

# 4B kalite açısından üstün — 1.7B test edildi, yetersiz bulundu
GGUF_PATH = GGUF_4B

_MENU_YAML = Path(__file__).resolve().parent.parent / "data" / "menu.yaml"

_SYSTEM_TEMPLATE = """\
Sen sıcakkanlı ve güler yüzlü bir Türk restoran garsonu olarak konuşan yapay zekasın. Gerçek bir garson gibi samimi ve içten ol: akıcı doğal Türkçe kullan, uygun anlarda "Buyurun!", "Harika seçim!" gibi kısa samimi ifadeler ekle. Her turda farklı sözcük ve cümle yapıları kullan; bir önceki yanıtındaki kapanış veya açılış ifadesini birebir tekrarlama. Müşteriye DAİMA "siz" ile hitap et; "musun", "istiyorsun", "ister misin" gibi tekil ikinci şahıs ASLA kullanma — yerine "musunuz", "istiyorsunuz", "ister misiniz" kullan.

MENÜ:
{menu_text}

KURALLAR:
- Yalnızca Türkçe. İngilizce kelime, madde işareti, kalın yazı veya emoji kullanma. Müşterinin kullandığı hitap biçimlerini ("kardeşim", "dostum", "lan", "abi" vb.) yanıtta ASLA tekrar etme.
- En fazla 2 kısa cümle, toplam 20 kelimeyi geçme. Listeleme yapma. Hesap/veda/afiyet kapanışları hariç yanıt MUTLAKA soru işaretiyle bitmeli.
- Yalnızca menüdeki ürünleri söyle; asla uydurma ürün ekleme.
- Karşılama ("merhaba", "selam", "hoş geldin" gibi) VEYA genel kategorisiz menü sorusu ("ne var", "menünüz ne" — "çorba/tatlı/ana yemek/içecek" gibi kategori adı GEÇMİYORSA): ZORUNLU — TEK cümlede "çorba", "ana yemek", "tatlı" ve "içecek" sözcüklerinin DÖRDÜ DE geçmeli + YANIT MUTLAKA SORU İŞARETİYLE BİTMELİ ("Ne arzu edersiniz?", "Ne istersiniz?" gibi). Ürün adı veya örnek SAYMA. En çok 15 kelime. Bu kural istisnasızdır.
- Kategori içeriği sorusu ("çorba ne var", "tatlılar neler", "hangi çorbalar var", "ana yemekler neler", "ne vardı" gibi — kategori adı geçiyorsa ve sipariş içermiyorsa): YALNIZCA o kategorideki ürün isimlerini say, fiyat ve "TL" SÖYLEME. Örnek: "Çorbada Mercimek ve Kremalı Mantar var. Hangisini tercih edersiniz?"
- FİYAT SÖYLEME KURALI: "TL", "lira" veya sayısal fiyat yalnızca şu üç durumda yanıtta GEÇEBİLİR — (1) müşteri açıkça fiyat sordu ("ne kadar", "fiyatı", "kaç TL"), (2) sipariş onayı ("alayım/istiyorum/getir" geçti), (3) hesap istendi. Bunların DIŞINDA — öneri, tanıtım, açıklama, karşılama, kategori listesi — "TL" yanıtta GEÇMEMELİ.
- Öneri veya tavsiye sorusunda ("ne önerirsin", "ne yesem", "ne alsam", "ne tavsiye edersiniz", "ne iyi" geçiyorsa): Eğer kategori belirtildiyse YALNIZCA o kategoriden 1-2 ürün söyle — başka kategorilerden hiçbir şey ekleme; yoksa menüden 1-2 öne çıkan ürünü öner. Yanıtta TL geçmesin.
- Sipariş ("alayım/istiyorum/getir" geçiyorsa): Önce istenen ürünün MENÜDE OLUP OLMADIĞINI kontrol et. Menüde YOKSA sipariş onayı YAPMA, başka ürün önerme veya uydurma — SADECE "Bu konuda bilgim yok, personelimize sorabilirsiniz." de; yanıtta hiçbir ürün adı veya fiyat geçmesin. Menüde VARSA: Sıcak olumlu bir kabul sözcüğüyle başla ("Elbette", "Tabii ki", "Tabii efendim", "Memnuniyetle", "Harika seçim" — her turda farklı birini kullan) + ürün adı + TL fiyat + SON CÜMLE MUTLAKA "başka" kelimesini içeren bir soru ("Başka bir şey alır mısınız?", "Başka bir isteğiniz var mı?", "Başka bir şey ister misiniz?", "Başka ne istersiniz?" — her turda farklı birini kullan). SİPARİŞ ONAYINDA "Getireyim mi?" KESINLIKLE YASAK — bu yalnızca ürün sorusuna yanıtta kullanılır.
- Birden fazla ürün siparişi: HER ürünü ayrı bir onay cümlesiyle (ürün adı + TL fiyat) onayla.
- Sipariş miktarı: Müşterinin söylediği adeti aynen yansıt. "iki köfte" → 2 adet (480 TL). Sayı söylemediyse 1 adet. ASLA kendiliğinden artırma.
- "Siparişiniz onaylandı", "onaylanıyor", "kaydedildi" YASAK.
- Ürün sorusu ("nedir", "nasıl", "ne var içinde", "malzeme", "içindekiler", "nasıl yapılıyor", "nasıl hazırlanıyor" geçiyorsa): Menüdeki açıklamayı ve malzemeleri kendi cümlelerinle anlat. ZORUNLU — son cümle İSTİSNASIZ tam olarak "Getireyim mi?" veya "İster misiniz?" ile bitmeli; başka hiçbir soru kalıbı ("...edilir mi?", "...sever misiniz?" gibi) KULLANMA. En fazla 3 cümle.
- Kalori sorusu ("kaç kalori", "kalori", "kalorisi", "kcal" geçiyorsa): İlgili ürünün kalori bilgisini menüden söyle. Sayıdan sonra mutlaka "kalori" söyle, "kcal" kelimesini kullanma. TL söyleme. 1 cümle yeterli.
- Eşleşme önerisi: Müşteri bir ürün sipariş ettiğinde "iyi gider" listesindeki 1 ürünü nazikçe önerebilirsin — "Yanında X de alır mısınız?" veya "X ile harika gider, tavsiye ederim." TL söyleme, 1 cümle. Zorunlu değil, konuşma akışında doğal geliyorsa ekle.
- Sipariş sırasında ASLA toplam söyleme. Hesap isteği yalnızca "hesabı alabilir miyim", "hesap lütfen", "ödeyeceğim", "ödeyeyim" gibi doğrudan taleplere verilen yanıttır. Bu durumda "Toplam X TL." biçiminde net tutar ver ve afiyet/iyi günler kapanışı ekle. "Toplam" kelimesi ve sayısal değer zorunludur.
- Müşteri siparişi kapatmak istediğini belirttiğinde ("başka istemiyorum", "bu kadar" veya sepette ürün varken bir veda ifadesi) ÖNCE sipariş özeti + Toplam [X] TL + "Onaylıyor musunuz?" sorusuyla yanıt ver; bu turda toplamı SÖYLE. Müşteri onaylayınca (evet/tamam/olur vb.) yalnızca "Afiyet olsun!" de, toplamı TEKRAR SÖYLEME. Sepet boşken gelen saf vedada ("Güle güle") bu akış uygulanmaz, sade veda yeterli.
- "Güle güle" yalnızca müşteri masadan kalkarken veya hesabı öderken söyle.
- Sipariş iptali/değişikliği ("istemiyorum/iptal/yerine/çıkar" geçiyorsa): Anlayışla karşıla, hangi ürünün çıkarıldığını söyle; yeni sipariş varsa ekle. Cümleyi her turda farklı kur.
- Vejetaryen/etsiz sorusu: Menüde [vejetaryen] etiketli ürünleri listele.
- Alerji sorusu ("alerji/gluten/süt/içerik" geçiyorsa): İlgili ürünlerin allerjen bilgisini menüden söyle; kesin karar için "personelimize danışabilirsiniz" de.
- Menüde olmayan ürün ("hamburger var mı?", "pizza" gibi): SADECE şunu söyle: "Bu konuda bilgim yok, personelimize sorabilirsiniz." Ek açıklama yapma, menü kategorilerini sayma, benzer ürün önerme.
- Sipariş sırasında ara toplam soruları ("şimdiye kadar ne kadar oldu?", "kaça çıktı?" gibi) HESAP İSTEĞİ DEĞİLDİR — SADECE şunu söyle: "Bu konuda bilgim yok, personelimize sorabilirsiniz.\""""


def _strip_markdown(text: str) -> str:
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'^\s*[-•]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'[\U0001F300-\U0001FAFF\U00002700-\U000027BF]+', '', text)
    text = re.sub(r'\n+', ' ', text)           # satır içi newline → boşluk (TTS için)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\b[İI]zgara\b', 'Izgara', text)
    text = re.sub(r'\bizgara\b', 'ızgara', text)
    text = re.sub(r'\bkuneffe?\b', 'künefe', text, flags=re.IGNORECASE)  # Kuneffe/kunefe → künefe
    text = re.sub(r'\biçeçek', 'içecek', text, flags=re.IGNORECASE)
    text = re.sub(r'\biçece[gğ]i\b', 'içeceği', text, flags=re.IGNORECASE)  # içecegi → içeceği
    text = re.sub(r'[Ss]ize getirmek ister misiniz\??', 'Getireyim mi?', text)
    # Yanlış sesli uyumu düzeltme (Qwen3 Türkçe gramer hatası)
    text = re.sub(r'\balır musunuz\b', 'alır mısınız', text, flags=re.IGNORECASE)
    text = re.sub(r'\bister musunuz\b', 'ister misiniz', text, flags=re.IGNORECASE)
    # <think>...</think> bloklarını temizle (thinking mode açık kalırsa)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Sipariş onayı sonrası parantez açıklamalarını temizle: "\n(açıklama.)"
    text = re.sub(r'\n\s*\([^)]{5,}\)\s*$', '', text)
    return text.strip()


_ALLERGEN_TR = {"gluten": "gluten", "dairy": "süt ürünü", "nuts": "kuruyemiş"}
_TAG_TR = {
    "vegetarian": "vejetaryen",
    "meat": "et",
    "chicken": "tavuk",
    "traditional": "geleneksel",
    "light": "hafif",
    "sweet": "tatlı",
    "hot": "sıcak",
    "cold": "soğuk",
    "refreshing": "ferahlatıcı",
}


def _build_menu_text() -> str:
    if not _MENU_YAML.exists():
        return "(Menü dosyası bulunamadı)"
    with open(_MENU_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    lines = []
    current_category = None
    for item in data.get("menu", []):
        cat = item.get("category", "")
        if cat != current_category:
            lines.append(f"\n{cat}:")
            current_category = cat
        name = item["name"]
        price = item["price"]
        desc = item.get("description", "")
        allergens = [_ALLERGEN_TR[a] for a in item.get("allergens", []) if a in _ALLERGEN_TR]
        tags = [_TAG_TR[t] for t in item.get("tags", []) if t in _TAG_TR]
        calories = item.get("calories")
        pairs = item.get("pairs_with", [])
        extra_parts = []
        if tags:
            extra_parts.append(", ".join(tags))
        if allergens:
            extra_parts.append(f"içerir: {', '.join(allergens)}")
        extra = f" [{'; '.join(extra_parts)}]" if extra_parts else ""
        cal_note = f" Yaklaşık {calories} kalori." if calories else ""
        pairs_str = f" [iyi gider: {', '.join(pairs)}]" if pairs else ""
        lines.append(f"  - {name}: {price} TL  ({desc}{cal_note}){extra}{pairs_str}")
    return "\n".join(lines).strip()


class LlamaCppBackend:
    """Qwen3-4B Q4_K_M GGUF backend via llama-cpp-python. Thread-safe after __init__."""

    def __init__(self, gguf_path: str | Path = GGUF_PATH) -> None:
        self._gguf_path = Path(gguf_path)
        self._history: list[dict] = []
        self._system_prompt = _SYSTEM_TEMPLATE.format(menu_text=_build_menu_text())
        self._llm = None
        self._load()

    def _load(self) -> None:
        from llama_cpp import Llama
        logger.info("Qwen3-4B GGUF yükleniyor: %s", self._gguf_path)
        self._llm = Llama(
            model_path=str(self._gguf_path),
            n_gpu_layers=-1,
            n_ctx=4096,
            # llama.cpp'nin seed verilmediğinde kullandığı örtük varsayılan
            # (LLAMA_DEFAULT_SEED) açıkça yazıldı — davranışı değiştirmez,
            # yalnızca dokümante eder ve gelecekte sürüm değişikliğiyle sessizce
            # farklılaşmasını önler. WSL2 + Jetson'da 32/32 senaryoda bit-bit
            # doğrulandı (WSL2: 5 Temmuz, Jetson: 6 Temmuz 2026). seed=42
            # denendi ve REDDEDİLDİ: davranışı değiştiriyor (görev #23).
            seed=0xFFFFFFFF,
            verbose=False,
        )
        logger.info("LlamaCppBackend hazır.")

    def _format_prompt(self, messages: list[dict]) -> str:
        """Qwen3 chat formatı — thinking modu kapalı (<think>\n\n</think> ile başlar)."""
        parts = []
        for msg in messages:
            role, content = msg["role"], msg["content"]
            if role == "system":
                parts.append(f"<|im_start|>system\n{content}<|im_end|>\n")
            elif role == "user":
                parts.append(f"<|im_start|>user\n{content}<|im_end|>\n")
            elif role == "assistant":
                parts.append(f"<|im_start|>assistant\n{content}<|im_end|>\n")
        parts.append("<|im_start|>assistant\n<think>\n\n</think>\n\n")
        return "".join(parts)

    # Görev wbot_v5 (10 Tem 2026) ölçümü: gerçek llama-cpp-python tokenizer'ıyla
    # wrapped sistem promptu 2922 tok (eski "~2100 tok" varsayımı güncel değildi —
    # menu.yaml + kural seti büyümüş). n_ctx(4096) - sistem(2922) - assistant
    # primer(12) - max_tokens(65) - güvenlik tamponu(300) ≈ 797 tok geçmiş bütçesi;
    # gerçek dataset diyaloglarıyla ölçülen oran (~1.41 karakter/wrapped-tok) ile
    # ~1000 karakter. 4000 değeri (eski varsayımla hesaplanmış) n_ctx'i ~730 tok
    # aşırıp ValueError fırlatabiliyordu (llama_cpp Llama.create_completion,
    # prompt_tokens >= n_ctx kontrolü) — ampirik olarak doğrulandı.
    _MAX_HIST_CHARS = 1000

    def _trim_history(self) -> None:
        """Bağlam penceresi dolmadan önce en eski user+assistant turlarını at."""
        while len(self._history) > 1:
            total = sum(len(m["content"]) for m in self._history)
            if total <= self._MAX_HIST_CHARS:
                break
            # En eski ikiliyi (user + assistant) sil; son mesaja dokunma
            if len(self._history) >= 3:
                self._history = self._history[2:]
                logger.warning("Bağlam penceresi dolmak üzere — en eski tur silindi, %d mesaj kaldı.", len(self._history))
            else:
                break

    def generate_reply(self, user_text: str) -> str:
        """Generate a Turkish waiter reply, maintaining conversation history."""
        self._history.append({"role": "user", "content": user_text})
        self._trim_history()

        messages = [{"role": "system", "content": self._system_prompt}] + self._history

        result = self._llm.create_completion(
            prompt=self._format_prompt(messages),
            max_tokens=65,
            temperature=0.55,
            top_p=0.9,
            top_k=40,
            repeat_penalty=1.3,
            stop=["<|im_end|>", "<|endoftext|>"],
        )

        reply = result["choices"][0]["text"].strip()
        reply = _strip_markdown(reply)

        self._history.append({"role": "assistant", "content": reply})
        return reply

    def stream_reply(self, user_text: str):
        """Generate reply as a token stream; yields raw tokens one by one.

        History is updated after all tokens are consumed (generator exhausted).
        """
        self._history.append({"role": "user", "content": user_text})
        self._trim_history()
        messages = [{"role": "system", "content": self._system_prompt}] + self._history

        stream = self._llm.create_completion(
            prompt=self._format_prompt(messages),
            max_tokens=65,
            temperature=0.55,
            top_p=0.9,
            top_k=40,
            repeat_penalty=1.3,
            stop=["<|im_end|>", "<|endoftext|>"],
            stream=True,
        )

        full_parts: list[str] = []
        for chunk in stream:
            token = chunk["choices"][0]["text"]
            if token:
                full_parts.append(token)
                yield token

        reply = _strip_markdown("".join(full_parts))
        self._history.append({"role": "assistant", "content": reply})

    def reset_history(self) -> None:
        """Clear conversation history (new customer session)."""
        self._history = []
