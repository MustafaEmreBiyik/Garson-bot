"""
scripts/demo_usb.py — W-BOT USB mikrofon + hoparlör demo.

Kullanım:
    python3 scripts/demo_usb.py

Çıkmak için Ctrl+C.

Akış:
    "hey garson" → USB mikrofondan 6 sn kayıt → Whisper STT →
    Qwen3-4B → Piper TTS → USB hoparlörden çal → tekrar

    hey_garson.onnx yoksa otomatik olarak ENTER tuşu moduna geçer.
"""
from __future__ import annotations

import asyncio
import io
import logging
import sys
import threading
import wave
from pathlib import Path

# ALSA underrun uyarılarını bastır — callback module-level'da tutulmalı (GC koruması)
try:
    import ctypes
    _asound = ctypes.cdll.LoadLibrary("libasound.so.2")
    _ALSA_ERROR_HANDLER = ctypes.CFUNCTYPE(
        None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p
    )
    _alsa_error_handler_ref = _ALSA_ERROR_HANDLER(lambda *_: None)  # GC'den koru
    _asound.snd_lib_error_set_handler(_alsa_error_handler_ref)
except Exception:
    pass

import numpy as np
import sounddevice as sd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("demo_usb")

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

SAMPLE_RATE    = 16_000
RECORD_SECONDS = 6
CHANNELS       = 1

WHISPER_MODEL = "medium"
PIPER_MODEL   = None  # None → otomatik bul

# Whisper'a Türkçe restoran bağlamı ver → menü kelimelerini daha iyi tanır
STT_INITIAL_PROMPT = (
    "Türkçe restoran siparişi. Menü: mercimek çorbası, mantar çorbası, "
    "ızgara köfte, et döner, tavuk salata, sütlaç, künefe, ayran, limonata, şalgam."
)

WAKEWORD_MODEL_PATH = (
    Path(__file__).resolve().parent.parent / "robot_waiter_ai" / "models" / "hey_garson.onnx"
)
WAKEWORD_THRESHOLD = 0.7   # 0.5 çok hassastı — yanlış pozitifler azaltıldı
WAKEWORD_CHUNK     = 1280   # 80 ms @ 16 kHz — openWakeWord beklentisi

# ALSA çıkış cihazı — None → sistem varsayılanı, "plughw:2,0" → Jetson APE jack çıkışı
ALSA_OUTPUT_DEVICE: str | None = None


def _find_input_device() -> int | None:
    """USB ses giriş cihazının sounddevice index'ini döndür, bulamazsa None."""
    for i, d in enumerate(sd.query_devices()):
        if "USB" in d["name"] and d["max_input_channels"] > 0:
            return i
    return None


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
    import os, subprocess, tempfile
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        Path(tmp).write_bytes(wav_bytes)
        cmd = ["aplay", "-q"]
        if ALSA_OUTPUT_DEVICE:
            cmd += ["-D", ALSA_OUTPUT_DEVICE]
        cmd.append(tmp)
        subprocess.run(cmd, check=True)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


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


async def _speak(tts, text: str, tts_active: threading.Event | None = None) -> None:
    """TTS ile seslendir. tts_active set iken wake word algılaması durur."""
    if tts_active is not None:
        tts_active.set()
    try:
        audio_bytes  = await tts.synthesize(text)
        content_type = getattr(tts, "AUDIO_CONTENT_TYPE", "audio/wav")
        if "wav" in content_type:
            await asyncio.to_thread(_play_wav, audio_bytes)
        else:
            await asyncio.to_thread(_play_mp3, audio_bytes)
    finally:
        if tts_active is not None:
            tts_active.clear()


def _beep() -> None:
    """Kısa onay bip tonu — wake word algılandığında çal."""
    t = np.linspace(0, 0.15, int(SAMPLE_RATE * 0.15), dtype=np.float32)
    tone = (np.sin(2 * np.pi * 880 * t) * 0.3).astype(np.float32)
    sd.play(tone, samplerate=SAMPLE_RATE)
    sd.wait()


def _record(input_device: int | None = None) -> bytes:
    print("  🎙  Dinliyorum... (6 sn)", flush=True)
    audio = sd.rec(
        int(SAMPLE_RATE * RECORD_SECONDS),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        device=input_device,
    )
    sd.wait()
    return _numpy_to_wav(audio.flatten(), SAMPLE_RATE)


# ---------------------------------------------------------------------------
# Wake word
# ---------------------------------------------------------------------------

def _load_wakeword():
    """hey_garson.onnx modelini yükle. Hata varsa None döner."""
    if not WAKEWORD_MODEL_PATH.exists():
        return None
    try:
        oww_dir = str(Path(__file__).resolve().parent.parent / "openWakeWord")
        if oww_dir not in sys.path:
            sys.path.insert(0, oww_dir)
        from openwakeword.model import Model
        m = Model(wakeword_models=[str(WAKEWORD_MODEL_PATH)], inference_framework="onnx")
        logger.info("Wake word modeli yüklendi.")
        return m
    except Exception as e:
        logger.warning("Wake word modeli yüklenemedi: %s", e)
        return None


async def _detect_wakeword(ww_model, tts_active: threading.Event,
                           input_device: int | None = None) -> None:
    """'hey garson' algılanana kadar mikrofonu dinle (tek kullanımlık coroutine)."""
    loop     = asyncio.get_event_loop()
    detected = asyncio.Event()

    def _cb(indata, frames, time_info, status):
        if tts_active.is_set():
            return  # TTS çalarken tetikleme yapma (feedback engeli)
        if detected.is_set():
            return
        audio  = (indata[:, 0] * 32768).astype(np.int16)
        scores = ww_model.predict(audio)
        score  = float(list(scores.values())[0])
        if score > WAKEWORD_THRESHOLD:
            loop.call_soon_threadsafe(detected.set)

    with sd.InputStream(samplerate=16_000, channels=1, dtype="float32",
                        blocksize=WAKEWORD_CHUNK, callback=_cb,
                        device=input_device):
        await detected.wait()


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

    # TTS
    try:
        tts = PiperTTS(model=PIPER_MODEL)
        print("TTS: Piper (offline)")
    except RuntimeError:
        from robot_waiter_ai.speech.tts import TextToSpeech
        tts = TextToSpeech()
        print("TTS: edge-tts (fallback, internet gerekli)")

    # LLM — llama-cpp-python (Jetson/GGUF) önce dene, yoksa transformers (PC)
    try:
        from robot_waiter_ai.inference.llama_cpp_backend import LlamaCppBackend
        llm = LlamaCppBackend()
        print("LLM: llama-cpp-python GGUF (GPU)")
    except Exception as _llama_err:
        from robot_waiter_ai.inference.qwen3_backend import Qwen3Backend
        llm = Qwen3Backend()
        print("LLM: Qwen3Backend (transformers)")

    # STT
    print("STT modeli yükleniyor...")
    stt = SpeechToText(model_size=WHISPER_MODEL, device="cuda", compute_type="float16")
    silence_wav = _numpy_to_wav(np.zeros(SAMPLE_RATE, dtype=np.int16), SAMPLE_RATE)
    await stt.transcribe(silence_wav, language="tr",
                         initial_prompt=STT_INITIAL_PROMPT)  # modeli ısıt
    print("STT: hazır\n")

    # USB mikrofon cihazını otomatik bul
    input_device = _find_input_device()
    if input_device is not None:
        print(f"Mikrofon: device {input_device} ({sd.query_devices(input_device)['name'].strip()})")
    else:
        print("Mikrofon: varsayılan cihaz")

    # Wake word
    ww_model   = _load_wakeword()
    tts_active = threading.Event()  # TTS çalarken set, dinlerken clear
    if ww_model:
        print("Wake word: hey_garson.onnx yüklendi")
    else:
        print("Wake word: model bulunamadı → ENTER tuşu modu")

    print("\n✓ Tüm modeller hazır!\n")

    GREETING = "Merhaba, hoş geldiniz! Ben W-BOT. Size nasıl yardımcı olabilirim?"

    # Wake word modunda karşılamayı ilk seslenişe bırak
    ww_task: "asyncio.Task | None" = None
    if ww_model:
        print("\n  👂 'hey garson' bekleniyor...", flush=True)
        ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))
    else:
        # ENTER modunda karşılamayı hemen söyle
        print(f"W-BOT: {GREETING}")
        try:
            await _speak(tts, GREETING, tts_active)
        except Exception as e:
            logger.warning("Karşılama TTS hatası: %s", e)

    # --- Ana döngü ---
    first_wakeword    = True
    new_customer      = True   # Her oturum başında karşıla
    while True:
        # Tetikleyici: wake word (task zaten çalışıyor) veya ENTER
        if ww_model:
            await ww_task
            print("  ✔  Wake word algılandı!", flush=True)
            if first_wakeword:
                await asyncio.to_thread(_beep)
                first_wakeword = False
        else:
            try:
                print("\n" + "-" * 40)
                input("  ENTER'a bas ve konuş → ")
            except EOFError:
                break

        # Yeni müşteri oturumunda karşıla, ardından direkt kayda geç
        if new_customer and ww_model:
            new_customer = False
            print(f"W-BOT: {GREETING}")
            try:
                await _speak(tts, GREETING, tts_active)
            except Exception as e:
                logger.warning("Karşılama TTS hatası: %s", e)

        # 1. Kayıt
        wav_bytes = await asyncio.to_thread(_record, input_device)

        # 2. STT
        print("  ⏳ Anlıyorum...", flush=True)
        try:
            result    = await stt.transcribe(wav_bytes, language="tr",
                                             initial_prompt=STT_INITIAL_PROMPT)
            user_text = result["text"].strip()
        except Exception as e:
            print(f"  ✗ STT hatası: {e}")
            if ww_model:
                ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))
            continue

        if not user_text:
            print("  (Ses algılanamadı, tekrar dene)")
            if ww_model:
                ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))
            continue

        print(f"\nMüşteri: {user_text}")

        # 3. LLM
        print("  ⏳ Düşünüyorum...", flush=True)
        try:
            reply = await asyncio.to_thread(llm.generate_reply, user_text)
        except Exception as e:
            print(f"  ✗ LLM hatası: {e}")
            if ww_model:
                ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))
            continue

        print(f"W-BOT:   {reply}")

        # 4. Konuşmadan önce bir sonraki tespiti başlat (aplay çatışmaz)
        if ww_model:
            ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))

        # 5. TTS + çal
        try:
            await _speak(tts, reply, tts_active)
        except Exception as e:
            logger.warning("TTS/oynatma hatası: %s", e)

        # Oturum sonu kontrolü — müşteri veya bot veda ediyorsa sıfırla
        farewell_phrases = ["güle güle", "görüşürüz", "hoşça kal", "iyi günler", "tekrar bekleriz"]
        short_user = user_text.strip().lower()
        reply_lower = reply.lower()
        is_farewell = (
            any(p in reply_lower for p in farewell_phrases)   # bot veda etti
            or any(p in short_user for p in farewell_phrases)  # müşteri veda etti
            or (len(short_user) < 40 and "teşekkür" in short_user
                and not any(q in short_user for q in ["alabilir", "istiyorum", "verir", "?", "mı", "mi"]))
        )
        if is_farewell:
            print("\n--- Yeni müşteri oturumu başladı ---")
            llm.reset_history()
            new_customer = True


def main() -> None:
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n\nDemo sonlandırıldı.")


if __name__ == "__main__":
    main()
