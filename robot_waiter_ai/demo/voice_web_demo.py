"""
Minimal local browser-based voice demo for the deterministic waiter assistant.
"""
from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Protocol, Tuple

from robot_waiter_ai.inference.grounded_demo import run_grounded_demo
from robot_waiter_ai.inference.menu_context_builder import build_menu_context


BASE_DIR = Path(__file__).resolve().parent
HTML_PATH = BASE_DIR / "voice_web_demo.html"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_BACKEND = "deterministic"
DEFAULT_QWEN_BASE_MODEL_PATH = "robot_waiter_ai/models/Qwen2.5-3B-Instruct"
DEFAULT_QWEN_ADAPTER_PATH = "robot_waiter_ai/models/qwen25_3b_waiter_v1_1_lora"


class QwenBackend(Protocol):
    def generate_reply(self, user_message: str, menu_context: str | None = None) -> str:
        ...


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
        return HTTPStatus.OK, response
    except ValueError as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive demo path
        return HTTPStatus.INTERNAL_SERVER_ERROR, {
            "error": "Demo request failed.",
            "details": str(exc),
        }


def _handler_class(
    html_path: Path,
    backend: str,
    qwen_backend: Optional[QwenBackend],
    menu_context: Optional[str],
) -> type[BaseHTTPRequestHandler]:
    class VoiceDemoHandler(BaseHTTPRequestHandler):
        def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self) -> None:
            body = html_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path in {"/", "/index.html"}:
                self._send_html()
                return
            if self.path == "/health":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "status": "ok",
                        "runtime_llm": "qwen" if backend == "qwen" else "not integrated",
                        "scope": "menu-grounded waiter conversation",
                    },
                )
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/chat":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
                return

            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            status_code, payload = handle_chat_request(
                raw_body,
                backend=backend,
                qwen_backend=qwen_backend,
                menu_context=menu_context,
            )
            self._send_json(status_code, payload)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

    return VoiceDemoHandler


def _load_qwen_backend(adapter_path: Path, base_model_path: str, load_in_4bit: bool) -> QwenBackend:
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


def run_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    backend: str = DEFAULT_BACKEND,
    qwen_base_model_path: str = DEFAULT_QWEN_BASE_MODEL_PATH,
    qwen_adapter_path: str = DEFAULT_QWEN_ADAPTER_PATH,
    load_in_4bit: bool = True,
) -> None:
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

    handler_class = _handler_class(HTML_PATH, backend, qwen_backend, menu_context)
    try:
        server = ThreadingHTTPServer((host, port), handler_class)
    except OSError as exc:
        if isinstance(exc, PermissionError) or getattr(exc, "errno", None) in {48, 98}:
            print(f"Port {port} is unavailable. Try: python -m robot_waiter_ai.demo.voice_web_demo --port 8001")
        raise
    print("Voice web demo is running.")
    print(f"Open: http://{host}:{port}")
    print("Browser note: Chrome or Edge is recommended for Web Speech API support.")
    print("Allow microphone permission when prompted.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nVoice web demo stopped.")
    finally:
        server.server_close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the local browser-based voice demo for the deterministic waiter assistant."
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host to bind (default: {DEFAULT_HOST})")
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to bind (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--backend",
        default=DEFAULT_BACKEND,
        choices=("deterministic", "qwen"),
        help="Backend to use (default: deterministic)",
    )
    parser.add_argument(
        "--qwen-base-model-path",
        default=DEFAULT_QWEN_BASE_MODEL_PATH,
        help="Local base model path or Hugging Face model id for the Qwen backend",
    )
    parser.add_argument(
        "--qwen-adapter-path",
        default=DEFAULT_QWEN_ADAPTER_PATH,
        help="Path to the Qwen LoRA adapter directory",
    )
    parser.add_argument(
        "--no-4bit",
        action="store_true",
        help="Disable 4-bit loading for the Qwen backend",
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
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
