"""
scripts/eval_llm.py — LLM kalite ve performans değerlendirmesi.

Kullanım:
    python3 scripts/eval_llm.py [--backend llama|qwen]

Her senaryo için:
  - Beklenen davranış kontrol edilir (PASS/FAIL)
  - Yanıt süresi ölçülür
  - Token sayısı gösterilir
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Test senaryoları
# ---------------------------------------------------------------------------

@dataclass
class Scenario:
    id: str
    turns: list[str]                   # sıralı kullanıcı mesajları
    checks: list[dict]                 # her turn için kontroller
    description: str = ""

def _check(reply: str, must_contain: list[str] = (), must_not_contain: list[str] = (),
           regex: str = "") -> tuple[bool, str]:
    r = reply.lower()
    for phrase in must_contain:
        if phrase.lower() not in r:
            return False, f"EKSİK: '{phrase}'"
    for phrase in must_not_contain:
        if phrase.lower() in r:
            return False, f"YASAK KELİME: '{phrase}'"
    if regex and not re.search(regex, reply, re.IGNORECASE | re.DOTALL):
        return False, f"REGEX UYUŞMADI: {regex}"
    return True, "OK"


SCENARIOS: list[Scenario] = [
    Scenario(
        id="S01",
        description="Karşılama — kategori özeti verilmeli, liste yok",
        turns=["Merhaba."],
        checks=[{
            "must_contain": ["çorba", "ana yemek", "tatlı", "içecek"],
            "must_not_contain": ["mercimek", "köfte", "döner", "sütlaç", "künefe",
                                  "ayran", "limonata", "siparişiniz onaylandı"],
        }],
    ),
    Scenario(
        id="S02",
        description="Öneri sorusu — ürün açıklanmalı, Getireyim mi? sorulmalı",
        turns=["Merhaba.", "Çorba olarak ne önerirsiniz?"],
        checks=[
            {"must_contain": ["çorba", "içecek", "tatlı"]},   # turn 1
            {
                "must_contain": ["mercimek", "mantar"],
                "must_not_contain": ["siparişiniz onaylandı", "başka bir şey"],
            },
        ],
    ),
    Scenario(
        id="S03",
        description="Ürün sorusu — kısa açıklama + Getireyim mi?",
        turns=["Künefe nedir?"],
        checks=[{
            "must_contain": ["kadayıf"],
            "regex": r"getireyim mi",
        }],
    ),
    Scenario(
        id="S04",
        description="Tek ürün siparişi — doğru fiyat, doğru format",
        turns=["Bir mercimek çorbası alayım."],
        checks=[{
            "must_contain": ["mercimek çorbası", "85"],
            "must_not_contain": ["siparişiniz onaylandı"],
            "regex": r"elbette",
        }],
    ),
    Scenario(
        id="S05",
        description="Çoklu ürün siparişi — her ürün ayrı cümle",
        turns=["Bir izgara köfte ve bir ayran istiyorum."],
        checks=[{
            "must_contain": ["240", "45"],
            "must_not_contain": ["siparişiniz onaylandı"],
        }],
    ),
    Scenario(
        id="S06",
        description="Sipariş sırasında toplam yasak",
        turns=[
            "Bir mercimek çorbası alayım.",
            "Bir de künefe.",
            "Şimdiye kadar ne kadar oldu?",
        ],
        checks=[
            {"must_contain": ["85"]},
            {"must_contain": ["140"]},
            {"must_not_contain": ["225", "toplam"],
             "must_contain": ["bilgim yok", "personel"]},
        ],
    ),
    Scenario(
        id="S07",
        description="Hesap isteği — doğru toplam gösterilmeli",
        turns=[
            "Bir et döner alayım.",
            "Bir de fırın sütlaç.",
            "Hesabı alabilir miyim?",
        ],
        checks=[
            {"must_contain": ["280"]},
            {"must_contain": ["100"]},
            {"must_contain": ["380"], "regex": r"toplam"},
        ],
    ),
    Scenario(
        id="S08",
        description="Siparişi bitirme — afiyet olsun",
        turns=[
            "Bir limonata alayım.",
            "Başka bir şey istemiyorum.",
        ],
        checks=[
            {"must_contain": ["70"]},
            {"must_contain": ["afiyet olsun"],
             "must_not_contain": ["güle güle"]},
        ],
    ),
    Scenario(
        id="S09",
        description="Menüde olmayan ürün sorusu",
        turns=["Hamburger var mı?"],
        checks=[{
            "must_contain": ["bilgim yok", "personel"],
            "must_not_contain": ["hamburger"],
        }],
    ),
    Scenario(
        id="S10",
        description="Sipariş onayı sonrası ekstra yok",
        turns=["Bir şalgam suyu alayım."],
        checks=[{
            "must_contain": ["50"],
            "must_not_contain": ["siparişiniz onaylandı"],
            # "başka" kelimesi + soru: "başka bir şey alır mısınız?", "başka ne arzu edersiniz?" vs.
            "regex": r"başka.{0,40}\?",
        }],
    ),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

@dataclass
class Result:
    scenario_id: str
    turn: int
    user: str
    reply: str
    elapsed_ms: float
    passed: bool
    reason: str


def run_scenario(backend, scenario: Scenario) -> list[Result]:
    backend.reset_history()
    results = []
    for i, (user_text, check) in enumerate(zip(scenario.turns, scenario.checks)):
        t0 = time.perf_counter()
        reply = backend.generate_reply(user_text)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        passed, reason = _check(
            reply,
            must_contain=check.get("must_contain", []),
            must_not_contain=check.get("must_not_contain", []),
            regex=check.get("regex", ""),
        )
        results.append(Result(
            scenario_id=scenario.id,
            turn=i + 1,
            user=user_text,
            reply=reply,
            elapsed_ms=elapsed_ms,
            passed=passed,
            reason=reason,
        ))
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["llama", "qwen"], default="llama")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  W-BOT LLM Eval  —  backend: {args.backend}")
    print(f"{'='*60}\n")

    if args.backend == "llama":
        from robot_waiter_ai.inference.llama_cpp_backend import LlamaCppBackend
        backend = LlamaCppBackend()
    else:
        from robot_waiter_ai.inference.qwen3_backend import Qwen3Backend
        backend = Qwen3Backend()

    all_results: list[Result] = []
    for scenario in SCENARIOS:
        results = run_scenario(backend, scenario)
        all_results.extend(results)

        # Son turn'ün sonucunu göster (o senaryonun hedef yanıtı)
        last = results[-1]
        status = "✓ PASS" if last.passed else "✗ FAIL"
        print(f"[{scenario.id}] {status}  {scenario.description}")
        if args.verbose or not last.passed:
            for r in results:
                s = "✓" if r.passed else "✗"
                print(f"       Turn {r.turn}: {s}  Kullanıcı: {r.user!r}")
                print(f"              Bot   : {r.reply!r}")
                if not r.passed:
                    print(f"              HATA  : {r.reason}")
                print(f"              Süre  : {r.elapsed_ms:.0f} ms")

    # Özet
    passed = [r for r in all_results if r.passed]
    failed = [r for r in all_results if not r.passed]
    times = [r.elapsed_ms for r in all_results]

    print(f"\n{'─'*60}")
    print(f"  Toplam turn  : {len(all_results)}")
    print(f"  PASS         : {len(passed)} ({100*len(passed)//len(all_results)}%)")
    print(f"  FAIL         : {len(failed)} ({100*len(failed)//len(all_results)}%)")
    print(f"  Ortalama süre: {sum(times)/len(times):.0f} ms")
    print(f"  Min süre     : {min(times):.0f} ms")
    print(f"  Max süre     : {max(times):.0f} ms")

    if failed:
        print(f"\n  Başarısız senaryolar:")
        for r in failed:
            print(f"    [{r.scenario_id}] Turn {r.turn} — {r.reason}")
            print(f"      Bot: {r.reply!r}")

    print(f"{'─'*60}\n")
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
