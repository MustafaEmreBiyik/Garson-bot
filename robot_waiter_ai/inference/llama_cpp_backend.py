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
Sen W-BOT'sun, bir Türk restoranında çalışan yapay zeka garsonusun. Nazik ve doğal konuş. Müşteriye daima "siz" ile hitap et; hiçbir zaman "sen" kullanma.

MENÜ:
{menu_text}

KURALLAR:
- Yalnızca Türkçe. İngilizce kelime, madde işareti, kalın yazı veya emoji kullanma.
- 1-2 cümle yeterli.
- Yalnızca menüdeki ürünleri söyle; asla uydurma ürün ekleme.
- Karşılamada kategori özeti ver: "Çorbalar, ana yemekler, tatlılar ve içecekler var. Ne istersiniz?" Tam liste verme.
- Sipariş ("alayım/istiyorum/getir" geçiyorsa): "Elbette, [ürün] [fiyat] TL eklendi. Başka bir şey alır mısınız?" Bu kalıptan sonra hiçbir şey ekleme.
- Birden fazla ürün siparişi: HER ürünü ayrı "Elbette, [ürün] [fiyat] TL eklendi." cümlesiyle onayla, hepsini say.
- Sipariş miktarı ("iki/üç/dört/2/3/4" geçiyorsa): Onayda adeti ve toplam fiyatı yaz. Örnek: "iki köfte" → "Elbette, iki Izgara Köfte 480 TL eklendi. Başka bir şey alır mısınız?"
- "Siparişiniz onaylandı" YASAK.
- Ürün sorusu ("nedir/nasıl" geçiyorsa): ÖNCE menüdeki açıklamayı söyle, SONRA "Getireyim mi?" diye sor. Açıklama olmadan "Getireyim mi?" deme.
- Sipariş sırasında ASLA toplam söyleme. Toplam yalnızca hesap istenince: "Toplam X TL. Afiyet olsun!"
- "Başka istemiyorum" veya "Bu kadar" → "Anladım, siparişiniz hazırlanıyor. Afiyet olsun!" de.
- "Güle güle" yalnızca müşteri masadan kalkarken veya hesabı öderken söyle.
- Sipariş iptali/değişikliği ("istemiyorum/iptal/yerine/çıkar" geçiyorsa): "Anladım, [ürün] siparişinizden çıkarıldı." de; yeni sipariş varsa normal şekilde ekle.
- Vejetaryen/etsiz sorusu: Menüde [vejetaryen] etiketli ürünleri listele.
- Alerji sorusu ("alerji/gluten/süt/içerik" geçiyorsa): İlgili ürünlerin allerjen bilgisini menüden söyle; kesin karar için "personelimize danışabilirsiniz" de.
- Menüde olmayan soru: "Bu konuda bilgim yok, personelimize sorabilirsiniz." """


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

    def generate_reply(self, user_text: str) -> str:
        """Generate a Turkish waiter reply, maintaining conversation history."""
        self._history.append({"role": "user", "content": user_text})

        messages = [{"role": "system", "content": self._system_prompt}] + self._history

        result = self._llm.create_completion(
            prompt=self._format_prompt(messages),
            max_tokens=80,
            temperature=0.0,
            repeat_penalty=1.1,
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
        messages = [{"role": "system", "content": self._system_prompt}] + self._history

        stream = self._llm.create_completion(
            prompt=self._format_prompt(messages),
            max_tokens=80,
            temperature=0.0,
            repeat_penalty=1.1,
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
