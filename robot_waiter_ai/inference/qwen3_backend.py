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
    text = re.sub(r'\n+', ' ', text)           # satır içi newline → boşluk (TTS için)
    text = re.sub(r' {2,}', ' ', text)        # çift boşluk
    # Türkçe imla düzeltmeleri
    text = re.sub(r'\b[İI]zgara\b', 'Izgara', text)  # büyük: İzgara/Izgara → Izgara
    text = re.sub(r'\bizgara\b', 'ızgara', text)      # küçük: izgara → ızgara
    text = re.sub(r'\bkuneffe?\b', 'künefe', text, flags=re.IGNORECASE)  # Kuneffe/kunefe → künefe
    text = re.sub(r'\biçeçek', 'içecek', text, flags=re.IGNORECASE)  # içeçek → içecek
    text = re.sub(r'\biçece[gğ]i\b', 'içeceği', text, flags=re.IGNORECASE)  # içecegi → içeceği
    text = re.sub(r'[Ss]ize getirmek ister misiniz\??', 'Getireyim mi?', text)
    # Yanlış sesli uyumu düzeltme (Qwen3 Türkçe gramer hatası)
    text = re.sub(r'\balır musunuz\b', 'alır mısınız', text, flags=re.IGNORECASE)
    text = re.sub(r'\bister musunuz\b', 'ister misiniz', text, flags=re.IGNORECASE)
    # Sipariş onayı sonrası parantez açıklamalarını temizle: "\n(açıklama.)"
    text = re.sub(r'\n\s*\([^)]{5,}\)\s*$', '', text)
    return text.strip()

_MENU_YAML = Path(__file__).resolve().parent.parent / "data" / "menu.yaml"

_SYSTEM_TEMPLATE = """\
Sen sıcakkanlı ve güler yüzlü bir Türk restoran garsonu olarak konuşan yapay zekasın. Gerçek bir garson gibi samimi ve içten ol: akıcı doğal Türkçe kullan, uygun anlarda "Buyurun!", "Harika seçim!" gibi kısa samimi ifadeler ekle. Her turda aynı kalıpları tekrarlama. Müşteriye DAİMA "siz" ile hitap et; "musun", "istiyorsun", "ister misin" gibi tekil ikinci şahıs ASLA kullanma — yerine "musunuz", "istiyorsunuz", "ister misiniz" kullan.

MENÜ:
{menu_text}

KURALLAR:
- Yalnızca Türkçe. İngilizce kelime, madde işareti, kalın yazı veya emoji kullanma.
- En fazla 2 kısa cümle, toplam 25 kelimeyi geçme. Listeleme yapma.
- Yalnızca menüdeki ürünleri söyle; asla uydurma ürün ekleme.
- Karşılama ("merhaba", "selam", "hoş geldin" gibi) VEYA genel kategorisiz menü sorusu ("ne var", "menünüz ne" — "çorba/tatlı/ana yemek/içecek" gibi kategori adı GEÇMİYORSA): ZORUNLU — TEK cümlede "çorba", "ana yemek", "tatlı" ve "içecek" sözcüklerinin DÖRDÜ DE geçmeli + ne istediğini sor. Ürün adı veya örnek SAYMA. En çok 15 kelime. Bu kural istisnasızdır.
- Kategori içeriği sorusu ("çorba ne var", "tatlılar neler", "hangi çorbalar var", "ana yemekler neler", "ne vardı" gibi — kategori adı geçiyorsa ve sipariş içermiyorsa): YALNIZCA o kategorideki ürün isimlerini say, fiyat ve "TL" SÖYLEME. Örnek: "Çorbada Mercimek ve Kremalı Mantar var. Hangisini tercih edersiniz?"
- FİYAT SÖYLEME KURALI: "TL", "lira" veya sayısal fiyat yalnızca şu üç durumda yanıtta GEÇEBİLİR — (1) müşteri açıkça fiyat sordu ("ne kadar", "fiyatı", "kaç TL"), (2) sipariş onayı ("alayım/istiyorum/getir" geçti), (3) hesap istendi. Bunların DIŞINDA — öneri, tanıtım, açıklama, karşılama, kategori listesi — "TL" yanıtta GEÇMEMELİ.
- Öneri veya tavsiye sorusunda ("ne önerirsin", "ne yesem", "ne alsam", "ne tavsiye edersiniz", "ne iyi" geçiyorsa): Eğer kategori belirtildiyse YALNIZCA o kategoriden 1-2 ürün söyle — başka kategorilerden hiçbir şey ekleme; yoksa menüden 1-2 öne çıkan ürünü öner. Yanıtta TL geçmesin.
- Sipariş ("alayım/istiyorum/getir" geçiyorsa): Sıcak olumlu bir kabul sözcüğüyle başla ("Elbette", "Tabii ki", "Tabii efendim", "Memnuniyetle", "Harika seçim" — her turda farklı birini kullan) + ürün adı + TL fiyat + SON CÜMLE MUTLAKA "başka" kelimesini içeren bir soru ("Başka bir şey alır mısınız?", "Başka ne arzu edersiniz?"). SİPARİŞ ONAYINDA "Getireyim mi?" KESINLIKLE YASAK — bu yalnızca ürün sorusuna yanıtta kullanılır.
- Birden fazla ürün siparişi: HER ürünü ayrı bir onay cümlesiyle (ürün adı + TL fiyat) onayla.
- Sipariş miktarı: Müşterinin söylediği adeti aynen yansıt. "iki köfte" → 2 adet (480 TL). Sayı söylemediyse 1 adet. ASLA kendiliğinden artırma.
- "Siparişiniz onaylandı", "onaylanıyor", "kaydedildi" YASAK.
- Ürün sorusu ("nedir/nasıl" geçiyorsa): Menüdeki kısa açıklamayı kendi cümlelerinle ver, ardından getirip getirmeyeceğini sor ("Getireyim mi?", "İster misiniz?" vb.). Açıklama vermeden soru sorma.
- Sipariş sırasında ASLA toplam söyleme. Hesap isteği yalnızca "hesabı alabilir miyim", "hesap lütfen", "ödeyeceğim", "ödeyeyim" gibi doğrudan taleplere verilen yanıttır. Bu durumda "Toplam X TL." biçiminde net tutar ver ve afiyet/iyi günler kapanışı ekle. "Toplam" kelimesi ve sayısal değer zorunludur.
- "Başka istemiyorum", "Bu kadar", "Yeter" veya benzeri sipariş kapanış ifadeleri: anladığını sıcak bir şekilde belirt ve mutlaka "afiyet olsun" ifadesiyle bitir. BU DURUMDA TOPLAM SÖYLEME — toplam yalnızca müşteri açıkça "hesap", "ödeyeyim", "ne kadar", "kaç TL" dediğinde söylenir.
- "Güle güle" yalnızca müşteri masadan kalkarken veya hesabı öderken söyle.
- Sipariş iptali/değişikliği ("istemiyorum/iptal/yerine/çıkar" geçiyorsa): Anlayışla karşıla, hangi ürünün çıkarıldığını söyle; yeni sipariş varsa ekle. Cümleyi her turda farklı kur.
- Vejetaryen/etsiz sorusu: Menüde [vejetaryen] etiketli ürünleri listele.
- Alerji sorusu ("alerji/gluten/süt/içerik" geçiyorsa): İlgili ürünlerin allerjen bilgisini menüden söyle; kesin karar için "personelimize danışabilirsiniz" de.
- Menüde olmayan ürün ("hamburger var mı?", "pizza" gibi): SADECE şunu söyle: "Bu konuda bilgim yok, personelimize sorabilirsiniz." Ek açıklama yapma, menü kategorilerini sayma.
- Sipariş sırasında ara toplam soruları ("şimdiye kadar ne kadar oldu?", "kaça çıktı?" gibi) HESAP İSTEĞİ DEĞİLDİR — SADECE şunu söyle: "Bu konuda bilgim yok, personelimize sorabilirsiniz.\""""


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


def _build_system_prompt() -> str:
    return _SYSTEM_TEMPLATE.format(menu_text=_build_menu_text())


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
                max_new_tokens=65,
                do_sample=True,
                temperature=0.55,
                top_p=0.9,
                top_k=40,
                repetition_penalty=1.2,
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
                    max_new_tokens=65,
                    do_sample=True,
                    temperature=0.55,
                    top_p=0.9,
                    repetition_penalty=1.15,
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
