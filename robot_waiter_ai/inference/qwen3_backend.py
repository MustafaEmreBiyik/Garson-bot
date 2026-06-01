"""
inference/qwen3_backend.py — Qwen3-4B conversational backend for W-BOT.

Loads Qwen3-4B with 4-bit NF4 quantization and maintains per-session
conversation history. Thinking mode is disabled for fast, direct responses.
"""
from __future__ import annotations

import logging
import threading
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
    text = re.sub(r'[Ss]ize getirmek ister misiniz\??', 'Getireyim mi?', text)
    # Sipariş onayı sonrası parantez açıklamalarını temizle: "\n(açıklama.)"
    text = re.sub(r'\n\s*\([^)]{5,}\)\s*$', '', text)
    return text.strip()

_MENU_YAML = Path(__file__).resolve().parent.parent / "data" / "menu.yaml"

_SYSTEM_TEMPLATE = """\
Sen W-BOT'sun, bir Türk restoranında çalışan yapay zeka garsonusun. Nazik ve doğal konuş. Müşteriye daima "siz" ile hitap et; hiçbir zaman "sen" kullanma.

MENÜ:
{menu_text}

KURALLAR:
- Yalnızca Türkçe. İngilizce kelime, madde işareti, kalın yazı veya emoji kullanma.
- 1-2 cümle yeterli.
- Yalnızca menüdeki ürünleri söyle; asla uydurma ürün ekleme.
- Genel menü sorusunda ("ne var", "ne servis ediyorsunuz", "menünüz ne" gibi): "Çorbalar, ana yemekler, tatlılar ve içecekler var. Ne istersiniz?" Tam liste verme.
- Öneri veya tavsiye sorusunda ("ne önerirsin", "ne yesem", "ne alsam", "ne tavsiye edersiniz", "ne iyi" geçiyorsa): Menüden 1-2 öne çıkan ürünü isim ve fiyatıyla öner. Örnek: "Izgara Köfte çok beğeniliyor, 240 TL. İsterseniz Mercimek Çorbası da güzel bir başlangıç, 85 TL. Ne istersiniz?"
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
        # local_files_only=True: ilk indirimden sonra HF Hub'a istek atmaz; ağ gerekmez.
        # Model cache'te yoksa OSError → tekrar dene (ilk çalıştırma).
        _shared = dict(trust_remote_code=True, local_files_only=True)
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(self._model_id, **_shared)
            self._model = AutoModelForCausalLM.from_pretrained(
                self._model_id, quantization_config=bnb, device_map="auto", **_shared
            )
        except OSError:
            logger.warning("Model cache'te yok, HuggingFace Hub'dan indiriliyor…")
            self._tokenizer = AutoTokenizer.from_pretrained(
                self._model_id, trust_remote_code=True
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                self._model_id, quantization_config=bnb, device_map="auto",
                trust_remote_code=True,
            )
        self._model.eval()
        if torch.cuda.is_available():
            used  = torch.cuda.memory_allocated() / 1024 ** 3
            total = torch.cuda.get_device_properties(0).total_memory / 1024 ** 3
            logger.info("Qwen3-4B hazır. VRAM: %.2f GB / %.2f GB", used, total)
            print(f"  VRAM: {used:.2f} GB kullanımda / {total:.2f} GB toplam")
        else:
            logger.info("Qwen3-4B hazır (CPU).")

    _MAX_HIST_CHARS = 12000

    def _trim_history(self) -> None:
        """Çok uzun geçmişi kısalt — en eski user+assistant turlarını at."""
        while len(self._history) > 1:
            total = sum(len(m["content"]) for m in self._history)
            if total <= self._MAX_HIST_CHARS:
                break
            if len(self._history) >= 3:
                self._history = self._history[2:]
                logger.warning("Geçmiş kısaltıldı — %d mesaj kaldı.", len(self._history))
            else:
                break

    def generate_reply(self, user_text: str) -> str:
        """Generate a Turkish waiter reply for *user_text*, maintaining history."""
        import torch

        self._history.append({"role": "user", "content": user_text})
        self._trim_history()

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
                max_new_tokens=80,
                do_sample=False,
                repetition_penalty=1.1,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        generated = outputs[0][inputs["input_ids"].shape[1]:]
        reply = self._tokenizer.decode(generated, skip_special_tokens=True).strip()
        reply = _strip_markdown(reply)

        self._history.append({"role": "assistant", "content": reply})
        return reply

    def stream_reply(self, user_text: str):
        """Generate reply as a token stream; yields raw tokens one by one.

        History is updated after all tokens are consumed (generator exhausted).
        """
        from transformers import TextIteratorStreamer
        import torch

        self._history.append({"role": "user", "content": user_text})
        self._trim_history()
        messages = [{"role": "system", "content": self._system_prompt}] + self._history

        text = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = self._tokenizer(text, return_tensors="pt").to(self._model.device)

        # timeout=30: gen_thread CUDA/OOM hatasında streamer sonsuza dek bloklanmasın
        streamer = TextIteratorStreamer(
            self._tokenizer, skip_prompt=True, skip_special_tokens=True, timeout=30.0
        )

        def _generate_safe():
            try:
                self._model.generate(**dict(
                    **inputs,
                    max_new_tokens=80,
                    do_sample=False,
                    repetition_penalty=1.1,
                    pad_token_id=self._tokenizer.eos_token_id,
                    streamer=streamer,
                ))
            except Exception as exc:
                logger.error("model.generate hatası: %s", exc)
                # Streamer'a dur sinyali gönder; yoksa for döngüsü sonsuza bloklanır
                try:
                    streamer.text_queue.put(streamer.stop_signal)
                except Exception:
                    pass

        gen_thread = threading.Thread(target=_generate_safe, daemon=True)
        gen_thread.start()

        full_parts: list[str] = []
        try:
            for token in streamer:
                full_parts.append(token)
                yield token
        except Exception as exc:
            logger.error("Streamer hatası: %s", exc)

        gen_thread.join(timeout=10)
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        reply = _strip_markdown("".join(full_parts))
        self._history.append({"role": "assistant", "content": reply})

    def reset_history(self) -> None:
        """Clear conversation history (new customer session)."""
        self._history = []
