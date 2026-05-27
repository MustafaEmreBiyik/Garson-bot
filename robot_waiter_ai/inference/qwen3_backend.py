"""
inference/qwen3_backend.py — Qwen3-4B conversational backend for W-BOT.

Loads Qwen3-4B with 4-bit NF4 quantization and maintains per-session
conversation history. Thinking mode is disabled for fast, direct responses.
"""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

import re

logger = logging.getLogger(__name__)

MODEL_ID = "Qwen/Qwen3-4B"


def _strip_markdown(text: str) -> str:
    """Yıldız, tire listesi ve emoji'yi temizle — TTS için düz metin."""
    text = re.sub(r'\*+', '', text)           # **bold** ve *italic*
    text = re.sub(r'^\s*[-•]\s+', '', text, flags=re.MULTILINE)  # madde işaretleri
    # emoji unicode bloklarını kaldır
    text = re.sub(r'[\U0001F300-\U0001FAFF\U00002700-\U000027BF]+', '', text)
    text = re.sub(r' {2,}', ' ', text)        # çift boşluk
    # Türkçe imla düzeltmeleri
    text = re.sub(r'\b[İI]zgara\b', 'Izgara', text)  # büyük: İzgara/Izgara → Izgara
    text = re.sub(r'\bizgara\b', 'ızgara', text)      # küçük: izgara → ızgara
    text = re.sub(r'\bkunefe\b', 'künefe', text, flags=re.IGNORECASE)
    text = re.sub(r'\biçeçek', 'içecek', text, flags=re.IGNORECASE)  # içeçek → içecek
    return text.strip()

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
- Menüyü sıralamak yerine sohbet ederek anlat. Örnek: "Çorbalarımız arasında mercimek ve kremalı mantar var."
- Kısa tut: 2-3 cümle yeterli. Müşteri daha fazla sormak isterse sorar.
- Yalnızca menüdeki ürünleri söyle, asla uydurma kelime veya ürün ekleme.
- Türkçe imla kurallarına uy: ürün adlarını menüdeki gibi yaz. Doğru: "ızgara köfte", "ızgara tavuk", "içecek". Yanlış: "izgara", "içeçek".
- Menüyü anlattıktan sonra "Ne sipariş etmek istersiniz?" veya "Size ne getirebilirim?" diye sor. "Başka bir şey alır mısınız?" SADECE müşteri sipariş verdikten sonra söyle.
- Sipariş alınca ürün adı ve fiyatıyla birlikte tekrar et, onay iste. Onaylandıktan sonra "Başka bir şey alır mısınız?" diye sor.
- Hesap sorulunca toplam tutarı düz sayıyla söyle: "Toplam 310 TL."
- Veda cümlelerini ("Güle güle", "Tekrar bekleriz") SADECE müşteri ayrılıyor veya hesabı ödüyor olduğunda söyle. Sipariş sonrası asla veda etme.
- Menüde olmayan soruları "Bu konuda bilgim yok, personelimize sorabilirsiniz." ile yanıtla."""


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


class Qwen3Backend:
    """Qwen3-4B 4-bit chat backend. Thread-safe after __init__ completes."""

    def __init__(self, model_id: str = MODEL_ID) -> None:
        self._model_id = model_id
        self._model = None
        self._tokenizer = None
        self._history: list[dict] = []
        self._system_prompt = _SYSTEM_TEMPLATE.format(menu_text=_build_menu_text())
        self._load()

    def _load(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        logger.info("Qwen3-4B yükleniyor (%s) …", self._model_id)
        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        self._tokenizer = AutoTokenizer.from_pretrained(
            self._model_id, trust_remote_code=True
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            self._model_id,
            quantization_config=bnb,
            device_map="auto",
            trust_remote_code=True,
        )
        self._model.eval()
        logger.info("Qwen3-4B hazır.")

    def generate_reply(self, user_text: str) -> str:
        """Generate a Turkish waiter reply for *user_text*, maintaining history."""
        import torch

        self._history.append({"role": "user", "content": user_text})

        messages = [{"role": "system", "content": self._system_prompt}] + self._history

        text = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = self._tokenizer(text, return_tensors="pt").to(self._model.device)

        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=150,
                do_sample=False,
                repetition_penalty=1.1,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        generated = outputs[0][inputs["input_ids"].shape[1]:]
        reply = self._tokenizer.decode(generated, skip_special_tokens=True).strip()
        reply = _strip_markdown(reply)

        self._history.append({"role": "assistant", "content": reply})
        return reply

    def reset_history(self) -> None:
        """Clear conversation history (new customer session)."""
        self._history = []
