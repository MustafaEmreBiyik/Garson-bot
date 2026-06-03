#!/usr/bin/env python3
"""
Kullanım:
  # Tek dosyayı enjekte et (önizleme):
  python inject_system_and_merge.py raw_cat1.jsonl

  # Birden fazla dosyayı birleştirerek wbot_finetune_v1.jsonl'e ekle:
  python inject_system_and_merge.py raw_cat1.jsonl raw_cat6.jsonl --merge

  # Tüm raw_*.jsonl dosyalarını birden birleştir:
  python inject_system_and_merge.py raw_*.jsonl --merge

  --merge bayrağı olmadan: çıktıyı stdout'a basar, dosyaya yazmaz (kuru çalıştırma).
  --merge ile:            wbot_finetune_v1.jsonl sonuna ekler, istatistik basar.

Doğrulama her iki modda da çalışır; hata varsa birleştirme gerçekleşmez.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ── Sistem promptu — §A'daki metin, aynen ───────────────────────────────────
SYSTEM_PROMPT = (
    "Sen sıcakkanlı ve güler yüzlü bir Türk restoran garsonu olarak konuşan yapay zekasın. "
    "Gerçek bir garson gibi samimi ve içten ol: akıcı doğal Türkçe kullan, uygun anlarda "
    '"Buyurun!", "Harika seçim!" gibi kısa samimi ifadeler ekle. Her turda aynı kalıpları '
    'tekrarlama. Müşteriye DAİMA "siz" ile hitap et; "musun", "istiyorsun", "ister misin" '
    "gibi tekil ikinci şahıs ASLA kullanma — yerine \"musunuz\", \"istiyorsunuz\", "
    '"ister misiniz" kullan.\n\n'
    "MENÜ:\n"
    "Çorba: Mercimek Çorbası: 85 TL | Kremalı Mantar Çorbası: 95 TL\n"
    "Ana Yemek: Izgara Köfte: 240 TL | Et Döner: 280 TL | Izgara Tavuk Salata: 210 TL\n"
    "Tatlı: Fırın Sütlaç: 100 TL | Künefe: 140 TL\n"
    "İçecek: Yayık Ayran: 45 TL | Limonata: 70 TL | Şalgam Suyu: 50 TL\n\n"
    "KURALLAR:\n"
    "- Yalnızca Türkçe. Madde işareti, kalın yazı, emoji yok. En fazla 2 cümle, 25 kelime.\n"
    "- Karşılama VEYA genel menü sorusu (kategori adı geçmiyorsa): \"çorba, ana yemek, tatlı, "
    'içecek" dördü TEK cümlede geçmeli. Max 15 kelime. Ürün adı sayma.\n'
    '- Kategori sorusu ("çorba ne var" gibi): YALNIZCA o kategorideki isimleri say, fiyat söyleme.\n'
    "- FİYAT: yalnızca (1) fiyat sorusu, (2) sipariş onayı, (3) hesap. Diğerinde \"TL\" geçmesin.\n"
    "- Öneri sorusu: kategori belirtildiyse YALNIZCA o kategoriden 1-2 ürün. Başka kategori ekleme.\n"
    '- Sipariş onayı: sıcak kabul + ürün adı + TL fiyat + "başka" sorusu. "Getireyim mi?" YASAK.\n'
    "- Birden fazla sipariş: her ürünü ayrı cümleyle onayla.\n"
    '- Hesap: "Toplam X TL." + afiyet/iyi günler kapanışı.\n'
    '- Menüde olmayan ürün: "Bu konuda bilgim yok, personelimize sorabilirsiniz."\n'
    '- Diyet/alerji/vegan/glüten soruları: "Bu konuda bilgim yok, personelimize sorabilirsiniz."\n'
    '- Restoran hakkında sorular (saat, konum, wifi, ödeme): '
    '"Bu konuda bilgim yok, personelimize sorabilirsiniz."\n'
    '- "Siparişiniz onaylandı", "onaylanıyor", "kaydedildi" YASAK.'
)

DATASET_PATH = Path(__file__).parent.parent / "datasets" / "processed" / "wbot_finetune_v1.jsonl"

BANNED = ["getireyim mi", "onaylandı", "onaylanıyor", "kaydedildi"]
SINGULAR = ["musun", "istiyorsun", "ister misin"]
PRICE_RE = re.compile(r"\d+\s*TL\b", re.IGNORECASE)


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def validate_record(record: dict, idx: int) -> list[str]:
    issues: list[str] = []
    msgs = record.get("messages", [])

    if not msgs:
        return ["messages dizisi boş"]

    # system mesajı doğru mu?
    if msgs[0]["role"] != "system" or msgs[0]["content"] != SYSTEM_PROMPT:
        issues.append("system mesajı eksik veya yanlış")

    # sadece assistant yanıtlarını kontrol et
    for m in msgs:
        if m["role"] != "assistant":
            continue
        content: str = m["content"]
        cl = content.lower()

        for b in BANNED:
            if b in cl:
                issues.append(f"YASAK: '{b}'")

        for s in SINGULAR:
            if re.search(r"\b" + s + r"\b", cl):
                issues.append(f"tekil: '{s}'")

        wc = word_count(content)
        if wc > 25:
            issues.append(f"kelime sayısı {wc} > 25")

    return [f"[kayıt {idx}] {issue}" for issue in issues]


def inject_system(raw_record: dict) -> dict:
    """user/assistant-only kaydına system mesajı ekler."""
    msgs = raw_record["messages"]
    if msgs and msgs[0]["role"] == "system":
        # zaten system var — üzerine yaz
        msgs[0]["content"] = SYSTEM_PROMPT
        return raw_record
    return {"messages": [{"role": "system", "content": SYSTEM_PROMPT}] + msgs}


def process_file(path: Path) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    all_issues: list[str] = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            raw = json.loads(raw_line)
        except json.JSONDecodeError as e:
            all_issues.append(f"[{path.name}:{line_no}] JSON hatası: {e}")
            continue
        record = inject_system(raw)
        issues = validate_record(record, line_no)
        all_issues.extend([f"[{path.name}] {i}" for i in issues])
        records.append(record)
    return records, all_issues


def main() -> None:
    parser = argparse.ArgumentParser(description="System prompt enjekte et ve dataset'e birleştir.")
    parser.add_argument("inputs", nargs="+", type=Path, help="Ham JSONL dosyaları")
    parser.add_argument(
        "--merge",
        action="store_true",
        help=f"Doğrulamadan sonra {DATASET_PATH.name} sonuna ekle",
    )
    args = parser.parse_args()

    all_records: list[dict] = []
    all_issues: list[str] = []

    for path in args.inputs:
        if not path.exists():
            print(f"HATA: dosya bulunamadı — {path}", file=sys.stderr)
            sys.exit(1)
        records, issues = process_file(path)
        all_records.extend(records)
        all_issues.extend(issues)
        print(f"{path.name}: {len(records)} kayıt işlendi, {len(issues)} sorun")

    if all_issues:
        print("\n--- DOĞRULAMA HATALARI ---")
        for issue in all_issues:
            print(issue)
        print(f"\nToplam {len(all_issues)} hata — birleştirme iptal edildi.")
        sys.exit(1)

    print(f"\nToplam {len(all_records)} kayıt, tüm doğrulamalar geçti.")

    if not args.merge:
        # Kuru çalıştırma: stdout'a bas
        print("\n--- ÖNIZLEME (ilk 3 kayıt) ---")
        for r in all_records[:3]:
            print(json.dumps(r, ensure_ascii=False))
        print("\n(--merge bayrağı olmadan gerçek yazma yapılmaz)")
        return

    # Birleştir
    existing = 0
    if DATASET_PATH.exists():
        existing = sum(1 for l in DATASET_PATH.read_text(encoding="utf-8").splitlines() if l.strip())

    with DATASET_PATH.open("a", encoding="utf-8") as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    total = existing + len(all_records)
    print(f"Eklendi: {len(all_records)} kayıt → {DATASET_PATH.name} (toplam: {total})")


if __name__ == "__main__":
    main()
