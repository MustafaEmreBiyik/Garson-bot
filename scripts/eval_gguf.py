#!/usr/bin/env python3
"""eval_gguf.py — wbot_v3 GGUF eval (Jetson'da çalıştır)

Kullanım:
    python3 scripts/eval_gguf.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from robot_waiter_ai.inference.llama_cpp_backend import LlamaCppBackend


def _contains(*words):
    def check(r): return all(w.lower() in r.lower() for w in words)
    return check

def _any_of(*words):
    def check(r): return any(w.lower() in r.lower() for w in words)
    return check

def _not_contains(*words):
    def check(r): return all(w.lower() not in r.lower() for w in words)
    return check

def _both(f1, f2):
    def check(r): return f1(r) and f2(r)
    return check

def _ends_question(r): return r.strip().endswith("?")


_EVAL_CASES = [
    ("E01", "Karşılama — 4 kategori + soru işareti",
     "Merhaba",
     _both(
         _both(_contains("çorba", "ana yemek", "tatlı", "içecek"),
               _not_contains("köfte", "ayran", "sütlaç", "limonata")),
         _ends_question,
     )),

    ("E02", "Genel menü sorusu — 4 kategori",
     "Ne yiyebilirim?",
     _contains("çorba", "ana yemek", "tatlı", "içecek")),

    ("E03", "Sipariş onayı — fiyat + başka sorusu",
     "Bir mercimek çorbası istiyorum.",
     _both(_contains("85"), _contains("başka"))),

    ("E04", "Sipariş iptali",
     "Aslında çorbayı istemiyorum, iptal edin.",
     _any_of("çıkar", "iptal", "kaldır", "tamam", "anladım")),

    ("E05", "Fiyat sorusu",
     "Izgara köftenin fiyatı ne kadar?",
     _contains("240")),

    ("E06", "Kategori listesi — fiyat yasağı",
     "Çorba ne var?",
     _both(_contains("mercimek", "mantar"), _not_contains("tl", "85", "95"))),

    ("E07", "Öneri — kategori dışına çıkma yasağı",
     "Tatlı olarak ne önerirsiniz?",
     _both(_any_of("sütlaç", "künefe"),
           _not_contains("köfte", "döner", "çorba", "ayran"))),

    ("E08", "Hesap isteği — toplam söylemeli",
     "Hesabı alabilir miyim?",
     _contains("toplam")),

    ("E09", "Menüde olmayan ürün",
     "Hamburger var mı?",
     _both(_contains("bilgim yok"), _not_contains("hamburger:"))),

    ("E10", "Konu dışı red",
     "Bana bir şiir yazar mısınız?",
     _not_contains("şiir\n", "İşte bir şiir")),

    ("E11", "Alerji — uydurma güvence vermemeli",
     "Fıstık alerjim var, ne önerirsiniz?",
     _not_contains("kesinlikle güvenli", "hiç sorun yok")),

    ("E12", "Hitap — siz formu",
     "Bana bir şey önerir misiniz?",
     _not_contains(" sen ", "ister misin", "musun")),

    ("E13", "Markdown yasağı",
     "Menünüzde neler var?",
     _not_contains("**", "##", "- ", "* ")),

    ("E14", '"Getireyim mi?" yasağı — sipariş onayında',
     "Bir ayran alabilir miyim?",
     _both(_contains("45"), _not_contains("getireyim mi"))),

    ("E15", "Sipariş onayı sıcak başlangıç kelimesi",
     "Bir köfte istiyorum.",
     _any_of("elbette", "tabii", "memnuniyetle", "harika")),

    ("E16", "Tek tekil hitap yasağı",
     "Ne önerirsin?",
     _not_contains("öneririm", "istersin", "alırsın")),
]


def main():
    print("GGUF yükleniyor...")
    llm = LlamaCppBackend()
    print(f"Model hazır. {len(_EVAL_CASES)} senaryo çalıştırılıyor...\n")

    passed = 0
    for case_id, desc, user_text, check_fn in _EVAL_CASES:
        llm.reset_history()
        reply = llm.generate_reply(user_text)
        ok = check_fn(reply)
        status = "✓ GEÇTİ" if ok else "✗ KALDI"
        if ok:
            passed += 1
        print(f"[{case_id}] {status}  {desc}")
        print(f"         Soru : {user_text}")
        print(f"         Yanıt: {reply}")
        print()

    total = len(_EVAL_CASES)
    print(f"{'='*55}")
    print(f"Sonuç: {passed}/{total} geçti  (%{100*passed//total})")


if __name__ == "__main__":
    main()
