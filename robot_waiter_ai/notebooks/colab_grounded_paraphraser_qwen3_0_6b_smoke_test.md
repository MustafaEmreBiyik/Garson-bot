# Grounded Paraphraser Colab Smoke Test

## A. Title And Warning
- This is a grounded paraphraser smoke-test notebook.
- It is not a raw waiter assistant training notebook.
- The deterministic system remains the source of truth for menu, prices, order state, and safety.
- The paraphraser must not invent menu items, prices, allergy claims, or off-topic answers.
- This notebook is not production-ready and should be treated as a pipeline validation experiment.

## B. Runtime Check
- Use Google Colab with a GPU runtime.
- GPU availability can vary by session and Colab tier.
- Run `nvidia-smi` before training and stop if no GPU is available.

## C. Project Setup
Choose one:
1. Upload the project zip manually to Colab and extract it.
2. Mount Google Drive and work from the synced project folder there.

Do not use both paths in the same run.

## D. Install Dependencies
Colab-only install set:
- `transformers`
- `datasets`
- `peft`
- `trl`
- `accelerate`
- `bitsandbytes`
- `sentencepiece`

These installs belong only inside Colab and must not be added to local requirements.

## E. Dataset Path Configuration
Use:
- `robot_waiter_ai/datasets/processed/grounded_paraphrase_train.jsonl`
- `robot_waiter_ai/datasets/processed/grounded_paraphrase_valid.jsonl`

Checks:
- train count should be `215`
- valid count should be `37`
- print 1-2 examples
- verify held-out helper files exist:
  - `robot_waiter_ai/evals/grounded_paraphrase_valid_reference.jsonl`
  - `robot_waiter_ai/evals/grounded_paraphrase_valid_output_template.jsonl`

## F. Model Configuration
Primary smoke-test model:
- `Qwen/Qwen3-0.6B`

Optional fallback:
- `Qwen/Qwen3-1.7B`

Important:
- `0.6B` is for paraphraser pipeline smoke-testing only
- it is not the final production model

## G. Formatting Function
- Use the built JSONL `messages` directly as the SFT source.
- Show a rendered prompt preview from one train example.
- Strip or block `<think>` style output.
- Force final-answer-only behavior:
  - only final answer
  - never output reasoning
  - never echo task instructions
  - never repeat forbidden examples
- Keep the task explicit:
  - preserve required terms
  - avoid forbidden terms
  - do not add new facts
  - produce natural Turkish
- Make preserve and forbidden constraints visually distinct in the prompt so the model is less likely to miss terms such as `teyit`, `Kategoriler`, `temizlendi`, and `yardımcı olamıyorum`.
- Add a small postprocess step that removes `<think>...</think>` blocks and trims instruction-like prefixes so the saved output is only the final paraphrase.

Experiment note:
- first smoke-test pass rate: `64.86%`
- this revision is for leakage reduction and constraint adherence improvement, not general quality polish

## H. LoRA/QLoRA Configuration
Use conservative settings:
- low epoch count
- small batch size
- `max_seq_length` around `512` or `1024`
- adapter-only save
- small smoke-test logging cadence

## I. Training Cell
- Include an executable training cell for Colab.
- Mark it clearly as a smoke test that must be reviewed before running.
- Do not describe it as production training.

## J. Held-Out Validation Generation
After training:
- load `grounded_paraphrase_valid_reference.jsonl`
- generate one paraphrase per held-out validation `id`
- save to `generated_grounded_paraphrase_qwen3_0_6b_smoke.jsonl`
- copy that file back into the repo as `robot_waiter_ai/evals/generated_grounded_paraphrase_qwen3_0_6b_smoke.jsonl`

Generation reminders:
- output only the final paraphrase
- do not emit reasoning or task text
- do not copy forbidden examples such as `Hamburger var`, `Hamburger mevcut`, `eklendi`, `fiyat?`, or `hava durumu`

Each output record must include:
- `id`
- `generated_paraphrase`
- `backend_name`
- `metadata`

## K. Download / Export Section
- zip adapter outputs
- download the generated validation JSONL
- bring the JSONL back into the repo at `robot_waiter_ai/evals/generated_grounded_paraphrase_qwen3_0_6b_smoke.jsonl`
- score locally with this single command:

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.evals.grounded_paraphrase_output_scorer --reference robot_waiter_ai/evals/grounded_paraphrase_valid_reference.jsonl --outputs robot_waiter_ai/evals/generated_grounded_paraphrase_qwen3_0_6b_smoke.jsonl
```

## L. Post-Run Report Template
Use this short template after a real Colab smoke test:

```text
- Colab runtime/GPU durumu:
- model indirildi mi:
- training basladi mi:
- training tamamlandi mi:
- adapter/checkpoint olustu mu:
- generated_grounded_paraphrase_qwen3_0_6b_smoke.jsonl uretildi mi:
- scorer sonucu:
- 3 basarili ornek:
- 3 basarisiz ornek:
- kisa kalite/risk yorumu:
```

Reporting reminder:
- Do not write "Model egitildi" unless training really completed and an adapter/checkpoint was produced.
- If training did not start or failed early, say that explicitly instead of implying success.
