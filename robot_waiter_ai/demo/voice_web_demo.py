"""
Minimal local browser-based voice demo — FastAPI edition.

Routes
------
GET  /           -> voice_web_demo.html
GET  /health     -> JSON status probe
GET  /tts?text=  -> synthesise Turkish speech, returns audio/mpeg bytes
POST /chat       -> text message -> assistant reply (JSON)
POST /transcribe -> raw audio bytes -> {"text": "..."} via faster-whisper STT
POST /listen     -> ReSpeaker capture -> {"text": "..."} via faster-whisper STT
WS   /ws/tts     -> streaming TTS: send text, receive MP3 chunks
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Protocol, Tuple

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse, Response as FResponse

from robot_waiter_ai.inference.grounded_demo import run_grounded_demo
from robot_waiter_ai.inference.menu_context_builder import (
    _extract_menu_item_names,
    build_menu_context,
)
from robot_waiter_ai.speech.stt import SpeechToText
from robot_waiter_ai.speech.tts import PiperTTS, TextToSpeech

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
HTML_PATH = BASE_DIR / "voice_web_demo.html"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_BACKEND = "deterministic"
DEFAULT_QWEN_BASE_MODEL_PATH = "robot_waiter_ai/models/Qwen2.5-3B-Instruct"
DEFAULT_QWEN_ADAPTER_PATH = "robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora"
DEFAULT_STT_MODEL = "small"
DEFAULT_STT_DEVICE = "cpu"
DEFAULT_STT_COMPUTE_TYPE = "int8"
DEFAULT_TTS_VOICE = "tr-TR-EmelNeural"
DEFAULT_TTS_ENGINE = "piper"
DEFAULT_MIC_SECONDS = 4.0
MAX_MIC_SECONDS = 30.0
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB hard cap for /transcribe uploads


class QwenBackend(Protocol):
    def generate_reply(self, user_message: str, menu_context: str | None = None) -> str:
        ...


class CaptureMic(Protocol):
    is_capturing: bool

    async def capture(self, seconds: float | None = None) -> bytes:
        ...


# ---------------------------------------------------------------------------
# /chat helpers (pure — no HTTP framework dependency, tested directly)
# ---------------------------------------------------------------------------

def build_chat_response(
    message: str,
    backend: str = DEFAULT_BACKEND,
    qwen_backend: Optional[QwenBackend] = None,
    menu_context: Optional[str] = None,
) -> Dict[str, Any]:
    cleaned = message.strip()
    if not cleaned:
        raise ValueError("Message must not be empty.")

    if backend == "deterministic":
        payload = run_grounded_demo(cleaned)
        return {
            "message": cleaned,
            "response": str(payload.get("final_response") or ""),
            "intent": str(payload.get("detected_intent") or ""),
            "metadata": dict(payload.get("metadata") or {}),
        }
    if backend == "qwen":
        if qwen_backend is None:
            raise RuntimeError("Qwen backend is not initialized.")
        reply = qwen_backend.generate_reply(cleaned, menu_context=menu_context)
        return {
            "message": cleaned,
            "response": str(reply),
            "intent": "llm_response",
            "metadata": {"backend": "qwen"},
        }
    raise ValueError(f"Unsupported backend: {backend}")


def _read_request_json(raw_body: bytes) -> Dict[str, Any]:
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid JSON request body.") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object.")
    return payload


def handle_chat_request(
    raw_body: bytes,
    backend: str = DEFAULT_BACKEND,
    qwen_backend: Optional[QwenBackend] = None,
    menu_context: Optional[str] = None,
) -> Tuple[int, Dict[str, Any]]:
    try:
        payload = _read_request_json(raw_body)
        message = payload.get("message")
        if not isinstance(message, str):
            raise ValueError("Field 'message' must be a string.")
        response = build_chat_response(
            message,
            backend=backend,
            qwen_backend=qwen_backend,
            menu_context=menu_context,
        )
        return 200, response
    except ValueError as exc:
        return 400, {"error": str(exc)}
    except Exception as exc:  # pragma: no cover
        return 500, {"error": "Demo request failed.", "details": str(exc)}


def handle_transcribe_request(
    audio_bytes: bytes,
    *,
    stt: Optional[SpeechToText] = None,
    use_vad: bool = True,
    initial_prompt: Optional[str] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Pure helper: transcribe *audio_bytes* and return (status_code, payload).

    Decoupled from any HTTP framework so it can be called directly in unit tests.
    """
    _stt = stt if stt is not None else SpeechToText()
    try:
        result = asyncio.run(
            _stt.transcribe(audio_bytes, use_vad=use_vad, initial_prompt=initial_prompt)
        )
        return 200, result
    except Exception as exc:  # pragma: no cover
        logger.exception("STT transcription failed.")
        return 500, {"error": "Transcription failed.", "details": str(exc)}


# ---------------------------------------------------------------------------
# FastAPI app factory
# ---------------------------------------------------------------------------

def create_app(
    html_path: Path = HTML_PATH,
    backend: str = DEFAULT_BACKEND,
    qwen_backend: Optional[QwenBackend] = None,
    menu_context: Optional[str] = None,
    stt: Optional[SpeechToText] = None,
    use_vad: bool = True,
    stt_prompt: Optional[str] = None,
    tts: Optional[TextToSpeech] = None,
    mic_enabled: bool = False,
    mic: Optional[CaptureMic] = None,
    mic_seconds: float = DEFAULT_MIC_SECONDS,
) -> FastAPI:
    """Build and return a FastAPI application instance.

    All state (stt, tts, mic, lock) is captured via closure so the app is
    fully self-contained and safe to instantiate multiple times in tests.
    """
    _stt: SpeechToText = stt or SpeechToText()
    _tts: Any = tts or TextToSpeech()
    _mic_lock = asyncio.Lock()

    app = FastAPI(title="GarsonBot Voice Demo")

    # ------------------------------------------------------------------ GET /
    @app.get("/")
    async def index() -> HTMLResponse:
        return HTMLResponse(html_path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------ GET /health
    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {
            "status": "ok",
            "runtime_llm": "qwen" if backend == "qwen" else "not integrated",
            "runtime_stt": "faster-whisper",
            "runtime_tts": "edge-tts",
            "scope": "menu-grounded waiter conversation",
        }

    # -------------------------------------------------------------- POST /chat
    @app.post("/chat")
    async def chat(request: Request) -> JSONResponse:
        raw_body = await request.body()
        status_code, payload = handle_chat_request(
            raw_body,
            backend=backend,
            qwen_backend=qwen_backend,
            menu_context=menu_context,
        )
        return JSONResponse(payload, status_code=status_code)

    # --------------------------------------------------------- POST /transcribe
    @app.post("/transcribe")
    async def transcribe(request: Request) -> JSONResponse:
        # Reject oversized requests based on declared Content-Length before
        # reading the body (avoids buffering 10+ MB unnecessarily).
        cl = request.headers.get("content-length")
        if cl is None:
            return JSONResponse({"error": "Gecersiz istek."}, status_code=400)
        try:
            content_length = int(cl)
            if content_length < 0:
                raise ValueError("negative")
        except ValueError:
            return JSONResponse({"error": "Gecersiz istek."}, status_code=400)

        if content_length > MAX_AUDIO_BYTES:
            return JSONResponse({"error": "Ses dosyasi cok buyuk."}, status_code=413)

        body = await request.body()
        try:
            result = await _stt.transcribe(body, use_vad=use_vad, initial_prompt=stt_prompt)
            return JSONResponse(result)
        except Exception as exc:  # pragma: no cover
            logger.exception("STT transcription failed.")
            return JSONResponse(
                {"error": "Transcription failed.", "details": str(exc)}, status_code=500
            )

    # ------------------------------------------------------------- POST /listen
    @app.post("/listen")
    async def listen_route() -> JSONResponse:
        if not mic_enabled:
            return JSONResponse({"error": "Mikrofon devre dışı"}, status_code=503)
        if mic is None:
            return JSONResponse({"error": "Mikrofon kullanılamıyor"}, status_code=503)
        # Non-blocking lock check: asyncio is single-threaded so no race between
        # locked() check and acquire() — no await between them.
        if _mic_lock.locked():
            return JSONResponse({"error": "Zaten kayıt yapılıyor"}, status_code=503)
        async with _mic_lock:
            if mic.is_capturing:
                return JSONResponse({"error": "Zaten kayıt yapılıyor"}, status_code=503)
            try:
                wav_bytes = await mic.capture(seconds=mic_seconds)
                result = await _stt.transcribe(
                    wav_bytes, use_vad=use_vad, initial_prompt=stt_prompt
                )
                return JSONResponse(result)
            except RuntimeError as exc:
                if "Zaten kayıt yapılıyor" in str(exc):
                    return JSONResponse({"error": "Zaten kayıt yapılıyor"}, status_code=503)
                logger.exception("Microphone capture failed.")
                return JSONResponse(
                    {"error": "Mikrofon kullanılamıyor", "details": str(exc)}, status_code=503
                )
            except Exception as exc:  # pragma: no cover
                logger.exception("Listen request failed.")
                return JSONResponse(
                    {"error": "Ses dinleme başarısız.", "details": str(exc)}, status_code=500
                )

    # --------------------------------------------------------------- GET /tts
    @app.get("/tts")
    async def tts_endpoint(text: Optional[str] = None) -> FResponse:
        if not text or not text.strip():
            return JSONResponse({"error": "Metin parametresi gerekli."}, status_code=400)
        try:
            audio_bytes = await _tts.synthesize(text)
            content_type = getattr(_tts, "AUDIO_CONTENT_TYPE", "audio/mpeg")
            return FResponse(
                audio_bytes,
                media_type=content_type,
                headers={"Cache-Control": "no-cache"},
            )
        except ValueError:
            return JSONResponse({"error": "Metin parametresi gerekli."}, status_code=400)
        except Exception as exc:  # pragma: no cover
            logger.exception("TTS synthesis failed.")
            return JSONResponse({"error": "Ses uretimi basarisiz."}, status_code=500)

    # ------------------------------------------------------------ WS /ws/tts
    @app.websocket("/ws/tts")
    async def tts_stream(websocket: WebSocket) -> None:
        """Streaming TTS over WebSocket.

        Protocol:
          1. Client connects and sends a UTF-8 text message (the text to speak).
          2. Server streams MP3 audio chunks as binary frames.
          3. Server closes the connection when synthesis is complete.
        """
        await websocket.accept()
        try:
            text = await websocket.receive_text()
            if not text.strip():
                await websocket.send_json({"error": "Metin bos olamaz."})
                await websocket.close(code=1008)
                return
            async for chunk in _tts.synthesize_streaming(text):
                await websocket.send_bytes(chunk)
        except Exception:
            pass
        finally:
            try:
                await websocket.close()
            except Exception:
                pass

    return app


# ---------------------------------------------------------------------------
# Backend loaders
# ---------------------------------------------------------------------------

def _load_qwen_backend(
    adapter_path: Path, base_model_path: str, load_in_4bit: bool
) -> QwenBackend:
    try:
        from robot_waiter_ai.inference.qwen_lora_waiter import QwenLoraWaiterBackend
    except Exception as exc:
        raise RuntimeError(
            "Qwen backend is unavailable. Install requirements-llm.txt and try again."
        ) from exc
    return QwenLoraWaiterBackend(
        adapter_path=str(adapter_path),
        base_model_path=base_model_path,
        load_in_4bit=load_in_4bit,
    )


def _open_respeaker_mic(capture_seconds: float) -> CaptureMic:
    from robot_waiter_ai.speech.mic import ReSpeakerMic

    mic = ReSpeakerMic(
        capture_seconds=capture_seconds,
        max_capture_seconds=MAX_MIC_SECONDS,
    )
    asyncio.run(mic.open())
    return mic


# ---------------------------------------------------------------------------
# Server entrypoint
# ---------------------------------------------------------------------------

def run_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    backend: str = DEFAULT_BACKEND,
    qwen_base_model_path: str = DEFAULT_QWEN_BASE_MODEL_PATH,
    qwen_adapter_path: str = DEFAULT_QWEN_ADAPTER_PATH,
    load_in_4bit: bool = True,
    stt_model: str = DEFAULT_STT_MODEL,
    stt_device: str = DEFAULT_STT_DEVICE,
    stt_compute_type: str = DEFAULT_STT_COMPUTE_TYPE,
    use_vad: bool = True,
    tts_voice: str = DEFAULT_TTS_VOICE,
    tts_engine: str = DEFAULT_TTS_ENGINE,
    enable_mic: bool = False,
    mic_seconds: float = DEFAULT_MIC_SECONDS,
) -> None:
    if not 0 < mic_seconds <= MAX_MIC_SECONDS:
        raise ValueError(f"mic_seconds must be between 0 and {MAX_MIC_SECONDS:g}.")

    if not HTML_PATH.exists():
        raise FileNotFoundError(f"HTML arayuzu bulunamadi: {HTML_PATH}")

    # --- Qwen backend (optional) ---
    qwen_backend: Optional[QwenBackend] = None
    menu_context: Optional[str] = None
    if backend == "qwen":
        adapter_path = Path(qwen_adapter_path)
        try:
            menu_context = build_menu_context()
            qwen_backend = _load_qwen_backend(
                adapter_path,
                base_model_path=qwen_base_model_path,
                load_in_4bit=load_in_4bit,
            )
        except Exception as exc:
            print(f"Qwen backend failed to load: {exc}")
            raise

    # --- STT ---
    menu_names = _extract_menu_item_names()
    stt_prompt: str | None = SpeechToText.build_initial_prompt(menu_names) or None
    stt = SpeechToText(model_size=stt_model, device=stt_device, compute_type=stt_compute_type)
    print(
        f"STT: faster-whisper '{stt_model}' on {stt_device}/{stt_compute_type}"
        f" | VAD={'on' if use_vad else 'off'}"
        f" | prompt={len(stt_prompt or '')} chars"
    )
    print("      Model will load on the first /transcribe request.")

    # --- TTS ---
    tts: Any
    if tts_engine == "piper":
        try:
            tts = PiperTTS()
            print(f"TTS: Piper offline  binary={tts._binary}  model={tts._model.name}")
        except RuntimeError as exc:
            print(f"TTS: Piper bulunamadı ({exc}), edge-tts'e fallback yapılıyor")
            tts = TextToSpeech(voice=tts_voice)
            print(f"TTS: edge-tts voice='{tts_voice}' (internet gerekli)")
    else:
        tts = TextToSpeech(voice=tts_voice)
        print(f"TTS: edge-tts voice='{tts_voice}' (internet gerekli)")

    # --- Mic (opt-in) ---
    mic: CaptureMic | None = None
    if enable_mic:
        try:
            mic = _open_respeaker_mic(mic_seconds)
            print(f"Mic: ReSpeaker server-side capture enabled ({mic_seconds:g} s)")
        except Exception as exc:
            logger.warning("ReSpeaker microphone unavailable: %s", exc)
            print(f"Mic: ReSpeaker kullanilamiyor ({exc})")
    else:
        print("Mic: server-side ReSpeaker capture disabled")

    app = create_app(
        html_path=HTML_PATH,
        backend=backend,
        qwen_backend=qwen_backend,
        menu_context=menu_context,
        stt=stt,
        use_vad=use_vad,
        stt_prompt=stt_prompt,
        tts=tts,
        mic_enabled=enable_mic,
        mic=mic,
        mic_seconds=mic_seconds,
    )

    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            "uvicorn gerekli: pip install 'uvicorn[standard]'"
        ) from exc

    print("Voice web demo is running.")
    print(f"Open: http://{host}:{port}")
    print("Browser note: Chrome or Edge is recommended.")
    print("Allow microphone permission when prompted.")

    try:
        uvicorn.run(app, host=host, port=port, log_level="warning")
    except (OSError, PermissionError):
        print(f"Port {port} is unavailable. Try --port {port + 1}")
        raise
    except KeyboardInterrupt:
        print("\nVoice web demo stopped.")
    finally:
        if mic is not None and hasattr(mic, "close"):
            asyncio.run(mic.close())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_mic_seconds(value: str) -> float:
    seconds = float(value)
    if not 0 < seconds <= MAX_MIC_SECONDS:
        raise argparse.ArgumentTypeError(
            f"mic seconds must be between 0 and {MAX_MIC_SECONDS:g}"
        )
    return seconds


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the local browser-based voice demo for the deterministic waiter assistant."
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--backend", default=DEFAULT_BACKEND, choices=("deterministic", "qwen")
    )
    parser.add_argument("--qwen-base-model-path", default=DEFAULT_QWEN_BASE_MODEL_PATH)
    parser.add_argument("--qwen-adapter-path", default=DEFAULT_QWEN_ADAPTER_PATH)
    parser.add_argument("--no-4bit", action="store_true")
    parser.add_argument("--stt-model", default=DEFAULT_STT_MODEL)
    parser.add_argument("--stt-device", default=DEFAULT_STT_DEVICE, choices=("cpu", "cuda"))
    parser.add_argument(
        "--stt-compute-type", default=DEFAULT_STT_COMPUTE_TYPE,
        choices=("int8", "float16", "float32"),
    )
    parser.add_argument("--no-vad", action="store_true")
    parser.add_argument(
        "--tts-voice", default=DEFAULT_TTS_VOICE,
        choices=["tr-TR-EmelNeural", "tr-TR-AhmetNeural"],
    )
    parser.add_argument(
        "--tts-engine", default=DEFAULT_TTS_ENGINE,
        choices=["piper", "edge-tts"],
    )
    parser.add_argument("--enable-mic", action="store_true")
    parser.add_argument(
        "--mic-seconds", type=_parse_mic_seconds, default=DEFAULT_MIC_SECONDS
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    run_server(
        host=args.host,
        port=args.port,
        backend=args.backend,
        qwen_base_model_path=args.qwen_base_model_path,
        qwen_adapter_path=args.qwen_adapter_path,
        load_in_4bit=not args.no_4bit,
        stt_model=args.stt_model,
        stt_device=args.stt_device,
        stt_compute_type=args.stt_compute_type,
        use_vad=not args.no_vad,
        tts_voice=args.tts_voice,
        tts_engine=args.tts_engine,
        enable_mic=args.enable_mic,
        mic_seconds=args.mic_seconds,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
