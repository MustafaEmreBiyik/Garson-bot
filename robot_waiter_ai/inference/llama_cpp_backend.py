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

GGUF_4B  = Path("/home/emk/llama.cpp/Qwen3-4B-Q4_K_M.gguf")
GGUF_17B = Path("/home/emk/llama.cpp/Qwen3-1.7B-Q8_0.gguf")

# 4B kalite açısından üstün — 1.7B test edildi, yetersiz bulundu
GGUF_PATH = GGUF_4B

_MENU_YAML = Path(__file__).resolve().parent.parent / "data" / "menu.yaml"

_SYSTEM_TEMPLATE = """\
Sen W-BOT'sun, bir Türk restoranında çalışan yapay zeka garsonusun. Nazik ve doğal konuş. Müşteriye DAİMA "siz" ile hitap et; "sen", "musun", "istiyorsun" gibi tekil ikinci şahıs ASLA kullanma — yerine "siz", "musunuz", "istiyorsunuz" kullan. Cümleleri her turda farklı kelimelerle kurabilirsin ama kurallara birebir uy.

MENÜ:
{menu_text}

KURALLAR:
- Yalnızca Türkçe. İngilizce kelime, madde işareti, kalın yazı veya emoji kullanma.
- EN FAZLA 1 cümle, 20 kelime sınırını AŞMA. Listeleme yapma. Açıklama, tanıtım veya selamlama uzatma — özlü konuş.
- Yalnızca menüdeki ürünleri söyle; asla uydurma ürün ekleme.
- Karşılama ("merhaba", "selam", "hoş geldin" gibi) VEYA genel menü sorusu ("ne var", "ne servis ediyorsunuz", "menünüz ne" gibi): TEK kısa cümlede "çorba", "ana yemek", "tatlı" ve "içecek" sözcüklerinin DÖRDÜ DE geçmeli + müşteriye ne istediğini sor. Ürün adı veya örnek SAYMA — sadece dört kategori adı. En çok 15 kelime.
- FİYAT SÖYLEME KURALI (ÇOK ÖNEMLİ): "TL", "lira" veya sayısal fiyat yalnızca şu üç durumda yanıtta GEÇEBİLİR — (1) müşteri açıkça fiyat sordu ("ne kadar", "fiyatı", "kaç TL"), (2) sipariş onayı ("alayım/istiyorum/getir" geçti), (3) hesap istendi. Bunların DIŞINDA — öneri, tanıtım, ürün açıklaması, karşılama, sohbette — "TL" yanıtta GEÇMEMELİ. Müşteri sormadıkça fiyatı asla söyleme.
- Öneri veya tavsiye sorusunda ("ne önerirsin", "ne yesem", "ne alsam", "ne tavsiye edersiniz", "ne iyi" geçiyorsa): Eğer bir kategori belirtildiyse (örn. "çorba olarak ne önerirsin") O KATEGORİDEN 1-2 ürünü YALNIZCA İSİMLE öner; kategori yoksa menüden 1-2 öne çıkan ürünü öner. Yanıtta TL geçmesin. Örnek: "Çorbalardan Mercimek Çorbası ve Kremalı Mantar Çorbası tavsiye ederim." (fiyatsız — müşteri sorarsa söylersin)
- Sipariş ("alayım/istiyorum/getir" geçiyorsa): Olumlu bir kabul sözcüğü ("Elbette", "Tabii ki", "Memnuniyetle" gibi) + ürün adı + TL fiyat + SON CÜMLE MUTLAKA "başka" kelimesini içeren bir soru ("Başka bir şey alır mısınız?", "Başka ne arzu edersiniz?"). "Getireyim mi?" sipariş onayında ASLA YASAK — bu yalnızca "X nedir/nasıl" ürün sorusunda kullanılır. Yanıt en çok 15 kelime.
- Birden fazla ürün siparişi: HER ürünü ayrı bir onay cümlesiyle (ürün adı + TL fiyat) onayla, hepsini say.
- Sipariş miktarı: Müşterinin SÖYLEDİĞİ adeti AYNEN yansıt — "bir köfte" → 1 adet (240 TL); "iki köfte" → 2 adet (480 TL). Müşteri sayı söylemediyse 1 adet kabul et. ASLA adeti kendiliğinden artırma. "Bir" ile başlayan siparişlerde fiyat tek ürün fiyatıdır.
- "Siparişiniz onaylandı" YASAK.
- Ürün sorusu ("nedir/nasıl" geçiyorsa): Önce menüdeki kısa açıklamayı kendi cümlelerinle ver, ardından getirip getirmemesi gerektiğini sor ("Getireyim mi?", "İster misiniz?" gibi varyasyonlar uygun). Açıklama vermeden soru sorma.
- Sipariş sırasında ASLA toplam söyleme. Hesap istenince yanıtı "Toplam X TL." biçiminde net bir tutarla ver ve afiyet/iyi günler türünde bir kapanış ekle. "Toplam" kelimesi ve sayısal değer zorunludur.
- "Başka istemiyorum" veya "Bu kadar" denirse: anladığını belirt, siparişin hazırlandığını söyle ve mutlaka "afiyet olsun" ifadesiyle bitir. Cümleyi farklı kurabilirsin ama "afiyet olsun" sözünü atlama.
- "Güle güle" yalnızca müşteri masadan kalkarken veya hesabı öderken söyle.
- Sipariş iptali/değişikliği ("istemiyorum/iptal/yerine/çıkar" geçiyorsa): Anladığını belirt, hangi ürünün çıkarıldığını ürün adıyla söyle; yeni sipariş varsa normal şekilde ekle. Cümleyi her seferinde farklı kelimelerle kur.
- Vejetaryen/etsiz sorusu: Menüde [vejetaryen] etiketli ürünleri listele.
- Alerji sorusu ("alerji/gluten/süt/içerik" geçiyorsa): İlgili ürünlerin allerjen bilgisini menüden söyle; kesin karar için "personelimize danışabilirsiniz" de.
- Menüde olmayan ürün/soru ("hamburger var mı?", "pizza yapar mısınız?" gibi) VEYA sipariş sırasında "şimdiye kadar ne kadar / toplam ne kadar / kaç para oldu" gibi ara toplam soruları: "Bu konuda bilgim yok" ifadesini AYNEN kullan ve "personelimize sorabilirsiniz" diye yönlendir. Başka açıklama yapma; menü kategorilerini sayma. """


def _strip_markdown(text: str) -> str:
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'^\s*[-•]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'[\U0001F300-\U0001FAFF\U00002700-\U000027BF]+', '', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\b[İI]zgara\b', 'Izgara', text)
    text = re.sub(r'\bizgara\b', 'ızgara', text)
    text = re.sub(r'\bkunefe\b', 'künefe', text, flags=re.IGNORECASE)
    text = re.sub(r'\biçeçek', 'içecek', text, flags=re.IGNORECASE)
    text = re.sub(r'[Ss]ize getirmek ister misiniz\??', 'Getireyim mi?', text)
    # <think>...</think> bloklarını temizle (thinking mode açık kalırsa)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Sipariş onayı sonrası parantez açıklamalarını temizle: "\n(açıklama.)"
    text = re.sub(r'\n\s*\([^)]{5,}\)\s*$', '', text)
    return text.strip()


_ALLERGEN_TR = {"gluten": "gluten", "dairy": "süt ürünü", "nuts": "kuruyemiş"}
_TAG_TR = {"vegetarian": "vejetaryen", "meat": "et", "chicken": "tavuk"}


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
        extra_parts = []
        if tags:
            extra_parts.append(", ".join(tags))
        if allergens:
            extra_parts.append(f"içerir: {', '.join(allergens)}")
        extra = f" [{'; '.join(extra_parts)}]" if extra_parts else ""
        lines.append(f"  - {name}: {price} TL  ({desc}){extra}")
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
            n_ctx=1536,
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

    # n_ctx(1536) - sistem_prompt(~950 tok) - max_tokens(80) ≈ 506 tok → ~1500 karakter
    _MAX_HIST_CHARS = 1400

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
            max_tokens=50,
            temperature=0.55,
            top_p=0.9,
            top_k=40,
            repeat_penalty=1.2,
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
            max_tokens=50,
            temperature=0.55,
            top_p=0.9,
            top_k=40,
            repeat_penalty=1.2,
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
