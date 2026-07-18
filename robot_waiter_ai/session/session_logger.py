"""
session/session_logger.py — demo_usb.py oturum loglama.

Amaç: (1) hukuki koruma — müşteri itirazlarında ("yanlış sipariş/fiyat
söylendi") elde somut kayıt bulunsun; (2) gelecekteki yeniden eğitim/analiz
için saha verisi biriksin (bkz. METODOLOJI.md §15 — bu modül o vizyonun
INTERNET GEREKTİRMEYEN, yerel-diske-yazan ilk parçasıdır, ayrı kapsam).

Tasarım ilkesi: ana döngüye (demo_usb.py) minimal müdahale, append-only,
crash-safe. Loglama hiçbir zaman demo'yu durdurmamalı — disk dolu/izin
hatası gibi durumlarda sessizce uyarı loglanır, akış devam eder.

Disk düzeni:
    data/sessions/<YYYY-MM-DD>/<session_id>/
        session.json      — meta + tur listesi (append-only, her turdan sonra yeniden yazılır)
        turn_001_user.wav  — müşterinin ham sesi (STT'ye giden wav_bytes, aynen)
        turn_002_user.wav
        ...

session.json şeması:
    {
        "session_id": "20260718-143022-a3f9",
        "table_no": null,                      # ROS masa-tespiti entegre olunca dolar
        "started_at": "2026-07-18T14:30:22",
        "ended_at": "2026-07-18T14:34:10",      # oturum kapanınca yazılır
        "turns": [
            {
                "turn": 1,
                "timestamp": "2026-07-18T14:30:25",
                "user_text": "Bir mercimek çorbası alayım.",
                "bot_reply": "Elbette, Mercimek Çorbası 85 TL. Başka bir şey alır mısınız?",
                "order_snapshot": [["Mercimek Çorbası", 85, 1]],
                "order_total": 85,
                "audio_file": "turn_001_user.wav"
            },
            ...
        ]
    }
"""
from __future__ import annotations

import json
import logging
import time
import uuid
import wave
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("session_logger")

_DEFAULT_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "sessions"
_DEFAULT_RETENTION_DAYS = 30


def _new_session_id() -> str:
    return f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4]}"


def _write_wav(path: Path, wav_bytes: bytes) -> None:
    """wav_bytes zaten geçerli bir WAV dosyasının ham içeriği (stt.transcribe
    girdisiyle aynı) — doğrudan diske yazılır, yeniden encode edilmez."""
    path.write_bytes(wav_bytes)


class SessionLogger:
    """Tek bir müşteri oturumunun log kaydını tutar.

    Kullanım (demo_usb.py ana döngüsünde):
        session = SessionLogger()                    # yeni müşteride oluştur
        ...
        await session.log_turn(user_text, reply, wav_bytes, order_tracker)
        ...
        await session.end()                           # oturum kapanınca (reset ile birlikte)

    Hiçbir metod exception fırlatmaz — iç hatalar loglanır, akış bozulmaz.
    """

    def __init__(self, root: Path | None = None, table_no: str | None = None) -> None:
        self._root = root or _DEFAULT_ROOT
        self._session_id = _new_session_id()
        self._table_no = table_no
        self._started_at = datetime.now()
        self._turn_count = 0
        self._turns: list[dict] = []
        self._dir: Path | None = None
        try:
            day_dir = self._root / self._started_at.strftime("%Y-%m-%d")
            self._dir = day_dir / self._session_id
            self._dir.mkdir(parents=True, exist_ok=True)
            self._write_meta(ended_at=None)
        except OSError as e:
            logger.warning("Oturum log dizini oluşturulamadı, loglama devre dışı: %s", e)
            self._dir = None

    @property
    def session_id(self) -> str:
        return self._session_id

    def _write_meta(self, *, ended_at: str | None) -> None:
        if self._dir is None:
            return
        payload = {
            "session_id": self._session_id,
            "table_no": self._table_no,
            "started_at": self._started_at.isoformat(timespec="seconds"),
            "ended_at": ended_at,
            "turns": self._turns,
        }
        tmp = self._dir / "session.json.tmp"
        final = self._dir / "session.json"
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(final)  # atomik — yarım yazılmış dosya asla görünmez

    async def log_turn(
        self,
        user_text: str,
        bot_reply: str,
        wav_bytes: bytes | None,
        order_items: list[tuple[str, int, int]],
        order_total: int,
    ) -> None:
        """Bir konuşma turunu kaydeder. Hata durumunda sessizce loglar, fırlatmaz."""
        if self._dir is None:
            return
        import asyncio

        self._turn_count += 1
        turn_no = self._turn_count
        audio_name = f"turn_{turn_no:03d}_user.wav" if wav_bytes else None
        try:
            if wav_bytes and audio_name:
                await asyncio.to_thread(_write_wav, self._dir / audio_name, wav_bytes)
            self._turns.append({
                "turn": turn_no,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "user_text": user_text,
                "bot_reply": bot_reply,
                "order_snapshot": [[n, p, q] for n, p, q in order_items],
                "order_total": order_total,
                "audio_file": audio_name,
            })
            await asyncio.to_thread(self._write_meta, ended_at=None)
        except OSError as e:
            logger.warning("Tur %d loglanamadı: %s", turn_no, e)

    async def end(self) -> None:
        """Oturumu kapatır (ended_at damgası)."""
        if self._dir is None:
            return
        import asyncio
        try:
            await asyncio.to_thread(
                self._write_meta, ended_at=datetime.now().isoformat(timespec="seconds"))
        except OSError as e:
            logger.warning("Oturum kapanışı loglanamadı: %s", e)


def cleanup_old_sessions(root: Path | None = None, retention_days: int = _DEFAULT_RETENTION_DAYS) -> int:
    """retention_days'ten eski gün-klasörlerini siler. Silinen klasör sayısını döner.

    run_demo() başlangıcında bir kez çağrılır (disk şişmesin diye). Hata
    durumunda sessizce loglar, demo başlatmayı engellemez.
    """
    root = root or _DEFAULT_ROOT
    if not root.exists():
        return 0
    cutoff = datetime.now() - timedelta(days=retention_days)
    removed = 0
    for day_dir in root.iterdir():
        if not day_dir.is_dir():
            continue
        try:
            day = datetime.strptime(day_dir.name, "%Y-%m-%d")
        except ValueError:
            continue  # beklenmeyen isim — dokunma
        if day < cutoff:
            try:
                import shutil
                shutil.rmtree(day_dir)
                removed += 1
            except OSError as e:
                logger.warning("Eski oturum klasörü silinemedi (%s): %s", day_dir, e)
    return removed
