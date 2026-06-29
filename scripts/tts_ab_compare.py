#!/usr/bin/env python3
"""
scripts/tts_ab_compare.py — TTS ses A/B karşılaştırması.

Aynı temsilî cümleleri farklı TTS motor/sesleriyle seslendirir; tek tıkla
dinlemek için bir `index.html` üretir. Amaç: ekibe "hangi ses sıcak/samimi"
kararını verdirmek (toplanti.md md.2 — "2-3 örnek ses onayı").

Kullanım:
    python scripts/tts_ab_compare.py
    python scripts/tts_ab_compare.py --text "Özel bir cümle"
    python scripts/tts_ab_compare.py --xtts-ref kayit.wav   # XTTS klon ekle (WSL+GPU)

Motorlar (bulunmayan otomatik atlanır):
    - edge-tts (online)  : Emel, Emel-warm (yavaş+pes), Ahmet
    - piper   (offline)  : binary + tr_TR-*.onnx bulunursa
    - xtts    (offline)  : coqui `TTS` kuruluysa + --xtts-ref verilirse (Türkçe klon)

Not: edge-tts internet ister. Ses KARAKTERİ donanımdan bağımsızdır — PC'de
üretilen ses Jetson'da da aynı tınıdadır (yalnızca latency farklı).
"""
from __future__ import annotations

import argparse
import asyncio
import html
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Windows Türkçe konsolu (cp1254) Unicode glyph'lerde patlar — UTF-8'e geç
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Temsilî cümleler — sıcaklık/ton kararı için farklı bağlamlar
SENTENCES: list[tuple[str, str]] = [
    ("karsilama", "Merhaba, hoş geldiniz! Size nasıl yardımcı olabilirim?"),
    ("siparis",   "Harika seçim! Mercimek Çorbası 85 TL. Başka bir şey alır mısınız?"),
    ("oneri",     "Canınız tatlı isterse künefemizi gönülden tavsiye ederim."),
    ("kapanis",   "Afiyet olsun, yine bekleriz efendim!"),
]

# edge-tts varyantları: (etiket, Communicate parametreleri)
EDGE_VARIANTS: list[tuple[str, dict]] = [
    ("edge_emel",      {"voice": "tr-TR-EmelNeural"}),
    ("edge_emel_warm", {"voice": "tr-TR-EmelNeural", "rate": "-8%", "pitch": "-2Hz"}),
    ("edge_ahmet",     {"voice": "tr-TR-AhmetNeural"}),
]

# Duygu/ton ön ayarları — prozodi (rate/pitch/volume). Türkçe'de "isimli stil"
# (excited vb.) çalışmadığı için duyguyu prozodiyle şekillendiriyoruz.
EMOTIONS: dict[str, dict] = {
    "neutral": {"rate": "+0%",  "pitch": "+0Hz",  "volume": "+0%"},
    "excited": {"rate": "+12%", "pitch": "+18Hz", "volume": "+12%"},  # heyecanlı
    "warm":    {"rate": "-8%",  "pitch": "-3Hz",  "volume": "+0%"},   # sıcak/içten
    "soft":    {"rate": "-10%", "pitch": "-1Hz",  "volume": "-6%"},   # yumuşak/sakin
}
_EMO_VOICE = "tr-TR-EmelNeural"


# ── edge-tts ────────────────────────────────────────────────────────────────

async def _gen_edge(text: str, out_path: Path, opts: dict) -> None:
    import edge_tts
    comm = edge_tts.Communicate(
        text,
        opts["voice"],
        rate=opts.get("rate", "+0%"),
        volume=opts.get("volume", "+0%"),
        pitch=opts.get("pitch", "+0Hz"),
    )
    await comm.save(str(out_path))


async def _edge_bytes(text: str, voice: str, emo: str) -> bytes:
    """Bir parçayı verilen duygu ön ayarıyla seslendir → mp3 bytes döndür."""
    import edge_tts
    p = EMOTIONS[emo]
    comm = edge_tts.Communicate(text, voice, rate=p["rate"],
                                pitch=p["pitch"], volume=p["volume"])
    buf = bytearray()
    async for ch in comm.stream():
        if ch["type"] == "audio":
            buf += ch["data"]
    return bytes(buf)


# Duygu demosu metinleri — dil bazlı
_EMO_TEXT = {
    "tr": {
        "voice": "tr-TR-EmelNeural",
        "siparis": "Harika seçim! Mercimek Çorbası 85 TL. Başka bir şey alır mısınız?",
        "karsilama": "Merhaba, hoş geldiniz! Size nasıl yardımcı olabilirim?",
        "excite": "Harika seçim!",
        "rest": "Mercimek Çorbası 85 TL. Başka bir şey alır mısınız?",
    },
    "en": {
        "voice": "en-US-AriaNeural",  # İngilizce sesler doğal olarak daha canlı
        "siparis": "Excellent choice! Lentil soup is 85 liras. Would you like anything else?",
        "karsilama": "Hello, welcome! How can I help you today?",
        "excite": "Excellent choice!",
        "rest": "Lentil soup is 85 liras. Would you like anything else?",
    },
}


def run_emotions(out_dir: Path, lang: str = "tr", voice: str | None = None) -> Path:
    """Duygu/ton demosu: aynı cümlenin farklı duygularla + faz-bazlı versiyonu."""
    cfg = _EMO_TEXT[lang]
    voice = voice or cfg["voice"]
    siparis, karsilama = cfg["siparis"], cfg["karsilama"]
    items: list[tuple[str, str]] = []  # (etiket, dosya)

    # 1) Sipariş cümlesi — tüm cümleye uygulanan duygular
    for emo in ("neutral", "excited", "warm", "soft"):
        fn = f"siparis_{lang}__{emo}.mp3"
        (out_dir / fn).write_bytes(asyncio.run(_edge_bytes(siparis, voice, emo)))
        items.append((f"Sipariş — tüm cümle: {emo}", fn))
        print(f"  [siparis/{emo}] ✓")

    # 2) Faz-bazlı: SADECE heyecan ifadesi heyecanlı, gerisi nötr (parça birleştirme)
    seg1 = asyncio.run(_edge_bytes(cfg["excite"], voice, "excited"))
    seg2 = asyncio.run(_edge_bytes(cfg["rest"], voice, "neutral"))
    fn = f"siparis_{lang}__mixed_excited.mp3"
    (out_dir / fn).write_bytes(seg1 + seg2)
    items.append((f"Sipariş — SADECE '{cfg['excite']}' heyecanlı (faz-bazlı)", fn))
    print("  [siparis/mixed] ✓")

    # 3) Karşılama — nötr vs sıcak
    for emo in ("neutral", "warm"):
        fn = f"karsilama_{lang}__{emo}.mp3"
        (out_dir / fn).write_bytes(asyncio.run(_edge_bytes(karsilama, voice, emo)))
        items.append((f"Karşılama — {emo}", fn))
        print(f"  [karsilama/{emo}] ✓")

    rows = "\n".join(
        f"<tr><td>{html.escape(lbl)}</td>"
        f"<td><audio controls preload='none' src='{html.escape(fn)}'></audio></td></tr>"
        for lbl, fn in items
    )
    doc = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<title>W-BOT TTS Duygu/Ton Demosu ({lang})</title>
<style>
 body{{font-family:system-ui,Arial,sans-serif;margin:24px;background:#fafafa}}
 h1{{font-size:20px}} p{{color:#555}}
 table{{border-collapse:collapse;width:100%}}
 td{{border:1px solid #ddd;padding:10px;vertical-align:middle}}
 td:first-child{{font-weight:600;max-width:420px}} audio{{width:260px}}
</style></head><body>
<h1>W-BOT — Duygu/Ton (prozodi) Demosu — dil: {lang}, ses: {html.escape(voice)}</h1>
<p>Hepsi aynı ses, yalnızca pitch/hız/ses-yüksekliği değişiyor (edge-tts prozodisi).
NOT: Bu hâlâ "isimli duygu stili" değil, prozodi hilesi. İngilizce sesler doğal olarak
daha canlı duyulur. "Faz-bazlı" örnekte sadece heyecan ifadesi heyecanlı — pipeline
cümle cümle çaldığı için production'da bedava (concat gerekmez).</p>
<table>{rows}</table></body></html>"""
    idx = out_dir / f"emotions_{lang}.html"
    idx.write_text(doc, encoding="utf-8")
    return idx


# ── Piper (offline) ─────────────────────────────────────────────────────────

def _gen_piper(text: str, out_path: Path) -> bool:
    """Piper binary+model varsa WAV üret. Yoksa False döner (atla)."""
    try:
        from robot_waiter_ai.speech.tts import PiperTTS
        piper = PiperTTS()
    except Exception as exc:
        print(f"  [piper] atlandı: {exc}")
        return False
    wav = asyncio.run(piper.synthesize(text))
    out_path.write_bytes(wav)
    return True


# ── XTTS-v2 (offline klonlama, GPU) ─────────────────────────────────────────

_XTTS_MODEL = {"obj": None}


def _gen_xtts(text: str, out_path: Path, ref_wav: str) -> bool:
    """coqui TTS kuruluysa ve referans ses verildiyse Türkçe klonla."""
    try:
        if _XTTS_MODEL["obj"] is None:
            from TTS.api import TTS  # type: ignore
            import torch
            dev = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"  [xtts] model yükleniyor ({dev})...")
            _XTTS_MODEL["obj"] = TTS(
                "tts_models/multilingual/multi-dataset/xtts_v2"
            ).to(dev)
        _XTTS_MODEL["obj"].tts_to_file(
            text=text, speaker_wav=ref_wav, language="tr", file_path=str(out_path)
        )
        return True
    except Exception as exc:
        print(f"  [xtts] atlandı: {exc}")
        return False


# ── index.html ──────────────────────────────────────────────────────────────

def _write_index(out_dir: Path, sentences, engines, produced: dict) -> Path:
    """produced[(engine, sent_key)] = dosya adı (yoksa yok)."""
    rows = []
    head_cells = "".join(f"<th>{html.escape(e)}</th>" for e in engines)
    for key, text in sentences:
        cells = [f"<td class='s'>{html.escape(text)}</td>"]
        for e in engines:
            fname = produced.get((e, key))
            if fname:
                cells.append(
                    f"<td><audio controls preload='none' src='{html.escape(fname)}'>"
                    f"</audio></td>"
                )
            else:
                cells.append("<td class='x'>—</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    doc = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<title>W-BOT TTS Ses A/B</title>
<style>
 body{{font-family:system-ui,Arial,sans-serif;margin:24px;background:#fafafa}}
 h1{{font-size:20px}} p{{color:#555}}
 table{{border-collapse:collapse;width:100%}}
 th,td{{border:1px solid #ddd;padding:8px;text-align:left;vertical-align:top}}
 th{{background:#f0f0f0;position:sticky;top:0}}
 td.s{{max-width:280px;font-weight:600}} td.x{{color:#bbb;text-align:center}}
 audio{{width:230px}}
</style></head><body>
<h1>W-BOT — TTS Ses A/B Karşılaştırması</h1>
<p>Her satır bir cümle, her sütun bir ses. Sıcak/samimi gelen sesi seçin. (edge-* online; offline adaylar XTTS/Fish eklenecek.)</p>
<table><tr><th>Cümle</th>{head_cells}</tr>
{chr(10).join(rows)}
</table></body></html>"""
    idx = out_dir / "index.html"
    idx.write_text(doc, encoding="utf-8")
    return idx


# ── main ────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="TTS ses A/B karşılaştırması")
    ap.add_argument("--out", default=str(PROJECT_ROOT / "tts_ab_out"))
    ap.add_argument("--text", default=None, help="Tek özel cümle (varsayılan set yerine)")
    ap.add_argument("--xtts-ref", default=None, help="XTTS klonlama için referans WAV")
    ap.add_argument("--no-edge", action="store_true", help="edge-tts'i atla")
    ap.add_argument("--no-piper", action="store_true", help="Piper'ı atla")
    ap.add_argument("--emotions", action="store_true",
                    help="Duygu/ton (prozodi) demosu üret → emotions_<lang>.html")
    ap.add_argument("--emo-lang", default="tr", choices=["tr", "en"],
                    help="Duygu demosu dili (tr/en)")
    ap.add_argument("--emo-voice", default=None, help="Duygu demosu sesi (override)")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.emotions:
        print(f"Duygu/ton demosu ({args.emo_lang}) → {out_dir}\n")
        idx = run_emotions(out_dir, lang=args.emo_lang, voice=args.emo_voice)
        print(f"\n✓ Dinlemek için aç: {idx}")
        return
    sentences = [("ozel", args.text)] if args.text else SENTENCES

    engines: list[str] = []
    if not args.no_edge:
        engines += [lbl for lbl, _ in EDGE_VARIANTS]
    if not args.no_piper:
        engines.append("piper")
    if args.xtts_ref:
        engines.append("xtts")

    produced: dict[tuple[str, str], str] = {}
    print(f"Çıktı: {out_dir}\n")

    for key, text in sentences:
        print(f"• {key}: {text}")
        # edge varyantları
        if not args.no_edge:
            for lbl, opts in EDGE_VARIANTS:
                fname = f"{key}__{lbl}.mp3"
                try:
                    asyncio.run(_gen_edge(text, out_dir / fname, opts))
                    produced[(lbl, key)] = fname
                    print(f"  [{lbl}] ✓")
                except Exception as exc:
                    print(f"  [{lbl}] hata: {exc}")
        # piper
        if not args.no_piper:
            fname = f"{key}__piper.wav"
            if _gen_piper(text, out_dir / fname):
                produced[("piper", key)] = fname
                print("  [piper] ✓")
        # xtts
        if args.xtts_ref:
            fname = f"{key}__xtts.wav"
            if _gen_xtts(text, out_dir / fname, args.xtts_ref):
                produced[("xtts", key)] = fname
                print("  [xtts] ✓")
        print()

    engines = [e for e in engines if any((e, k) in produced for k, _ in sentences)]
    idx = _write_index(out_dir, sentences, engines, produced)
    print(f"✓ {len(produced)} dosya üretildi.")
    print(f"✓ Dinlemek için aç: {idx}")


if __name__ == "__main__":
    main()
