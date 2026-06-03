#!/usr/bin/env python3
"""
train_wbot_v2.py — Qwen3-4B QLoRA SFT v2 (2 epoch, ~2216 kayıt, sıfırdan)

Colab quick-start:
    # 1. Runtime > Change runtime type > T4 GPU (ücretsiz) veya A100 (Pro)
    # 2. Google Drive bağla (tavsiye edilir — checkpoint korunur):
    #      from google.colab import drive; drive.mount('/content/drive')
    # 3. Repoyu klonla:
    #      !git clone <repo-url> /content/garson-bot
    #      %cd /content/garson-bot
    # 4. Bağımlılıkları yükle:
    #      !pip install -q torch transformers datasets accelerate peft bitsandbytes
    # 5. Eğitimi başlat:
    #      !python robot_waiter_ai/training/train_wbot_v2.py \\
    #              --drive-dir /content/drive/MyDrive/garsonbot_runs/wbot_v2

Lokal dry-run (torch gerekmez):
    python train_wbot_v2.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
_HERE      = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent
_DATASET_DEFAULT = _REPO_ROOT / "robot_waiter_ai/datasets/processed/wbot_finetune_v1.jsonl"
_OUTPUT_DEFAULT  = _REPO_ROOT / "artifacts/wbot_v2_qlora"
_EVAL_SCRIPT     = _REPO_ROOT / "scripts/eval_adapter.py"

# ── Hyperparameters ───────────────────────────────────────────────────────────
_BASE_MODEL   = "Qwen/Qwen3-4B"

_LORA_R       = 32
_LORA_ALPHA   = 64
_LORA_DROPOUT = 0.05
_TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]

# v2 defaults (v1'e göre değişenler: epochs 3→2, max_seq 1024→800, eval 50→25)
_EPOCHS      = 2
_LR          = 2e-4
_BATCH_SIZE  = 1        # per-device
_GRAD_ACCUM  = 8        # effective batch = 8
_MAX_SEQ_LEN = 800      # dataset gerçek max ~600 tok (kısa prompt); 800 yeterli
_WARMUP_RATIO = 0.05
_EVAL_STEPS  = 25
_SAVE_STEPS  = 50
_SEED        = 42
_VALID_RATIO = 0.10

# Early stopping: validation loss 3 eval adımı iyileşmezse dur
_EARLY_STOP_PATIENCE = 3

# ── Kısa sistem promptu ───────────────────────────────────────────────────────
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
                log.error("JSON parse hatası satır %d: %s", lineno, exc)
                sys.exit(1)
    return records


def split_dataset(records: list[dict], valid_ratio: float, seed: int):
    rng = random.Random(seed)
    shuffled = records.copy()
    rng.shuffle(shuffled)
    n_valid = max(1, round(len(shuffled) * valid_ratio))
    return shuffled[n_valid:], shuffled[:n_valid]


def validate_records(records: list[dict]) -> None:
    for i, r in enumerate(records[:30]):
        msgs = r.get("messages")
        if not msgs or not isinstance(msgs, list):
            raise ValueError(f"Kayıt {i}: 'messages' eksik veya liste değil")
        if msgs[0]["role"] != "system":
            raise ValueError(f"Kayıt {i}: ilk turn role='{msgs[0]['role']}', 'system' bekleniyor")
        if msgs[-1]["role"] != "assistant":
            raise ValueError(f"Kayıt {i}: son turn role='{msgs[-1]['role']}', 'assistant' bekleniyor")


# ── Model ─────────────────────────────────────────────────────────────────────

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


def load_model_and_tokenizer(base_model: str, use_gc: bool = True):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import get_peft_model, prepare_model_for_kbit_training

    log.info("Tokenizer: %s", base_model)
    tok = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "right"

    log.info("Model yükleniyor (NF4 4-bit): %s", base_model)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=make_bnb_config(),
        device_map="auto",
        trust_remote_code=True,
        dtype=torch.bfloat16,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=use_gc)
    model = get_peft_model(model, make_lora_config())
    model.print_trainable_parameters()
    return model, tok


# ── Dataset tokenization — completion-only masking ────────────────────────────

def _mask_completion_only(
    ids: list[int], asst_start: list[int], im_end: list[int]
) -> list[int]:
    labels = [-100] * len(ids)
    n_s, n_e = len(asst_start), len(im_end)
    i = 0
    while i <= len(ids) - n_s:
        if ids[i:i + n_s] == asst_start:
            j = i + n_s
            while j < len(ids):
                if ids[j:j + n_e] == im_end:
                    for k in range(n_e):
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


def build_hf_dataset(records: list[dict], tokenizer, max_length: int, short_prompt: bool = True):
    from datasets import Dataset

    asst_start = tokenizer.encode("<|im_start|>assistant\n", add_special_tokens=False)
    im_end     = tokenizer.encode("<|im_end|>",              add_special_tokens=False)
    log.info("Completion-only mask — asst_start=%s  im_end=%s", asst_start, im_end)

    rows: list[dict] = []
    n_empty = 0
    for rec in records:
        messages = rec["messages"]
        if short_prompt:
            messages = [{"role": "system", "content": _SYSTEM_SHORT}] + [
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
        rows.append({
            "input_ids":      ids,
            "attention_mask": enc["attention_mask"],
            "labels":         labels,
        })

    if n_empty:
        log.warning(
            "%d/%d kayıtta asistan token bulunamadı — asst_start IDs eşleşmiyor olabilir",
            n_empty, len(records),
        )
    log.info("Tokenize tamamlandı: %d kayıt", len(rows))
    return Dataset.from_list(rows)


# ── Smoke test ────────────────────────────────────────────────────────────────

def run_smoke_test(model, tok, system_content: str, output_dir: Path) -> None:
    import torch

    model.config.use_cache = True
    if hasattr(model, "gradient_checkpointing_disable"):
        model.gradient_checkpointing_disable()
    model.eval()

    log.info("Smoke test (%d prompt)...", len(_SMOKE_PROMPTS))
    results = []
    for prompt in _SMOKE_PROMPTS:
        msgs = [{"role": "system", "content": system_content}, {"role": "user", "content": prompt}]
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
        n_in = inputs["input_ids"].shape[1]
        response = tok.decode(out[0][n_in:], skip_special_tokens=True).strip()
        log.info("  [%s] → %s", prompt, response)
        results.append({"prompt": prompt, "response": response})

    out_file = output_dir / "smoke_generations.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log.info("Smoke sonuçları: %s", out_file)


# ── Drive sync ────────────────────────────────────────────────────────────────

def sync_to_drive(output_dir: Path, drive_dir: str) -> None:
    dst = Path(drive_dir)
    dst.mkdir(parents=True, exist_ok=True)
    log.info("Drive'a kopyalanıyor: %s → %s", output_dir, dst)
    shutil.copytree(str(output_dir), str(dst), dirs_exist_ok=True)
    log.info("Drive sync tamamlandı.")


# ── Post-training eval ────────────────────────────────────────────────────────

def run_formal_eval(adapter_dir: Path, full_prompt: bool) -> None:
    if not _EVAL_SCRIPT.exists():
        log.warning("eval_adapter.py bulunamadı: %s  (eval atlanıyor)", _EVAL_SCRIPT)
        return
    cmd = [
        sys.executable, str(_EVAL_SCRIPT),
        "--adapter-dir", str(adapter_dir),
    ]
    if full_prompt:
        cmd.append("--full-prompt")
    log.info("Formal eval başlıyor: %s", " ".join(cmd))
    subprocess.run(cmd, check=False)


# ── Training ──────────────────────────────────────────────────────────────────

def run_training(args: argparse.Namespace, output_dir: Path) -> None:
    import math
    import torch
    from transformers import (
        DataCollatorForSeq2Seq,
        EarlyStoppingCallback,
        Trainer,
        TrainingArguments,
    )

    records = load_jsonl(Path(args.dataset))
    log.info("Dataset: %d kayıt", len(records))
    validate_records(records)

    train_rec, valid_rec = split_dataset(records, _VALID_RATIO, args.seed)
    log.info("Split: %d train / %d valid", len(train_rec), len(valid_rec))

    steps_per_epoch = math.ceil(len(train_rec) / (args.batch_size * args.grad_accum))
    total_steps     = steps_per_epoch * args.epochs
    log.info(
        "Adım tahmini: %d/epoch × %d epoch = %d toplam optimizer adımı",
        steps_per_epoch, args.epochs, total_steps,
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    use_gc = not args.no_grad_checkpointing
    model, tok = load_model_and_tokenizer(args.base_model, use_gc=use_gc)

    short = not args.full_prompt
    log.info(
        "Tokenize (max_seq=%d, prompt=%s)...",
        args.max_seq_len,
        "kısa" if short else "tam",
    )
    train_ds = build_hf_dataset(train_rec, tok, args.max_seq_len, short_prompt=short)
    valid_ds  = build_hf_dataset(valid_rec, tok, args.max_seq_len, short_prompt=short)

    collator = DataCollatorForSeq2Seq(
        tokenizer=tok,
        padding=True,
        label_pad_token_id=-100,
        pad_to_multiple_of=8,
    )

    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()

    # save_steps must be a multiple of eval_steps for load_best_model_at_end
    eff_save = args.eval_steps * max(1, math.ceil(args.save_steps / args.eval_steps))
    if eff_save != args.save_steps:
        log.info("save_steps %d → %d (eval_steps katına yuvarlandı)", args.save_steps, eff_save)

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
        save_steps=eff_save,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        logging_steps=10,
        report_to="none",
        seed=args.seed,
        optim="paged_adamw_8bit",
        gradient_checkpointing=use_gc,
        dataloader_pin_memory=False,
        remove_unused_columns=False,
    )

    callbacks = [EarlyStoppingCallback(early_stopping_patience=_EARLY_STOP_PATIENCE)]

    trainer = Trainer(
        model=model,
        train_dataset=train_ds,
        eval_dataset=valid_ds,
        data_collator=collator,
        args=training_args,
        callbacks=callbacks,
    )

    log.info(
        "Eğitim başlıyor — epochs=%d  eff_batch=%d  lr=%.1e  max_seq=%d  early_stop=%d",
        args.epochs,
        args.batch_size * args.grad_accum,
        args.lr,
        args.max_seq_len,
        _EARLY_STOP_PATIENCE,
    )

    resume = getattr(args, "resume", None)
    if resume:
        resume_path = Path(resume) if resume != "auto" else True
        log.info("Checkpoint'ten devam: %s", resume)
        trainer.train(resume_from_checkpoint=resume_path)
    else:
        trainer.train()

    # ── Adapter kaydet ────────────────────────────────────────────────────────
    adapter_dir = output_dir / "adapter"
    model.save_pretrained(str(adapter_dir))
    tok.save_pretrained(str(adapter_dir))
    log.info("Adapter kaydedildi: %s", adapter_dir)

    # ── Smoke test ────────────────────────────────────────────────────────────
    system_content = records[0]["messages"][0]["content"]
    run_smoke_test(model, tok, system_content, output_dir)

    # ── Drive sync ────────────────────────────────────────────────────────────
    if args.drive_dir:
        sync_to_drive(output_dir, args.drive_dir)

    # ── Formal eval ───────────────────────────────────────────────────────────
    if args.run_eval:
        run_formal_eval(adapter_dir, args.full_prompt)


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="W-BOT v2 — Qwen3-4B QLoRA SFT (2 epoch, sıfırdan)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--base-model",  default=_BASE_MODEL,          help="HuggingFace model ID veya lokal yol")
    p.add_argument("--dataset",     default=str(_DATASET_DEFAULT), help="JSONL dataset yolu")
    p.add_argument("--output-dir",  default=str(_OUTPUT_DEFAULT),  help="Artifact çıktı dizini")
    p.add_argument("--dry-run",     action="store_true",           help="Sadece doğrula, model yükleme/eğitim yok")
    p.add_argument("--epochs",      type=int,   default=_EPOCHS)
    p.add_argument("--lr",          type=float, default=_LR)
    p.add_argument("--batch-size",  type=int,   default=_BATCH_SIZE)
    p.add_argument("--grad-accum",  type=int,   default=_GRAD_ACCUM)
    p.add_argument("--max-seq-len", type=int,   default=_MAX_SEQ_LEN)
    p.add_argument("--eval-steps",  type=int,   default=_EVAL_STEPS)
    p.add_argument("--save-steps",  type=int,   default=_SAVE_STEPS)
    p.add_argument("--seed",        type=int,   default=_SEED)
    p.add_argument(
        "--full-prompt",
        action="store_true",
        help="Dataset'teki orijinal ~2092-token sistem promptunu kullan (varsayılan: kısa ~250 tok)",
    )
    p.add_argument(
        "--no-grad-checkpointing",
        action="store_true",
        help="Gradient checkpointing kapat (~30%% hız artışı, daha fazla VRAM)",
    )
    p.add_argument(
        "--resume",
        default=None,
        metavar="CHECKPOINT_DIR|auto",
        help="Checkpoint'ten devam et. Dizin yolu ya da 'auto' (output-dir son checkpoint)",
    )
    p.add_argument(
        "--drive-dir",
        default=None,
        metavar="DRIVE_PATH",
        help="Eğitim sonunda adapter'ı bu Drive dizinine kopyala (Colab için)",
    )
    p.add_argument(
        "--run-eval",
        action="store_true",
        help="Eğitim sonunda eval_adapter.py ile 14 senaryo testini otomatik çalıştır",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    import math

    args = build_parser().parse_args(argv)
    dataset_path = Path(args.dataset)

    if not dataset_path.exists():
        log.error("Dataset bulunamadı: %s", dataset_path)
        return 1

    records = load_jsonl(dataset_path)
    validate_records(records)
    train_rec, valid_rec = split_dataset(records, _VALID_RATIO, args.seed)
    eff_batch = args.batch_size * args.grad_accum
    steps_per_epoch = math.ceil(len(train_rec) / eff_batch)

    log.info("Dataset   : %d kayıt", len(records))
    log.info("Split     : %d train / %d valid", len(train_rec), len(valid_rec))
    log.info("Model     : %s", args.base_model)
    log.info("LoRA      : r=%d  alpha=%d  modules=%s", _LORA_R, _LORA_ALPHA, ",".join(_TARGET_MODULES))
    log.info(
        "Training  : epochs=%d  eff_batch=%d  lr=%.1e  max_seq=%d",
        args.epochs, eff_batch, args.lr, args.max_seq_len,
    )
    log.info("Adımlar   : ~%d/epoch × %d = ~%d toplam", steps_per_epoch, args.epochs, steps_per_epoch * args.epochs)
    log.info("Early stop: patience=%d eval adımı", _EARLY_STOP_PATIENCE)
    log.info("Output    : %s", args.output_dir)

    if args.dry_run:
        log.info("Dry-run PASS — model yüklenmedi, eğitim başlatılmadı.")
        return 0

    run_training(args, Path(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
