#!/usr/bin/env python3
"""
eval_adapter.py — wbot_v1_qlora fine-tune kalite değerlendirmesi

Colab kullanımı:
    !python scripts/eval_adapter.py \
        --adapter-dir /content/drive/MyDrive/garsonbot_runs/wbot_v1_qlora/adapter

Bayraklar:
    --adapter-dir   Adapter dizini (zorunlu)
    --base-model    Temel model (varsayılan: Qwen/Qwen3-4B)
    --full-prompt   Kısa eğitim promptu yerine tam sistem promptunu kullan
    --smoke-only    Sadece 7 smoke promptu çalıştır, formal eval atla
    --no-quant      4-bit quantization olmadan yükle (daha fazla VRAM gerekir)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ── Kısa sistem promptu (eğitimde kullanılan) ─────────────────────────────────
_SYSTEM_SHORT = """\
Sen sıcakkanlı bir Türk restoran garsonu yapay zekasısın. Akıcı doğal Türkçe kullan. \
Müşteriye DAİMA "siz" ile hitap et; "musun"/"ister misin" YASAK, "musunuz"/"ister misiniz" kullan.

MENÜ:
Çorba: Mercimek Çorbası 85 TL, Kremalı Mantar Çorbası 95 TL
Ana Yemek: Izgara Köfte 240 TL, Et Döner 280 TL, Izgara Tavuk Salata 210 TL
Tatlı: Fırın Sütlaç 100 TL, Künefe 140 TL
İçecek: Yayık Ayran 45 TL, Limonata 70 TL, Şalgam Suyu 50 TL

KURALLAR:
- Yalnızca Türkçe. Madde işareti, kalın yazı, emoji yok. En fazla 2 cümle, 25 kelime.
- Karşılama VEYA genel menü sorusu (kategori adı geçmiyorsa): "çorba, ana yemek, tatlı, içecek" \
dördü TEK cümlede geçmeli. Max 15 kelime. Ürün adı sayma.
- Kategori sorusu ("çorba ne var" gibi): YALNIZCA o kategorideki isimleri say, fiyat söyleme.
- FİYAT: yalnızca (1) fiyat sorusu, (2) sipariş onayı, (3) hesap. Diğerinde "TL" geçmesin.
- Öneri sorusu: kategori belirtildiyse YALNIZCA o kategoriden 1-2 ürün. Başka kategori ekleme.
- Sipariş onayı: sıcak kabul + ürün adı + TL fiyat + "başka" sorusu. "Getireyim mi?" YASAK.
- Birden fazla sipariş: her ürünü ayrı cümleyle onayla.
- Hesap: "Toplam X TL." + afiyet/iyi günler kapanışı.
- Menüde olmayan ürün: "Bu konuda bilgim yok, personelimize sorabilirsiniz."
- "Siparişiniz onaylandı", "onaylanıyor", "kaydedildi" YASAK.\
"""

# ── Smoke prompts ─────────────────────────────────────────────────────────────
_SMOKE_PROMPTS = [
    "Merhaba",
    "Çorba ne var?",
    "Izgara köfte ne kadar?",
    "Hangi tatlıyı önerirsiniz?",
    "Bir mercimek çorbası alabilir miyim?",
    "Fıstık alerjim var, ne önerirsiniz?",
    "Hamburger var mı?",
]

# ── Formal eval senaryoları ───────────────────────────────────────────────────
# Her senaryo: (id, açıklama, kullanıcı mesajı, kontrol fonksiyonu)
# Kontrol: f(yanıt: str) -> bool
def _contains(*words):
    """Tüm kelimeler yanıtta olmalı."""
    def check(r): return all(w.lower() in r.lower() for w in words)
    return check

def _any_of(*words):
    """En az bir kelime yanıtta olmalı."""
    def check(r): return any(w.lower() in r.lower() for w in words)
    return check

def _not_contains(*words):
    def check(r): return all(w.lower() not in r.lower() for w in words)
    return check

def _both(f1, f2):
    def check(r): return f1(r) and f2(r)
    return check

_EVAL_CASES = [
    # Karşılama — 4 kategori adı geçmeli, ürün adı saymamalı
    ("E01", "Karşılama — 4 kategori adı",
     "Merhaba",
     _both(
         _contains("çorba", "ana yemek", "tatlı", "içecek"),
         _not_contains("köfte", "ayran", "sütlaç", "limonata"),
     )),

    # Genel menü sorusu — aynı kural
    ("E02", "Genel menü sorusu",
     "Ne yiyebilirim?",
     _contains("çorba", "ana yemek", "tatlı", "içecek")),

    # Sipariş onayı — fiyat + başka sorusu
    ("E03", "Sipariş onayı — fiyat + başka sorusu",
     "Bir mercimek çorbası istiyorum.",
     _both(_contains("85"), _contains("başka"))),

    # Sipariş iptali
    ("E04", "Sipariş iptali onayı",
     "Aslında çorbayı istemiyorum, iptal edin.",
     _any_of("çıkar", "iptal", "kaldır", "tamam", "anladım")),

    # Fiyat sorusu — TL söylemeli
    ("E05", "Fiyat sorusu",
     "Izgara köftenin fiyatı ne kadar?",
     _contains("240")),

    # Kategori sorusu — fiyat söylememeli (W13)
    ("E06", "Kategori listesi — fiyat yasağı (W13)",
     "Çorba ne var?",
     _both(
         _contains("mercimek", "mantar"),
         _not_contains("tl", "85", "95"),
     )),

    # Kategori önerisi — başka kategori eklememeli (W14)
    ("E07", "Öneri — kategori dışına çıkma yasağı (W14)",
     "Tatlı olarak ne önerirsiniz?",
     _both(
         _any_of("sütlaç", "künefe"),
         _not_contains("köfte", "döner", "çorba", "ayran"),
     )),

    # Hesap — toplam söylemeli, ama önceden söylememeli
    ("E08", "Hesap isteği",
     "Hesabı alabilir miyim?",
     _contains("toplam")),

    # Menüde olmayan ürün
    ("E09", "Menüde olmayan ürün",
     "Hamburger var mı?",
     _contains("bilgim yok", "personel")),

    # Konu dışı refusal
    ("E10", "Konu dışı — yardım reddi",
     "Bana bir şiir yazar mısınız?",
     _not_contains("şiir")),

    # Alerji uyarısı
    ("E11", "Alerji sorusu",
     "Fıstık alerjim var, ne önerirsiniz?",
     _not_contains("fıstık")),

    # "siz" hitabı — "sen" olmamalı
    ("E12", "Hitap biçimi — siz formu",
     "Bana bir şey önerir misiniz?",
     _not_contains(" sen ", "ister misin", "musun")),

    # Markdown / emoji yok
    ("E13", "Markdown yasağı",
     "Menünüzde neler var?",
     _not_contains("**", "##", "- ", "* ")),

    # "Getireyim mi?" yasağı — sipariş onayında kullanılmamalı
    ("E14", '"Getireyim mi?" yasağı',
     "Bir ayran alabilir miyim?",
     _both(
         _contains("45"),
         _not_contains("getireyim mi"),
     )),
]


def load_model(adapter_dir: str, base_model: str, use_quant: bool):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    print(f"Tokenizer yükleniyor: {base_model}")
    tok = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    print(f"Base model yükleniyor: {base_model}")
    if use_quant:
        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            quantization_config=bnb,
            device_map="auto",
            trust_remote_code=True,
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
        )

    print(f"Adapter yükleniyor: {adapter_dir}")
    model = PeftModel.from_pretrained(model, adapter_dir)
    model.eval()
    model.config.use_cache = True
    print("Model hazır.\n")
    return model, tok


def generate(model, tok, system: str, user: str, max_new_tokens: int = 80) -> str:
    import torch
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    text += "<think>\n\n</think>\n\n"
    inputs = tok(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.55,
            top_p=0.9,
            top_k=40,
            do_sample=True,
            repetition_penalty=1.2,
            pad_token_id=tok.eos_token_id,
        )
    n = inputs["input_ids"].shape[1]
    return tok.decode(out[0][n:], skip_special_tokens=True).strip()


def run_smoke(model, tok, system: str) -> None:
    print("=" * 60)
    print("SMOKE TEST")
    print("=" * 60)
    for prompt in _SMOKE_PROMPTS:
        resp = generate(model, tok, system, prompt)
        print(f"\n[{prompt}]\n→ {resp}")
    print()


def run_eval(model, tok, system: str) -> None:
    print("=" * 60)
    print("FORMAL EVAL")
    print("=" * 60)
    passed, failed = 0, 0
    for case_id, desc, user_msg, check_fn in _EVAL_CASES:
        resp = generate(model, tok, system, user_msg)
        ok = check_fn(resp)
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"\n[{case_id}] {status} — {desc}")
        print(f"  Kullanıcı : {user_msg}")
        print(f"  Yanıt     : {resp}")
    total = passed + failed
    print("\n" + "=" * 60)
    print(f"SONUÇ: {passed}/{total} PASS ({100*passed//total}%)")
    print("=" * 60)


def main(argv=None):
    p = argparse.ArgumentParser(
        description="wbot_v1_qlora adapter değerlendirmesi",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--adapter-dir", required=True, help="Adapter dizini")
    p.add_argument("--base-model", default="Qwen/Qwen3-4B")
    p.add_argument("--full-prompt", action="store_true",
                   help="Kısa eğitim promptu yerine qwen3_backend sistem promptunu kullan")
    p.add_argument("--smoke-only", action="store_true",
                   help="Sadece smoke testi çalıştır")
    p.add_argument("--no-quant", action="store_true",
                   help="4-bit quantization olmadan yükle")
    args = p.parse_args(argv)

    if args.full_prompt:
        # qwen3_backend.py'deki tam sistem promptunu dinamik olarak yükle
        repo_root = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(repo_root))
        from robot_waiter_ai.inference.qwen3_backend import _build_system_prompt
        system = _build_system_prompt()
        print("Sistem promptu: TAM (qwen3_backend)\n")
    else:
        system = _SYSTEM_SHORT
        print("Sistem promptu: KISA (eğitim promptu)\n")

    model, tok = load_model(args.adapter_dir, args.base_model, use_quant=not args.no_quant)

    run_smoke(model, tok, system)
    if not args.smoke_only:
        run_eval(model, tok, system)


if __name__ == "__main__":
    main()
