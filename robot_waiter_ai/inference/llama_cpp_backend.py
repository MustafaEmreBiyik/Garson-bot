"""
inference/llama_cpp_backend.py — Qwen3-4B GGUF backend for Jetson (llama-cpp-python).

Drop-in replacement for qwen3_backend.Qwen3Backend.
Uses llama-cpp-python with full CUDA offload (SM87, Jetson Orin NX).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

GGUF_4B  = Path("/home/emk/llama.cpp/Qwen3-4B-Q4_K_M.gguf")
GGUF_17B = Path("/home/emk/llama.cpp/Qwen3-1.7B-Q8_0.gguf")

# 4B kalite açısından üstün — 1.7B test edildi, yetersiz bulundu
GGUF_PATH = GGUF_4B

_MENU_YAML = Path(__file__).resolve().parent.parent / "data" / "menu.yaml"

_SYSTEM_TEMPLATE = """\
Sen W-BOT'sun, bir Türk restoranında çalışan nazik ve sıcakkanlı yapay zeka garsonusun.
Müşterileri içtenlikle karşıla, menüyü doğal bir şekilde anlat, sipariş al.

MENÜ:
{menu_text}

KURALLAR:
- Sadece Türkçe konuş.
- Doğal ve akıcı cümleler kur, sanki gerçek bir garson gibi konuş.
- Kesinlikle madde işareti (*), tire listesi (-), kalın yazı (**) veya emoji kullanma. Sadece düz Türkçe cümle.
- İlk karşılamada menü kategorilerini say, ürünleri tek tek listeleme: "Çorbalar, ana yemekler, tatlılar ve içecekler var. Ne istersiniz?" gibi. Asla tam liste verme.
- Kısa tut: 1-2 cümle yeterli. Müşteri daha fazla sormak isterse sorar.
- Yalnızca menüdeki ürünleri söyle, asla uydurma kelime veya ürün ekleme.
- Türkçe imla kurallarına uy: ürün adlarını menüdeki gibi yaz. Doğru: "ızgara köfte", "ızgara tavuk", "içecek". Yanlış: "izgara", "içeçek".
- Menüyü anlattıktan sonra "Ne sipariş etmek istersiniz?" veya "Size ne getirebilirim?" diye sor. "Başka bir şey alır mısınız?" SADECE müşteri sipariş verdikten sonra söyle.
- Müşteri bir şey istediğinde direkt sipariş olarak al. Format: "Elbette, [ürün adı] [fiyat] TL eklendi. Başka bir şey alır mısınız?" Bu cümleden sonra HIÇBIR ŞEY yazma — açıklama, parantez, yorum yok.
- Müşteri tek seferde birden fazla ürün istediğinde her birini ayrı cümleyle onayla: "Elbette, ızgara köfte 240 TL eklendi. Yayık ayran 45 TL eklendi. Başka bir şey alır mısınız?"
- "Siparişiniz onaylandı" ifadesini HİÇBİR ZAMAN kullanma. Bu ifade yasaktır.
- Ürün hakkında soru gelince kısa bilgi ver ve "Getireyim mi?" diye sor. "Size getirmek ister misiniz?" ifadesini kullanma.
- Sipariş alırken ASLA toplam söyleme. Yanlış: "Izgara köfte eklendi, toplam 325 TL." Doğru: "Elbette, ızgara köfte 240 TL eklendi. Başka bir şey alır mısınız?"
- Toplam tutarı YALNIZCA müşteri açıkça hesap istediğinde söyle ("hesabı alabilir miyim", "hesap lütfen", "ödeyeyim"). Örnek yanıt: "Toplam 325 TL. Afiyet olsun!"
- Müşteri "Başka bir şey istemiyorum / Bu kadar / Hepsi bu" derse "Anladım, siparişiniz hazırlanıyor. Afiyet olsun!" de, veda etme. "Güle güle" yalnızca müşteri masadan kalkıp ayrılırken veya hesabı öderken söyle.
- "Size yardımcı oldum", "Satıyoruz" gibi robotik ifadeler kullanma. Doğal garson dili kullan.
- Menüde olmayan soruları "Bu konuda bilgim yok, personelimize sorabilirsiniz." ile yanıtla."""


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
        lines.append(f"  - {name}: {price} TL  ({desc})")
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
            n_ctx=2048,
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
            max_tokens=100,
            temperature=0.0,
            repeat_penalty=1.1,
            stop=["<|im_end|>", "<|endoftext|>"],
        )

        reply = result["choices"][0]["text"].strip()
        reply = _strip_markdown(reply)

        self._history.append({"role": "assistant", "content": reply})
        return reply

    def reset_history(self) -> None:
        """Clear conversation history (new customer session)."""
        self._history = []
