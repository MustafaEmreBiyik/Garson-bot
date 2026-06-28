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
import collections
from typing import Any
import io
import logging
import re
import sys
import threading
import wave

import yaml
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
CHANNELS       = 1

# VAD kayıt parametreleri
VAD_AGGRESSIVENESS = 3     # webrtcvad sertliği 0-3 (3 = en agresif, gürültülü ortam)
VAD_CHUNK_MS       = 30    # webrtcvad geçerli değerleri: 10, 20, 30
VAD_SILENCE_S      = 1.5   # konuşma bittikten sonra bu kadar sessizlik → kaydı bitir
VAD_PRE_ROLL       = 5     # konuşma başlamadan önce tutulacak chunk (5×30ms = 150ms)
VAD_MAX_S          = 12    # güvenlik kapağı — en fazla bu kadar kayıt yap
VAD_ENERGY_THRESH  = 300   # webrtcvad yoksa enerji eşiği (0–32767 arası int16 RMS)
CONVO_HOLD_S       = 10    # bot yanıtından sonra wake word'süz dinleme penceresi

WHISPER_MODEL = "medium"  # Jetson 16GB CUDA — 1.7s latency, small'dan daha iyi Türkçe kalitesi
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
ALSA_OUTPUT_DEVICE: str | None = "plughw:3,0"  # Jetson USB Audio Device (card 3)

# Cümle sonu tespiti: nokta/ünlem/soru işaretinden sonra boşluk veya newline
_SENT_RE = re.compile(r'(?<=[.!?])[ \t\n]')


_MENU_YAML_PATH = Path(__file__).resolve().parent.parent / "robot_waiter_ai" / "data" / "menu.yaml"

_ORDER_VERBS  = {"istiyorum", "alayım", "alabilir", "getirir", "lütfen",
                 "tane", "adet", "istiyom", "alalım", "getir", "ver"}
_CANCEL_VERBS = {"istemiyorum", "istemiyom", "iptal", "çıkar", "çıkarın", "kaldır"}
_QUANTITIES   = {"iki": 2, "üç": 3, "dört": 4, "2": 2, "3": 3, "4": 4}
_DESCRIPTION_TRIGGERS = {"nasıl", "nedir", "ne gibi", "tarif", "anlat", "hakkında"}

_STT_LANG_PROB_MIN   = 0.50   # Guard 1: Whisper dil güven eşiği
_STT_MIN_WORDS_FRESH = 2      # Guard 1: Fresh turn'de ≤ bu kadar kelime → VAD kesimi şüpheli
_VAGUE_TERMS         = {"şey", "şeyler", "birşey", "birşeyler"}
_CONFIRM_STARTS      = {"evet", "hayır", "tabii", "tamam", "olur", "olmaz", "peki", "kesinlikle"}
_OFFENSIVE_TERMS     = {
    "salak", "gerizekalı", "geri zekalı", "aptal", "ahmak",
    "mankafa", "embesil", "şerefsiz", "piç", "orospu",
    "siktir", "oç", "göt",
}


def _load_menu_lookup() -> list[tuple[list[str], str, int]]:
    """(aliases, name, price) listesi döndür."""
    if not _MENU_YAML_PATH.exists():
        return []
    with open(_MENU_YAML_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    result = []
    for item in data.get("menu", []):
        aliases = [a.lower() for a in item.get("aliases", [])]
        aliases.append(item["name"].lower())
        result.append((aliases, item["name"], item["price"]))
    return result


def _match_items(t: str, lookup: list) -> list[tuple[str, int, int]]:
    """t içindeki menü öğelerini bul; [(name, price, qty)] döndür."""
    matches = []
    for aliases, name, price in lookup:
        for alias in aliases:
            if alias not in t:
                continue
            # Alias'dan önce gelen 1-2 kelimeye bak — miktar olabilir
            # "iki köfte" → 1 kelime; "iki tane köfte" → 2 kelime
            m1 = re.search(r'(\w+)\s+' + re.escape(alias), t)
            m2 = re.search(r'(\w+)\s+\w+\s+' + re.escape(alias), t)
            qty = 1
            if m1:
                qty = _QUANTITIES.get(m1.group(1), 1)
            if qty == 1 and m2:
                qty = _QUANTITIES.get(m2.group(1), 1)
            matches.append((name, price, qty))
            break  # Bu ürün için ilk eşleşen alias yeterli
    return matches


class OrderTracker:
    """Kullanıcı metninden menü ürünü tespit eder, toplamı takip eder."""

    def __init__(self) -> None:
        self._total = 0
        self._lookup = _load_menu_lookup()

    def detect_order(self, user_text: str) -> None:
        """Sipariş/iptal/takas niyetini tespit et ve toplamı güncelle.

        Üç durum:
          - "X yerine Y": X'i çıkar, Y'yi ekle.
          - "X iptal / X istemiyorum": X'i çıkar.
          - "X alayım / Y istiyorum": X'i ekle.
        """
        # "İ".lower() → "i̇" (birleştirme noktası) → regex kopar; temizle
        t = user_text.lower().replace('̇', '')

        is_cancel = any(v in t for v in _CANCEL_VERBS)
        is_swap   = "yerine" in t

        if is_swap:
            # "X yerine Y istiyorum" — sol: iptal, sağ: ekle
            before, after = t.split("yerine", 1)
            for _, price, qty in _match_items(before, self._lookup):
                self._total = max(0, self._total - price * qty)
            for _, price, qty in _match_items(after, self._lookup):
                self._total += price * qty
            return

        if is_cancel:
            # "X iptal" / "X istemiyorum" — eşleşen ürünleri çıkar
            for _, price, qty in _match_items(t, self._lookup):
                self._total = max(0, self._total - price * qty)
            return

        # Normal sipariş — eylem fiili yoksa dikkate alma
        if not any(v in t for v in _ORDER_VERBS):
            return
        for _, price, qty in _match_items(t, self._lookup):
            self._total += price * qty

    @property
    def total(self) -> int:
        return self._total

    def reset(self) -> None:
        self._total = 0


_BILL_KEYWORDS = ["hesab", "hesap", "ödeyeyim", "ödüyorum", "parayı öde",
                  "toplam", "tutar", "ne kadar tut", "kaç tl", "kaç lira"]


def _is_bill_request(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in _BILL_KEYWORDS)


def _is_description_question(user_text: str, lookup: list) -> bool:
    """Kullanıcı menüdeki bir ürün hakkında açıklama soruyor mu? (E19 fix)"""
    t = user_text.lower().replace('̇', '')
    if not any(w in t for w in _DESCRIPTION_TRIGGERS):
        return False
    for aliases, _, _ in lookup:
        for alias in aliases:
            if alias in t:
                return True
    return False


def _stt_low_confidence(result: dict, text: str, *, in_convo: bool) -> bool:
    """Guard 1: STT güvensizse True döndür.

    (a) language_probability eşiğin altındaysa — Whisper Türkçe'den emin değil.
    (b) Fresh turn (in_convo=False) VE çok kısa metin — VAD erken kesti.
    Conversation hold'da kelime sayısı koşulu uygulanmaz: "evet", "tamam" geçerli.
    """
    lang_prob = result.get("language_probability", 1.0)
    if lang_prob < _STT_LANG_PROB_MIN:
        return True
    if not in_convo and len(text.split()) <= _STT_MIN_WORDS_FRESH:
        return True
    return False


def _is_off_menu_order(text: str, lookup: list, *, in_convo: bool) -> bool:
    """Guard 2: Sipariş fiili var ama menü eşleşmiyorsa True döndür.

    Tüm koşullar aynı anda doğru olmalı:
      1. _ORDER_VERBS metinde var
      2. _match_items() boş döndü
      3. _VAGUE_TERMS yok ("birşey istiyorum" → LLM'e bırak)
      4. İlk kelime _CONFIRM_STARTS'ta değil ("evet, alayım" → LLM'e bırak)
      5. Fiil/miktar/stopword çıktıktan sonra en az 1 içerik kelimesi kalıyor
    """
    t = text.lower().replace('̇', '')
    if not any(v in t for v in _ORDER_VERBS):
        return False
    if _match_items(t, lookup):
        return False
    if any(vague in t for vague in _VAGUE_TERMS):
        return False
    words = t.split()
    if not words or words[0] in _CONFIRM_STARTS:
        return False
    _STOPWORDS = {"bir", "de", "da", "ile", "ve", "mi", "mı", "mu", "mü",
                  "lütfen", "acaba", "bana", "bize", "buraya"}
    noise = _ORDER_VERBS | set(_QUANTITIES.keys()) | _STOPWORDS
    content_words = [w for w in words if w not in noise]
    return len(content_words) >= 1


def _is_offensive(text: str) -> bool:
    """Guard 3: Hakaret veya küfür içeriyorsa True döndür."""
    t = text.lower().replace('̇', '')
    return any(term in t for term in _OFFENSIVE_TERMS)


def _find_input_device() -> int | None:
    """USB ses giriş cihazının sounddevice index'ini döndür, bulamazsa None.

    "USB PnP" / "PnP Sound" cihazını önceliklendir — Jetson'da bu genellikle
    gerçek mikrofondur; USB Audio Device ise hoparlör+mikrofon adapttörü olup
    giriş kalitesi daha düşük olabilir.
    """
    devices = list(enumerate(sd.query_devices()))
    # Önce USB PnP / standalone mic ara
    for i, d in devices:
        if "USB" in d["name"] and "PnP" in d["name"] and d["max_input_channels"] > 0:
            return i
    # Bulamazsa ilk USB giriş cihazına dön
    for i, d in devices:
        if "USB" in d["name"] and d["max_input_channels"] > 0:
            return i
    return None


def _find_output_device() -> str | None:
    """USB hoparlörün ALSA cihaz string'ini ('plughw:X,Y') döndür.

    sounddevice cihaz isimlerindeki '(hw:KART,CİHAZ)' ifadesini ayrıştırır.
    "USB Audio" içeren ama "PnP" içermeyen (= hoparlör) ve çıkış kanalı olan
    cihazı bulur. Kart numarası replug/boot'ta değişse de isim sabit kalır.
    Bulamazsa None (ALSA_OUTPUT_DEVICE sabiti fallback olarak kalır).
    """
    for d in sd.query_devices():
        name = d["name"]
        if "USB Audio" in name and "PnP" not in name and d["max_output_channels"] > 0:
            m = re.search(r"hw:(\d+),(\d+)", name)
            if m:
                return f"plughw:{m.group(1)},{m.group(2)}"
    return None


class _OpenAIWhisperSTT:
    """openai-whisper CPU fallback — faster-whisper/CTranslate2 SGEMM yoksa kullan."""

    def __init__(self, model_size: str = "small") -> None:
        import whisper as _ow
        print(f"  STT: openai-whisper '{model_size}' yükleniyor (CPU)...")
        self._model = _ow.load_model(model_size)

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        language: str = "tr",
        initial_prompt: str | None = None,
        use_vad: bool = True,
    ) -> dict:
        import os as _os, tempfile as _tmp
        if not audio_bytes:
            return {"text": "", "segments": [], "language": language,
                    "language_probability": 0.0, "low_confidence": True}
        fd, tmp = _tmp.mkstemp(suffix=".wav")
        _os.close(fd)
        try:
            Path(tmp).write_bytes(audio_bytes)
            kw: dict = {"language": language, "fp16": False}
            if initial_prompt:
                kw["initial_prompt"] = initial_prompt
            result = await asyncio.to_thread(self._model.transcribe, tmp, **kw)
        finally:
            try:
                _os.unlink(tmp)
            except OSError:
                pass
        return {
            "text": result.get("text", ""),
            "segments": [{"start": s["start"], "end": s["end"], "text": s["text"]}
                         for s in result.get("segments", [])],
            "language": result.get("language", language),
            "language_probability": 1.0,
            "low_confidence": False,
        }


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


async def _speak_streaming(tts, llm, user_text: str,
                            tts_active: "threading.Event | None" = None) -> str:
    """LLM token akışını cümle cümle TTS'e ver; ilk sesi hızla başlat.

    Pipeline: LLM thread → sentence_q → tts_worker → audio_q → play_worker
    tts_worker ve play_worker eş zamanlı çalışır: biri sentezlerken diğeri çalar.
    """
    loop = asyncio.get_event_loop()
    sentence_q: asyncio.Queue = asyncio.Queue()
    audio_q: asyncio.Queue = asyncio.Queue(maxsize=2)
    spoken: list[str] = []

    def _run_llm():
        buf = ""
        try:
            for token in llm.stream_reply(user_text):
                buf += token
                while True:
                    m = _SENT_RE.search(buf)
                    if not m:
                        break
                    sentence = buf[:m.start()].strip()
                    buf = buf[m.end():]
                    if sentence:
                        loop.call_soon_threadsafe(sentence_q.put_nowait, sentence)
        except Exception as exc:
            logger.error("LLM stream hatası: %s", exc)
        finally:
            if buf.strip():
                loop.call_soon_threadsafe(sentence_q.put_nowait, buf.strip())
            loop.call_soon_threadsafe(sentence_q.put_nowait, None)

    async def _tts_worker():
        ctype = getattr(tts, "AUDIO_CONTENT_TYPE", "audio/wav")
        while True:
            sentence = await sentence_q.get()
            if sentence is None:
                await audio_q.put(None)
                break
            spoken.append(sentence)
            clean = re.sub(r'\*+', '', sentence).strip()
            if not clean:
                continue
            wav = await tts.synthesize(clean)
            await audio_q.put((wav, ctype))

    async def _play_worker():
        while True:
            item = await audio_q.get()
            if item is None:
                break
            wav, ctype = item
            if "wav" in ctype:
                await asyncio.to_thread(_play_wav, wav)
            else:
                await asyncio.to_thread(_play_mp3, wav)

    if tts_active is not None:
        tts_active.set()
    llm_thread = threading.Thread(target=_run_llm, daemon=True)
    llm_thread.start()
    try:
        await asyncio.gather(_tts_worker(), _play_worker())
    finally:
        if tts_active is not None:
            tts_active.clear()
        llm_thread.join(timeout=5)

    return " ".join(spoken)


def _beep() -> None:
    """Kısa onay bip tonu — wake word algılandığında çal."""
    t = np.linspace(0, 0.15, int(SAMPLE_RATE * 0.15), dtype=np.float32)
    tone = (np.sin(2 * np.pi * 880 * t) * 0.3).astype(np.float32)
    sd.play(tone, samplerate=SAMPLE_RATE)
    sd.wait()


def _resample_to_16k(audio: np.ndarray, from_sr: int) -> np.ndarray:
    """audio'yu from_sr'den SAMPLE_RATE'e düşür — numpy lineer interpolasyon."""
    if from_sr == SAMPLE_RATE:
        return audio
    target_len = int(len(audio) * SAMPLE_RATE / from_sr)
    return np.interp(
        np.linspace(0, len(audio) - 1, target_len),
        np.arange(len(audio)),
        audio.astype(np.float32),
    ).astype(np.int16)


def _record(input_device: int | None = None, *,
            initial_wait_s: float | None = None) -> bytes:
    """VAD tabanlı kayıt — sessizlik sonrası durur, maks VAD_MAX_S saniye.

    webrtcvad kuruluysa kullanır; yoksa enerji eşiğine döner.

    initial_wait_s: konuşma başlamadan beklenecek max süre. None ise VAD_MAX_S
    (mevcut davranış). Süre dolduğunda konuşma başlamadıysa boş bytes (b"")
    döndürülür — çağıran "kullanıcı konuşmadı" diye anlayabilir.
    """
    CHUNK_SAMPLES = SAMPLE_RATE * VAD_CHUNK_MS // 1000  # 16000*30//1000 = 480

    # webrtcvad veya enerji tabanlı fallback
    try:
        import webrtcvad as _wvad
        _v = _wvad.Vad(VAD_AGGRESSIVENESS)
        def _is_speech(pcm: bytes) -> bool:
            try:
                return _v.is_speech(pcm, SAMPLE_RATE)
            except Exception:
                return False
    except ImportError:
        def _is_speech(pcm: bytes) -> bool:
            arr = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
            return float(np.sqrt(np.mean(arr ** 2))) > VAD_ENERGY_THRESH

    # Native sample rate (USB mikler genelde 48 kHz)
    if input_device is not None:
        native_sr = int(sd.query_devices(input_device)["default_samplerate"])
    else:
        native_sr = SAMPLE_RATE
    native_chunk = int(native_sr * VAD_CHUNK_MS / 1000)

    silence_limit = int(VAD_SILENCE_S * 1000 / VAD_CHUNK_MS)
    max_chunks    = int(VAD_MAX_S    * 1000 / VAD_CHUNK_MS)
    # Konuşma başlamadan beklenecek max chunk; initial_wait_s verilmediyse max_chunks
    initial_max  = int(initial_wait_s * 1000 / VAD_CHUNK_MS) if initial_wait_s else max_chunks

    ring_buf    = collections.deque(maxlen=VAD_PRE_ROLL)
    voiced_16k: list[bytes] = []
    in_speech   = False
    silence_cnt = 0
    total       = 0

    print("  🎙  Dinliyorum...", flush=True)

    with sd.InputStream(samplerate=native_sr, channels=CHANNELS,
                        dtype="int16", blocksize=native_chunk,
                        device=input_device) as stream:
        while total < max_chunks:
            indata, _ = stream.read(native_chunk)
            total += 1
            chunk = indata[:, 0] if indata.ndim > 1 else indata.flatten()

            # 16 kHz'e dönüştür
            if native_sr != SAMPLE_RATE:
                chunk = _resample_to_16k(chunk, native_sr)

            # webrtcvad tam boyut ister — kırp ya da pad uygula
            if len(chunk) > CHUNK_SAMPLES:
                chunk = chunk[:CHUNK_SAMPLES]
            elif len(chunk) < CHUNK_SAMPLES:
                chunk = np.pad(chunk, (0, CHUNK_SAMPLES - len(chunk)))

            pcm    = chunk.astype(np.int16).tobytes()
            speech = _is_speech(pcm)

            if not in_speech:
                ring_buf.append(pcm)
                if speech:
                    in_speech = True
                    voiced_16k.extend(ring_buf)
                    ring_buf.clear()
                    silence_cnt = 0
                elif total >= initial_max:
                    # Konuşma başlamadan timeout — çağıran sessizlik diye anlasın
                    break
            else:
                voiced_16k.append(pcm)
                if speech:
                    silence_cnt = 0
                else:
                    silence_cnt += 1
                    if silence_cnt >= silence_limit:
                        elapsed = total * VAD_CHUNK_MS / 1000
                        print(f"  ✓  Alındı ({elapsed:.1f}s)", flush=True)
                        break

    if not voiced_16k:
        return b""  # konuşma yoktu — çağıran "sessizlik / timeout" diye değerlendirir

    audio = np.frombuffer(b"".join(voiced_16k), dtype=np.int16)
    return _numpy_to_wav(audio, SAMPLE_RATE)


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

    # USB mikler genelde 48kHz native — 16kHz'i reddedebilirler
    if input_device is not None:
        native_sr = int(sd.query_devices(input_device)["default_samplerate"])
    else:
        native_sr = SAMPLE_RATE
    native_chunk = int(native_sr * WAKEWORD_CHUNK / SAMPLE_RATE)

    # Stream açılırken buffer'da kalan ses kalıntısı ilk chunk'larda false positive yapar;
    # 10 chunk (10×80ms = 800ms) atla — kullanıcıya gecikme hissettirmez.
    _warm_up = [10]

    def _cb(indata, frames, time_info, status):
        if _warm_up[0] > 0:
            _warm_up[0] -= 1
            return
        if tts_active.is_set():
            return  # TTS çalarken tetikleme yapma (feedback engeli)
        if detected.is_set():
            return
        audio = (indata[:, 0] * 32768).astype(np.int16)
        if native_sr != SAMPLE_RATE:
            audio = _resample_to_16k(audio, native_sr)
        scores = ww_model.predict(audio)
        score  = float(list(scores.values())[0])
        if score > WAKEWORD_THRESHOLD:
            loop.call_soon_threadsafe(detected.set)

    with sd.InputStream(samplerate=native_sr, channels=1, dtype="float32",
                        blocksize=native_chunk, callback=_cb,
                        device=input_device):
        await detected.wait()


# ---------------------------------------------------------------------------
# Ana döngü
# ---------------------------------------------------------------------------

async def run_demo(adapter_dir: str | None = None) -> None:
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
        llm = Qwen3Backend(adapter_dir=adapter_dir)
        label = f"Qwen3Backend + adapter ({adapter_dir})" if adapter_dir else "Qwen3Backend (base)"
        print(f"LLM: {label}")

    # KV cache ön ısıtma — sistem promptu (944 tok) bir kez işle, tüm müşterilerin
    # ilk turn'ü soğuk start yerine sıcak (~0.25s TTFT) olsun.
    print("LLM KV cache ısıtılıyor…")
    await asyncio.to_thread(llm.generate_reply, "Merhaba.")
    llm.reset_history()
    try:
        import torch as _torch
        if _torch.cuda.is_available():
            _torch.cuda.empty_cache()
    except Exception:
        pass
    print("LLM: KV cache hazır")

    # STT cihaz seçimi — LLM ile aynı GPU'da çakışmasını önler.
    #   * Total VRAM < 8 GB ise CUDA'da Qwen3-4B + Whisper birlikte sığmaz (OOM)
    #     → CPU int8. Bu host (RTX 4050 6 GB) bu kategoride.
    #   * Total VRAM ≥ 8 GB (örn. Jetson Orin NX 16 GB) → CUDA float16.
    #   * W_BOT_STT_DEVICE env değişkeni ("cpu"/"cuda") ile manuel override.
    _STT_VRAM_THRESHOLD_GB = 8.0

    def _stt_backend():
        import os as _os
        override = _os.environ.get("W_BOT_STT_DEVICE", "").lower()
        if override != "cpu":
            # CTranslate2 CUDA'yı PyTorch'tan bağımsız sorgula (Jetson driver uyumu için)
            try:
                import ctranslate2 as _ct2
                if _ct2.get_supported_compute_types("cuda"):
                    print("  STT: CTranslate2 CUDA seçildi")
                    return "cuda", "float16"
            except Exception:
                pass
        try:
            import ctranslate2 as _ct2
            if "int8" in _ct2.get_supported_compute_types("cpu"):
                return "cpu", "int8"
        except Exception:
            pass
        return "cpu", "float32"

    _stt_dev, _stt_ct = _stt_backend()
    print(f"STT modeli yükleniyor... ({_stt_dev})")
    stt: Any = SpeechToText(model_size=WHISPER_MODEL, device=_stt_dev, compute_type=_stt_ct)
    silence_wav = _numpy_to_wav(np.zeros(SAMPLE_RATE, dtype=np.int16), SAMPLE_RATE)
    # SGEMM testi: gerçek ses benzeri küçük gürültüyle CTranslate2'yi doğrula
    _test_wav = _numpy_to_wav(
        (np.random.rand(SAMPLE_RATE // 4) * 200 - 100).astype(np.int16), SAMPLE_RATE
    )
    try:
        await stt.transcribe(_test_wav, language="tr")
        await stt.transcribe(silence_wav, language="tr", initial_prompt=STT_INITIAL_PROMPT)
        print("STT: hazır\n")
    except Exception as _stt_err:
        if "SGEMM" in str(_stt_err) or "backend" in str(_stt_err).lower() or "cuda" in str(_stt_err).lower():
            print(f"  ⚠ CTranslate2 hatası ({_stt_err}) → openai-whisper fallback")
            stt = _OpenAIWhisperSTT(model_size=WHISPER_MODEL)
            await stt.transcribe(silence_wav, language="tr")
            print("STT: openai-whisper hazır\n")
        else:
            raise

    # USB mikrofon cihazını otomatik bul
    input_device = _find_input_device()
    if input_device is not None:
        print(f"Mikrofon: device {input_device} ({sd.query_devices(input_device)['name'].strip()})")
    else:
        print("Mikrofon: varsayılan cihaz")

    # USB hoparlörü isimle oto-tespit — kart numarası replug/boot'ta kayabilir
    global ALSA_OUTPUT_DEVICE
    _detected_out = _find_output_device()
    if _detected_out:
        ALSA_OUTPUT_DEVICE = _detected_out
        print(f"Hoparlör: {_detected_out} (oto-tespit)")
    else:
        print(f"Hoparlör: {ALSA_OUTPUT_DEVICE} (sabit fallback)")

    order_tracker = OrderTracker()

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
    first_wakeword     = True
    new_customer       = True   # Her oturum başında karşıla
    conversation_active = False  # Yanıttan sonra wake word'süz dinleme penceresi açık mı?
    pending_reset      = False  # Farewell tespit edildi mi (10s sessizlik sonrası uygulanır)
    while True:
        # Tetikleyici: conversation hold | wake word | ENTER
        if conversation_active:
            # Yanıttan hemen sonra 10s pencere — wake word beklenmez
            wav_bytes = await asyncio.to_thread(
                _record, input_device, initial_wait_s=CONVO_HOLD_S)
            if not wav_bytes:
                # Sessizlik — wake word moduna geri dön
                print(f"  ⏰ {CONVO_HOLD_S}s sessizlik — 'hey garson' bekleniyor...", flush=True)
                conversation_active = False
                if pending_reset:
                    llm.reset_history()
                    order_tracker.reset()
                    new_customer = True
                    pending_reset = False
                    print("--- Yeni müşteri oturumu hazır ---", flush=True)
                if ww_model:
                    ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))
                continue
            # Konuşma geldi — farewell beklemesini iptal et, tur devam etsin
            pending_reset = False
        else:
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

            # Kayıt — mevcut davranış (VAD_MAX_S güvenlik kapağı)
            wav_bytes = await asyncio.to_thread(_record, input_device)
            if not wav_bytes:
                # Wake word algılandı ama konuşma gelmedi — tekrar wake word'e dön
                if ww_model:
                    ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))
                    print("\n  👂 'hey garson' bekleniyor...", flush=True)
                continue

        # STT
        import time as _time
        print("  ⏳ Anlıyorum...", flush=True)
        _t_stt = _time.perf_counter()
        try:
            result    = await stt.transcribe(wav_bytes, language="tr",
                                             initial_prompt=STT_INITIAL_PROMPT)
            user_text = result["text"].strip()
        except Exception as e:
            print(f"  ✗ STT hatası: {e}")
            conversation_active = False
            if ww_model:
                ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))
            continue
        _stt_ms = (_time.perf_counter() - _t_stt) * 1000

        if not user_text:
            print("  (Ses algılanamadı, tekrar dene)")
            conversation_active = False
            if ww_model:
                ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))
            continue

        print(f"\nMüşteri: {user_text}")
        print(f"  ⏱  STT: {_stt_ms:.0f}ms", flush=True)

        # --- Guard 1: STT düşük güven ---
        if _stt_low_confidence(result, user_text, in_convo=conversation_active):
            print("  ⚠  STT güven düşük — tekrar dinleniyor", flush=True)
            _guard1_msg = "Özür dilerim, tam anlayamadım. Tekrar söyler misiniz?"
            try:
                await _speak(tts, _guard1_msg, tts_active)
            except Exception as _g1e:
                logger.warning("Guard1 TTS hatası: %s", _g1e)
            conversation_active = True
            continue

        # --- Guard 2: Menü-dışı sipariş ---
        if _is_off_menu_order(user_text, order_tracker._lookup, in_convo=conversation_active):
            print("  ⚠  Menü-dışı ürün tespit edildi", flush=True)
            _guard2_msg = "Maalesef bu ürün menümüzde yok. Başka bir şey söyleyebilir miyim?"
            try:
                await _speak(tts, _guard2_msg, tts_active)
            except Exception as _g2e:
                logger.warning("Guard2 TTS hatası: %s", _g2e)
            conversation_active = True
            continue

        # --- Guard 3: Hakaret / küfür ---
        if _is_offensive(user_text):
            print("  ⚠  Uygunsuz dil tespit edildi", flush=True)
            _guard3_msg = "Yalnızca sipariş ve menü konularında yardımcı olabilirim. Başka bir şey söyleyebilir misiniz?"
            try:
                await _speak(tts, _guard3_msg, tts_active)
            except Exception as _g3e:
                logger.warning("Guard3 TTS hatası: %s", _g3e)
            conversation_active = True
            continue

        # 3+5. Streaming: LLM üretim + TTS sentez + oynatma paralel pipeline
        print("  ⏳ Yanıt üretiliyor...", flush=True)
        # Siparişi ÖNCE işle; aynı cümlede "sütlaç alayım + hesap" varsa doğru toplam gider
        order_tracker.detect_order(user_text)
        llm_input = user_text
        if _is_bill_request(user_text) and order_tracker.total > 0:
            t_lower = user_text.lower()
            has_new_order = any(v in t_lower for v in _ORDER_VERBS)
            if has_new_order:
                # Hem yeni sipariş hem hesap: yanıtın sonu toplamla bitmeli
                llm_input = (f"{user_text} [Yanıtın sonu şöyle bitmeli: "
                             f"Toplam {order_tracker.total} TL. Afiyet olsun!]")
            else:
                llm_input = f"{user_text} [Gerçek toplam: {order_tracker.total} TL]"
        _t_llm = _time.perf_counter()
        try:
            if _is_bill_request(user_text) and order_tracker.total > 0:
                # Hesap: streaming değil — toplam üretildikten sonra regex override
                import re as _re
                from robot_waiter_ai.inference.llama_cpp_backend import _strip_markdown as _sm
                raw = await asyncio.to_thread(llm.generate_reply, llm_input)
                raw = _sm(raw)
                correct = order_tracker.total
                raw = _re.sub(r'[Tt]oplam\s+\d[\d.\s]*TL', f'Toplam {correct} TL', raw)
                if 'oplam' not in raw:
                    raw = raw.rstrip('.!') + f'. Toplam {correct} TL.'
                await _speak(tts, raw, tts_active)
                reply = raw
            else:
                reply = await _speak_streaming(tts, llm, llm_input, tts_active)
                # E19 fix: ürün açıklaması sorusuna yanıt "?" ile bitmiyorsa ekle
                if (not reply.rstrip().endswith("?")
                        and _is_description_question(user_text, order_tracker._lookup)):
                    addition = "Getireyim mi?"
                    await _speak(tts, addition, tts_active)
                    reply = reply.rstrip() + " " + addition
        except Exception as e:
            print(f"  ✗ LLM/TTS hatası: {e}")
            if ww_model:
                ww_task = asyncio.create_task(_detect_wakeword(ww_model, tts_active, input_device))
            continue
        _llm_ms = (_time.perf_counter() - _t_llm) * 1000

        print(f"W-BOT:   {reply}")
        print(f"  ⏱  LLM+TTS: {_llm_ms:.0f}ms  |  Toplam: {_stt_ms + _llm_ms:.0f}ms")

        # Oturum sonu tespiti — müşteri veya bot veda ediyorsa 10s sonra sıfırla
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
            pending_reset = True
            print(f"  💤 Veda algılandı — {CONVO_HOLD_S}s sessizlik sonrası yeni müşteri için hazır")

        # Conversation hold penceresini aç; sessizlikte wake word'e dönülür
        conversation_active = True
        print(f"  ⏳ Devam etmek için konuşabilirsiniz ({CONVO_HOLD_S}s)...", flush=True)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="W-BOT demo")
    parser.add_argument("--adapter-dir", default=None,
                        help="LoRA adapter dizini (opsiyonel, sadece PC/transformers backend)")
    args = parser.parse_args()
    try:
        asyncio.run(run_demo(adapter_dir=args.adapter_dir))
    except KeyboardInterrupt:
        print("\n\nDemo sonlandırıldı.")


if __name__ == "__main__":
    main()
