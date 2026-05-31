"""
scripts/compare_models.py — Qwen3-4B vs Qwen3-1.7B kalite ve hız karşılaştırması.

Kullanım:
    python3 scripts/compare_models.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from robot_waiter_ai.inference.llama_cpp_backend import (
    LlamaCppBackend, GGUF_4B, GGUF_17B
)

CONVERSATIONS = [
    [
        "Merhaba, ne yiyebilirim acaba?",
        "Çorba çeşitleriniz var mı?",
        "Mercimek çorbası alayım.",
        "Izgara köfte nasıl bir şey?",
        "O zaman onu da alayım.",
        "Başka bir şey istemiyorum.",
        "Hesabı alabilir miyim?",
    ],
    [
        "Pizza var mı menünüzde?",
        "Tatlı olarak ne önerirsiniz?",
        "Künefe alayım, içecek de limonata.",
        "Güle güle.",
    ],
    [
        "Et döner kaç lira?",
        "İki tane et döner istiyorum.",
        "Bir de ayran lütfen.",
        "Teşekkürler, hesabı getirir misiniz?",
    ],
]

SEP = "─" * 60


def run_conversation(llm: LlamaCppBackend, turns: list[str]) -> list[tuple[str, str, float]]:
    llm.reset_history()
    results = []
    for question in turns:
        t0 = time.time()
        reply = llm.generate_reply(question)
        elapsed = time.time() - t0
        results.append((question, reply, elapsed))
    return results


def print_comparison(results_4b, results_17b, conv_idx: int) -> None:
    print(f"\n{'═'*60}")
    print(f"  SENARYO {conv_idx + 1}")
    print(f"{'═'*60}")
    for i, ((q, r4, t4), (_, r17, t17)) in enumerate(zip(results_4b, results_17b)):
        print(f"\n[{i+1}] Müşteri: {q}")
        print(f"  4B  ({t4:.1f}s): {r4}")
        print(f"  1.7B({t17:.1f}s): {r17}")


def main() -> None:
    models = []
    for path, label in [(GGUF_17B, "1.7B Q8_0"), (GGUF_4B, "4B Q4_K_M")]:
        if not path.exists():
            print(f"⚠  Model bulunamadı, atlanıyor: {path.name}")
            models.append((None, label))
        else:
            print(f"Yükleniyor: {label} ...")
            models.append((LlamaCppBackend(path), label))

    llm_4b  = next((m for m, l in models if l == "4B Q4_K_M"), None)
    llm_17b = next((m for m, l in models if l == "1.7B Q8_0"), None)

    if llm_4b is None or llm_17b is None:
        print("Her iki model de gerekli. Eksik olanı indirin.")
        return

    total_4b = total_17b = 0.0
    turn_count = 0

    for ci, conversation in enumerate(CONVERSATIONS):
        r4  = run_conversation(llm_4b,  conversation)
        r17 = run_conversation(llm_17b, conversation)
        print_comparison(r4, r17, ci)

        for (_, _, t4), (_, _, t17) in zip(r4, r17):
            total_4b  += t4
            total_17b += t17
            turn_count += 1

    avg_4b  = total_4b  / turn_count
    avg_17b = total_17b / turn_count
    speedup = avg_4b / avg_17b

    print(f"\n{'═'*60}")
    print("  ÖZET")
    print(f"{'═'*60}")
    print(f"  Tur sayısı   : {turn_count}")
    print(f"  4B  ort. süre: {avg_4b:.2f} sn/yanıt")
    print(f"  1.7B ort.süre: {avg_17b:.2f} sn/yanıt")
    print(f"  Hız kazancı  : {speedup:.1f}x")
    print()


if __name__ == "__main__":
    main()
