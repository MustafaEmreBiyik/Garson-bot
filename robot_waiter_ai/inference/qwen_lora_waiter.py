from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

DEFAULT_BASE_MODEL_PATH = "robot_waiter_ai/models/Qwen2.5-3B-Instruct"
DEFAULT_BASE_MODEL_NAME = "Qwen/Qwen2.5-3B-Instruct"
DEFAULT_MAX_NEW_TOKENS = 120
DEFAULT_REPETITION_PENALTY = 1.05
SYSTEM_PROMPT = (
    "Sen Türkçe konuşan kibar bir restoran garson asistanısın. "
    "Müşteriyle doğal, kısa ve net konuş. "
    "Menü, fiyat, stok, kampanya, teslimat veya alerjen bilgisi uydurma. "
    "Kesin bilgi gerekiyorsa güncel menüye, personele veya mutfağa yönlendir. "
    "Restoran dışı konularda sohbeti nazikçe menü veya sipariş konusuna geri getir."
)
CONTEXT_GUARDRAIL = (
    "Yalnızca aşağıda verilen menü ve restoran bağlamını kullan. "
    "Fiyat, ürün, açılış saati, ödeme yöntemi, stok veya alerji güvenliği uydurma. "
    "Yanıt bağlamda yoksa güncel menüden, personelden veya mutfaktan kontrol edilmesi gerektiğini söyle."
)


class QwenLoraWaiterBackend:
    def __init__(
        self,
        adapter_path: str,
        base_model_path: str = DEFAULT_BASE_MODEL_PATH,
        load_in_4bit: bool = True,
    ) -> None:
        self.base_model_path = base_model_path
        self.load_in_4bit = load_in_4bit
        self.adapter_path = self._resolve_adapter_path(Path(adapter_path))
        self.base_model_source = self._resolve_base_model_source(base_model_path)
        self.tokenizer = None
        self.model = None
        self._torch = None
        self._load_model()

    @staticmethod
    def _resolve_adapter_path(adapter_path: Path) -> Path:
        if not adapter_path.exists():
            raise FileNotFoundError(
                f"LoRA adapter path not found: {adapter_path}\n"
                "Expected the adapter folder to contain adapter_config.json and adapter_model.safetensors."
            )

        direct_config = adapter_path / "adapter_config.json"
        if direct_config.exists():
            return adapter_path

        child_candidates = [
            child for child in adapter_path.iterdir() if child.is_dir() and (child / "adapter_config.json").exists()
        ]
        if len(child_candidates) == 1:
            return child_candidates[0]

        raise FileNotFoundError(
            "Could not find adapter_config.json in the provided adapter path. "
            "Point --qwen-adapter-path to the LoRA adapter directory."
        )

    @staticmethod
    def _resolve_base_model_source(base_model_path: str) -> str:
        candidate = Path(base_model_path)
        looks_like_path = any(sep in base_model_path for sep in ("\\", "/")) or candidate.drive != ""

        if candidate.exists():
            config_path = candidate / "config.json"
            if not config_path.exists():
                raise FileNotFoundError(
                    f"Base model folder exists but config.json is missing: {candidate}\n"
                    "Download Qwen/Qwen2.5-3B-Instruct into this folder before running the Qwen backend."
                )
            return str(candidate)

        if looks_like_path:
            raise FileNotFoundError(
                f"Base model path not found: {candidate}\n"
                "Offline/local Qwen requires the base model files in robot_waiter_ai/models/Qwen2.5-3B-Instruct."
            )

        return base_model_path

    def _load_model(self) -> None:
        try:
            import torch
        except ImportError as exc:
            raise ImportError(
                "Qwen backend requires optional LLM dependencies. Install requirements-llm.txt first."
            ) from exc

        try:
            from peft import PeftModel
        except ImportError as exc:
            raise ImportError(
                "Qwen backend requires 'peft'. Install requirements-llm.txt first."
            ) from exc

        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        except ImportError as exc:
            raise ImportError(
                "Qwen backend requires 'transformers'. Install requirements-llm.txt first."
            ) from exc

        quantization_config = None
        model_kwargs: dict[str, Any] = {
            "device_map": "auto",
            "low_cpu_mem_usage": True,
        }

        if self.load_in_4bit:
            try:
                import bitsandbytes  # noqa: F401
            except Exception as exc:
                raise RuntimeError(
                    "4-bit Qwen loading requested but bitsandbytes is unavailable. "
                    "This is common on Windows. Reinstall optional dependencies or rerun with --no-4bit."
                ) from exc

            quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            model_kwargs["quantization_config"] = quantization_config
            model_kwargs["torch_dtype"] = torch.float16
        elif torch.cuda.is_available():
            model_kwargs["torch_dtype"] = torch.float16
        else:
            model_kwargs["torch_dtype"] = torch.float32

        self._torch = torch

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(str(self.adapter_path), use_fast=False)
        except Exception:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_source, use_fast=False)
            except Exception as exc:
                raise RuntimeError(
                    "Tokenizer loading failed. Check that the local base model files are present and that "
                    "transformers/sentencepiece are installed."
                ) from exc

        if getattr(self.tokenizer, "pad_token", None) is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        try:
            base_model = AutoModelForCausalLM.from_pretrained(self.base_model_source, **model_kwargs)
        except Exception as exc:
            message = str(exc).lower()
            if "out of memory" in message or "cuda out of memory" in message:
                raise RuntimeError(
                    "Base model loading failed because there is not enough VRAM or RAM for this configuration. "
                    "Try --no-4bit carefully, or test the Qwen backend on Colab, Ubuntu, WSL2, or Jetson."
                ) from exc
            if "bitsandbytes" in message:
                raise RuntimeError(
                    "Base model loading failed because bitsandbytes is not working on this machine. "
                    "This is a common Windows issue. Retry with --no-4bit or use Colab, Ubuntu, WSL2, or Jetson."
                ) from exc
            if isinstance(exc, FileNotFoundError):
                raise
            raise RuntimeError(
                "Base model loading failed. Check that robot_waiter_ai/models/Qwen2.5-3B-Instruct contains "
                "the downloaded Qwen/Qwen2.5-3B-Instruct files and that optional LLM dependencies are installed."
            ) from exc

        try:
            self.model = PeftModel.from_pretrained(base_model, str(self.adapter_path))
        except Exception as exc:
            raise RuntimeError(
                "LoRA adapter loading failed. Check that the adapter folder contains adapter_config.json and "
                "adapter_model.safetensors and that it matches Qwen2.5-3B-Instruct."
            ) from exc
        self.model.eval()

    def _build_messages(self, user_message: str, menu_context: str | None = None) -> list[dict[str, str]]:
        cleaned = user_message.strip()
        if not cleaned:
            raise ValueError("User message must not be empty.")

        system_prompt = SYSTEM_PROMPT
        if menu_context:
            system_prompt = f"{system_prompt}\n{CONTEXT_GUARDRAIL}\n\nBağlam:\n{menu_context.strip()}"

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": cleaned},
        ]

    def _build_prompt(self, user_message: str, menu_context: str | None = None) -> str:
        messages = self._build_messages(user_message, menu_context=menu_context)
        try:
            return self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except AttributeError:
            system_prompt = messages[0]["content"]
            user_prompt = messages[1]["content"]
            return f"{system_prompt}\n\nKullanıcı: {user_prompt}\nAsistan:"

    def generate_reply(self, user_message: str, menu_context: str | None = None) -> str:
        prompt = self._build_prompt(user_message, menu_context=menu_context)
        inputs = self.tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"].to(self.model.device)
        attention_mask = inputs.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(self.model.device)

        with self._torch.inference_mode():
            output_ids = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                do_sample=False,
                max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
                repetition_penalty=DEFAULT_REPETITION_PENALTY,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        generated_ids = output_ids[0][input_ids.shape[-1] :]
        reply = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        return reply.strip()


QwenLoRAWaiter = QwenLoraWaiterBackend


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local text prompt against the Qwen LoRA waiter backend.")
    parser.add_argument("--adapter-path", required=True, help="Path to the LoRA adapter directory")
    parser.add_argument("--message", required=True, help="User message to send to the model")
    parser.add_argument(
        "--base-model-path",
        default=DEFAULT_BASE_MODEL_PATH,
        help=f"Local base model path or Hugging Face model id (default: {DEFAULT_BASE_MODEL_PATH})",
    )
    parser.add_argument(
        "--no-4bit",
        action="store_true",
        help="Disable 4-bit loading if bitsandbytes is unavailable on this machine",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        backend = QwenLoraWaiterBackend(
            adapter_path=args.adapter_path,
            base_model_path=args.base_model_path,
            load_in_4bit=not args.no_4bit,
        )
        print(backend.generate_reply(args.message))
        return 0
    except Exception as exc:
        print(f"Qwen text test failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
