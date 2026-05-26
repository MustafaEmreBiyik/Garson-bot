"""
scripts/demo_usb.py — W-BOT USB mikrofon + hoparlör demo.

Kullanım:
    python3 scripts/demo_usb.py

Çıkmak için Ctrl+C.

Akış:
    ENTER'a bas → USB mikrofondan 6 sn kayıt → Whisper STT →
    Qwen3-4B → Piper TTS → USB hoparlörden çal → tekrar
"""
from __future__ import annotations

import asyncio
import io
import logging
import sys
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("demo_usb")

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

SAMPLE_RATE = 16_000
RECORD_SECONDS = 6
CHANNELS = 1

WHISPER_MODEL = "medium"
PIPER_MODEL = None  # None → otomatik bul

# Whisper'a Türkçe restoran bağlamı ver → menü kelimelerini daha iyi tanır
STT_INITIAL_PROMPT = (
    "Türkçe restoran siparişi. Menü: mercimek çorbası, mantar çorbası, "
    "izgara köfte, et döner, tavuk salata, sütlaç, künefe, ayran, limonata, şalgam."
)


# ---------------------------------------------------------------------------
# Ses yardımcıları
# ---------------------------------------------------------------------------

def _numpy_to_wav(audio: np.ndarray, rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(audio.astype(np.int16).tobytes())
    return buf.getvalue()


def _play_wav(wav_bytes: bytes) -> None:
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, "rb") as wf:
        rate = wf.getframerate()
        ch = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())
    audio = np.frombuffer(raw, dtype=np.int16)
    if ch > 1:
        audio = audio.reshape(-1, ch)
    sd.play(audio, samplerate=rate)
    sd.wait()


def _play_mp3(mp3_bytes: bytes) -> None:
    import os, subprocess, tempfile
    fd, tmp = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        Path(tmp).write_bytes(mp3_bytes)
        subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp],
                       check=True)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


async def _speak(tts, text: str) -> None:
    """TTS ile seslendir — Piper (WAV) ve edge-tts (MP3) ikisini de destekler."""
    audio_bytes = await tts.synthesize(text)
    content_type = getattr(tts, "AUDIO_CONTENT_TYPE", "audio/wav")
    if "wav" in content_type:
        await asyncio.to_thread(_play_wav, audio_bytes)
    else:
        await asyncio.to_thread(_play_mp3, audio_bytes)


def _record() -> bytes:
    print("  🎙  Dinliyorum... (6 sn)", flush=True)
    audio = sd.rec(
        int(SAMPLE_RATE * RECORD_SECONDS),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
    )
    sd.wait()
    return _numpy_to_wav(audio.flatten(), SAMPLE_RATE)


# ---------------------------------------------------------------------------
# Ana döngü
# ---------------------------------------------------------------------------

async def run_demo() -> None:
    print("\n" + "=" * 55)
    print("  W-BOT USB Demo  —  Ctrl+C ile çıkış")
    print("=" * 55)
    print("\nModeller yükleniyor, lütfen bekleyin...\n")

    from robot_waiter_ai.speech.stt import SpeechToText
    from robot_waiter_ai.speech.tts import PiperTTS
    from robot_waiter_ai.inference.qwen3_backend import Qwen3Backend

    # TTS
    try:
        tts = PiperTTS(model=PIPER_MODEL)
        print("TTS: Piper (offline)")
    except RuntimeError:
        from robot_waiter_ai.speech.tts import TextToSpeech
        tts = TextToSpeech()
        print("TTS: edge-tts (fallback, internet gerekli)")

    # LLM
    llm = Qwen3Backend()

    # STT — modeli şimdi yükle (lazy load'u startup'a çek, ilk konuşmada gecikme olmasın)
    print("STT modeli yükleniyor...")
    stt = SpeechToText(model_size=WHISPER_MODEL, device="cuda", compute_type="float16")
    silence_wav = _numpy_to_wav(np.zeros(SAMPLE_RATE, dtype=np.int16), SAMPLE_RATE)
    await stt.transcribe(silence_wav, language="tr",
                         initial_prompt=STT_INITIAL_PROMPT)  # modeli ısıt
    print("STT: hazır\n")

    print("✓ Tüm modeller hazır!\n")

    # Karşılama
    greeting = "Merhaba, hoş geldiniz! Ben W-BOT. Size nasıl yardımcı olabilirim?"
    print(f"W-BOT: {greeting}")
    try:
        await _speak(tts, greeting)
    except Exception as e:
        logger.warning("Karşılama TTS hatası: %s", e)

    # --- Ana döngü ---
    while True:
        print("\n" + "-" * 40)
        try:
            input("  ENTER'a bas ve konuş → ")
        except EOFError:
            break

        # 1. Kayıt
        wav_bytes = await asyncio.to_thread(_record)

        # 2. STT
        print("  ⏳ Anlıyorum...", flush=True)
        try:
            result = await stt.transcribe(wav_bytes, language="tr",
                                         initial_prompt=STT_INITIAL_PROMPT)
            user_text = result["text"].strip()
        except Exception as e:
            print(f"  ✗ STT hatası: {e}")
            continue

        if not user_text:
            print("  (Ses algılanamadı, tekrar dene)")
            continue

        print(f"\nMüşteri: {user_text}")

        # 3. LLM
        print("  ⏳ Düşünüyorum...", flush=True)
        try:
            reply = await asyncio.to_thread(llm.generate_reply, user_text)
        except Exception as e:
            print(f"  ✗ LLM hatası: {e}")
            continue

        print(f"W-BOT:   {reply}")

        # 4. TTS + çal
        try:
            await _speak(tts, reply)
        except Exception as e:
            logger.warning("TTS/oynatma hatası: %s", e)

        # Oturum sonu → kısa veda cümlesi ise history sıfırla
        # "Tabii teşekkürler, bir şey daha..." gibi uzun cümleleri tetiklememeli
        farewell_phrases = ["güle güle", "görüşürüz", "hoşça kal", "iyi günler"]
        short_thanks = user_text.strip().lower()
        is_farewell = (
            any(p in short_thanks for p in farewell_phrases)
            or (len(short_thanks) < 40 and "teşekkür" in short_thanks
                and not any(q in short_thanks for q in ["alabilir", "istiyorum", "verir", "?", "mı", "mi"]))
        )
        if is_farewell:
            print("\n--- Yeni müşteri oturumu başladı ---")
            llm.reset_history()


def main() -> None:
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n\nDemo sonlandırıldı.")


if __name__ == "__main__":
    main()
