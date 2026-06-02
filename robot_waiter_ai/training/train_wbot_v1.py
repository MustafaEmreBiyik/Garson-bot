#!/usr/bin/env python3
"""
train_wbot_v1.py — Qwen3-4B QLoRA SFT on wbot_finetune_v1.jsonl

Dependencies (install in Colab / training venv — NOT locally):
    pip install torch transformers datasets accelerate peft trl bitsandbytes

Usage:
    python train_wbot_v1.py                          # train with defaults
    python train_wbot_v1.py --dry-run                # validate only (no torch needed)
    python train_wbot_v1.py --base-model Qwen/Qwen3-4B --output-dir /path/to/out
    python train_wbot_v1.py --epochs 5 --lr 1e-4

Colab quick-start (after mounting Drive and cloning repo):
    !python robot_waiter_ai/training/train_wbot_v1.py
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent
_DATASET_DEFAULT = _REPO_ROOT / "robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl"
_OUTPUT_DEFAULT = _REPO_ROOT / "artifacts/wbot_v1_qlora"

# ── Hyperparameters ───────────────────────────────────────────────────────────
_BASE_MODEL = "Qwen/Qwen3-4B"

_LORA_R = 32
_LORA_ALPHA = 64
_LORA_DROPOUT = 0.05
# All attention + MLP projection layers
_TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

_EPOCHS = 3
_LR = 2e-4
_BATCH_SIZE = 1           # per-device; keep low for Colab T4
_GRAD_ACCUM = 8           # effective batch = 8
_MAX_SEQ_LEN = 1024       # default with --short-prompt (~700 tok/record); use 2400 with --full-prompt
_WARMUP_RATIO = 0.05
_EVAL_STEPS = 50
_SAVE_STEPS = 100
_SEED = 42
_VALID_RATIO = 0.10       # 10% → ~97 validation records

# ── Short training system prompt ───────────────────────────────────────────────
# Full system prompt: 2092 tokens/record → ~24h on T4 (session timeout).
# Short prompt:       ~250 tokens/record → ~3-4h on T4.
# Used by default; pass --full-prompt to use the original system message from the dataset.
_TRAINING_SYSTEM_SHORT = """\
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

# Smoke prompts used after training to do a quick sanity check
_SMOKE_PROMPTS = [
    "Merhaba",
    "Çorba ne var?",
    "Izgara köfte ne kadar?",
    "Hangi tatlıyı önerirsiniz?",
    "Bir mercimek çorbası alabilir miyim?",
    "Fıstık alerjim var, ne önerirsiniz?",
    "Hamburger var mı?",
]


# ── Dataset helpers ───────────────────────────────────────────────────────────

def load_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                log.error("JSON parse error at line %d: %s", lineno, exc)
                sys.exit(1)
    return records


def split_dataset(
    records: list[dict], valid_ratio: float, seed: int
) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    shuffled = records.copy()
    rng.shuffle(shuffled)
    n_valid = max(1, round(len(shuffled) * valid_ratio))
    return shuffled[n_valid:], shuffled[:n_valid]


def validate_records(records: list[dict]) -> None:
    for i, r in enumerate(records[:30]):
        msgs = r.get("messages")
        if not msgs or not isinstance(msgs, list):
            raise ValueError(f"Record {i}: 'messages' missing or not a list")
        if msgs[0]["role"] != "system":
            raise ValueError(f"Record {i}: first turn role is '{msgs[0]['role']}', expected 'system'")
        if msgs[-1]["role"] != "assistant":
            raise ValueError(f"Record {i}: last turn role is '{msgs[-1]['role']}', expected 'assistant'")


# ── Model loading ─────────────────────────────────────────────────────────────

def make_bnb_config():
    import torch
    from transformers import BitsAndBytesConfig
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )


def make_lora_config():
    from peft import LoraConfig
    return LoraConfig(
        r=_LORA_R,
        lora_alpha=_LORA_ALPHA,
        lora_dropout=_LORA_DROPOUT,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=_TARGET_MODULES,
    )


def load_model_and_tokenizer(base_model: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import get_peft_model, prepare_model_for_kbit_training

    log.info("Tokenizer yükleniyor: %s", base_model)
    tok = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "right"   # required for completion-only training

    log.info("Model yükleniyor (NF4 4-bit QLoRA): %s", base_model)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=make_bnb_config(),
        device_map="auto",
        trust_remote_code=True,
        dtype=torch.bfloat16,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, make_lora_config())
    model.print_trainable_parameters()
    return model, tok


# ── Dataset formatting + completion-only label masking ────────────────────────

def _mask_completion_only(ids: list[int], asst_start: list[int], im_end: list[int]) -> list[int]:
    """Return labels list: -100 for system/user tokens, real token IDs for assistant tokens."""
    labels = [-100] * len(ids)
    n_s, n_e = len(asst_start), len(im_end)
    i = 0
    while i <= len(ids) - n_s:
        if ids[i:i + n_s] == asst_start:
            j = i + n_s
            while j < len(ids):
                if ids[j:j + n_e] == im_end:
                    for k in range(n_e):       # include <|im_end|> so model learns to stop
                        if j + k < len(ids):
                            labels[j + k] = ids[j + k]
                    j += n_e
                    break
                labels[j] = ids[j]
                j += 1
            i = j
        else:
            i += 1
    return labels


def build_hf_dataset(
    records: list[dict],
    tokenizer,
    max_length: int,
    short_prompt: bool = True,
):
    """Tokenize records and apply completion-only label masking.

    Returns a Dataset with input_ids / attention_mask / labels fields.
    No TRL dependency — works directly with transformers.Trainer.

    short_prompt=True  : replace system message with _TRAINING_SYSTEM_SHORT (~250 tok)
    short_prompt=False : use original system message from dataset (~2092 tok, slow)
    """
    from datasets import Dataset

    asst_start = tokenizer.encode("<|im_start|>assistant\n", add_special_tokens=False)
    im_end     = tokenizer.encode("<|im_end|>",              add_special_tokens=False)
    log.info("Completion-only mask — asst_start_ids: %s  im_end_ids: %s", asst_start, im_end)

    rows: list[dict] = []
    n_empty = 0
    for rec in records:
        messages = rec["messages"]
        if short_prompt:
            # Replace the system turn with the compact training prompt
            messages = [{"role": "system", "content": _TRAINING_SYSTEM_SHORT}] + [
                m for m in messages if m["role"] != "system"
            ]
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
        enc = tokenizer(
            text, truncation=True, max_length=max_length, padding=False, return_tensors=None
        )
        ids    = enc["input_ids"]
        labels = _mask_completion_only(ids, asst_start, im_end)
        if all(l == -100 for l in labels):
            n_empty += 1
        rows.append({"input_ids": ids, "attention_mask": enc["attention_mask"], "labels": labels})

    if n_empty:
        log.warning(
            "%d/%d kayıtta asistan token'ı bulunamadı — asst_start IDs eşleşmiyor olabilir",
            n_empty, len(records),
        )
    return Dataset.from_list(rows)


# ── Training ──────────────────────────────────────────────────────────────────

def run_training(args: argparse.Namespace, output_dir: Path) -> None:
    import torch
    from transformers import DataCollatorForSeq2Seq, Trainer, TrainingArguments

    records = load_jsonl(Path(args.dataset))
    log.info("Dataset: %d records", len(records))
    validate_records(records)

    train_rec, valid_rec = split_dataset(records, _VALID_RATIO, args.seed)
    log.info("Split: %d train / %d valid", len(train_rec), len(valid_rec))

    output_dir.mkdir(parents=True, exist_ok=True)

    model, tok = load_model_and_tokenizer(args.base_model)

    # Pre-tokenize with completion-only label masking — no TRL required
    short = not args.full_prompt
    log.info(
        "Dataset tokenize ediliyor (max_seq=%d, system_prompt=%s)...",
        args.max_seq_len,
        "orijinal (~2092 tok)" if not short else "kısa (~250 tok)",
    )
    train_ds = build_hf_dataset(train_rec, tok, args.max_seq_len, short_prompt=short)
    valid_ds  = build_hf_dataset(valid_rec, tok, args.max_seq_len, short_prompt=short)

    # DataCollatorForSeq2Seq pads input_ids and propagates -100 labels correctly
    collator = DataCollatorForSeq2Seq(
        tokenizer=tok,
        padding=True,
        label_pad_token_id=-100,
        pad_to_multiple_of=8,
    )

    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=_WARMUP_RATIO,
        bf16=use_bf16,
        fp16=not use_bf16,
        eval_strategy="steps",
        eval_steps=args.eval_steps,
        save_strategy="steps",
        save_steps=args.save_steps,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        logging_steps=10,
        report_to="none",
        seed=args.seed,
        optim="paged_adamw_8bit",
        gradient_checkpointing=True,
        dataloader_pin_memory=False,
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        train_dataset=train_ds,
        eval_dataset=valid_ds,
        data_collator=collator,
        args=training_args,
    )

    log.info(
        "Eğitim başlıyor — epochs=%d  eff_batch=%d  lr=%.1e  max_seq=%d",
        args.epochs,
        args.batch_size * args.grad_accum,
        args.lr,
        args.max_seq_len,
    )
    trainer.train()

    adapter_dir = output_dir / "adapter"
    model.save_pretrained(str(adapter_dir))
    tok.save_pretrained(str(adapter_dir))
    log.info("Adapter kaydedildi: %s", adapter_dir)

    system_content = records[0]["messages"][0]["content"]
    run_smoke_test(model, tok, system_content, output_dir)


# ── Smoke test ────────────────────────────────────────────────────────────────

def run_smoke_test(model, tok, system_content: str, output_dir: Path) -> None:
    import torch

    log.info("Smoke test başlıyor (%d prompts)...", len(_SMOKE_PROMPTS))
    results = []

    for prompt in _SMOKE_PROMPTS:
        msgs = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ]
        # Apply chat template then force thinking mode off (Qwen3 convention)
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        text += "<think>\n\n</think>\n\n"

        inputs = tok(text, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=80,
                temperature=0.55,
                top_p=0.9,
                top_k=40,
                do_sample=True,
                repetition_penalty=1.2,
                pad_token_id=tok.eos_token_id,
            )
        n_prompt = inputs["input_ids"].shape[1]
        response = tok.decode(out[0][n_prompt:], skip_special_tokens=True).strip()
        log.info("  [%s] → %s", prompt, response)
        results.append({"prompt": prompt, "response": response})

    out_file = output_dir / "smoke_generations.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log.info("Smoke generations kaydedildi: %s", out_file)


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Qwen3-4B QLoRA SFT — W-BOT Turkish waiter fine-tune",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--base-model", default=_BASE_MODEL, help="HuggingFace model ID or local path")
    p.add_argument("--dataset", default=str(_DATASET_DEFAULT), help="JSONL dataset path")
    p.add_argument("--output-dir", default=str(_OUTPUT_DEFAULT), help="Artifact output directory")
    p.add_argument("--dry-run", action="store_true", help="Validate inputs and config, no training")
    p.add_argument("--epochs", type=int, default=_EPOCHS)
    p.add_argument("--lr", type=float, default=_LR)
    p.add_argument("--batch-size", type=int, default=_BATCH_SIZE)
    p.add_argument("--grad-accum", type=int, default=_GRAD_ACCUM)
    p.add_argument("--max-seq-len", type=int, default=_MAX_SEQ_LEN)
    p.add_argument("--eval-steps", type=int, default=_EVAL_STEPS)
    p.add_argument("--save-steps", type=int, default=_SAVE_STEPS)
    p.add_argument("--seed", type=int, default=_SEED)
    p.add_argument(
        "--full-prompt",
        action="store_true",
        help="Orijinal 2092-token sistem promptunu kullan (varsayılan: kısa ~250-token prompt)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dataset_path = Path(args.dataset)

    if not dataset_path.exists():
        log.error("Dataset bulunamadı: %s", dataset_path)
        return 1

    if args.dry_run:
        records = load_jsonl(dataset_path)
        validate_records(records)
        train_rec, valid_rec = split_dataset(records, _VALID_RATIO, args.seed)
        eff_batch = args.batch_size * args.grad_accum
        log.info("Dry-run PASS")
        log.info("  Dataset   : %d records", len(records))
        log.info("  Split     : %d train / %d valid", len(train_rec), len(valid_rec))
        log.info("  Model     : %s", args.base_model)
        log.info("  LoRA      : r=%d  alpha=%d  dropout=%.2f", _LORA_R, _LORA_ALPHA, _LORA_DROPOUT)
        log.info("  Training  : epochs=%d  eff_batch=%d  lr=%.1e  max_seq=%d",
                 args.epochs, eff_batch, args.lr, args.max_seq_len)
        log.info("  Output    : %s", args.output_dir)
        log.info("  (Hiçbir model yüklenmedi, eğitim başlatılmadı.)")
        return 0

    run_training(args, Path(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())