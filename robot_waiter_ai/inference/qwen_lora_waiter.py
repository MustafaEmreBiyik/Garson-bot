from __future__ import annotations

import argparse
import platform
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_BASE_MODEL_PATH = "robot_waiter_ai/models/Qwen2.5-3B-Instruct"
DEFAULT_BASE_MODEL_NAME = "Qwen/Qwen2.5-3B-Instruct"
DEFAULT_MAX_NEW_TOKENS = 120
DEFAULT_REPETITION_PENALTY = 1.05
DEFAULT_DEVICE = "auto"
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
        device: str = DEFAULT_DEVICE,
    ) -> None:
        self.backend_name = "qwen_lora_waiter"
        self.base_model_path = base_model_path
        self.load_in_4bit = load_in_4bit
        self.requested_device = self._normalize_device(device)
        self.adapter_path = self._resolve_adapter_path(Path(adapter_path))
        self.base_model_source = self._resolve_base_model_source(base_model_path)
        self.tokenizer = None
        self.model = None
        self._torch = None
        self.device_used = "uninitialized"
        self.runtime_torch_dtype = "unknown"
        self.torch_cuda_available = False
        self.load_in_4bit_effective = False
        self.load_in_4bit_disabled_reason: str | None = None
        self._load_model()

    @staticmethod
    def _normalize_device(device: str | None) -> str:
        normalized = (device or DEFAULT_DEVICE).strip().lower()
        if normalized not in {"auto", "cuda", "cpu"}:
            raise ValueError("Device must be one of: auto, cuda, cpu.")
        return normalized

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

    @staticmethod
    def _default_4bit_disable_reason(use_cuda: bool) -> str | None:
        if use_cuda and platform.system().lower() == "windows":
            return (
                "4-bit Qwen loading is disabled by default on Windows because this runtime path "
                "can degrade reply quality even when bitsandbytes loads successfully."
            )
        return None

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
            "low_cpu_mem_usage": True,
        }

        self._torch = torch
        self.torch_cuda_available = bool(torch.cuda.is_available())
        use_cuda = self.torch_cuda_available and self.requested_device != "cpu"
        if self.requested_device == "cuda" and not self.torch_cuda_available:
            raise RuntimeError(
                "CUDA device was requested but torch.cuda.is_available() is False on this machine."
            )

        self.load_in_4bit_disabled_reason = None
        if self.load_in_4bit:
            self.load_in_4bit_disabled_reason = self._default_4bit_disable_reason(use_cuda)

        self.load_in_4bit_effective = self.load_in_4bit and use_cuda and not self.load_in_4bit_disabled_reason

        if self.load_in_4bit_effective:
            try:
                import bitsandbytes  # noqa: F401
            except Exception as exc:
                raise RuntimeError(
                    "4-bit Qwen loading requested but bitsandbytes is unavailable. "
                    "This is common on Windows. Reinstall optional dependencies or rerun with --no-4bit."
                ) from exc

            quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            model_kwargs["quantization_config"] = quantization_config
            model_kwargs["device_map"] = "auto"
            model_kwargs["torch_dtype"] = self._preferred_cuda_dtype(torch)
        elif use_cuda:
            model_kwargs["torch_dtype"] = self._preferred_cuda_dtype(torch)
        else:
            model_kwargs["torch_dtype"] = torch.float32

        self.runtime_torch_dtype = str(model_kwargs["torch_dtype"]).replace("torch.", "")

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

        if use_cuda and not self.load_in_4bit_effective:
            base_model = base_model.to("cuda")

        try:
            self.model = PeftModel.from_pretrained(base_model, str(self.adapter_path))
        except Exception as exc:
            raise RuntimeError(
                "LoRA adapter loading failed. Check that the adapter folder contains adapter_config.json and "
                "adapter_model.safetensors and that it matches Qwen2.5-3B-Instruct."
            ) from exc
        if use_cuda and not self.load_in_4bit_effective:
            self.model = self.model.to("cuda")
        self.model.eval()
        self.device_used = self._resolve_model_device()

    @staticmethod
    def _preferred_cuda_dtype(torch_module: Any) -> Any:
        cuda_module = getattr(torch_module, "cuda", None)
        if cuda_module is not None:
            try:
                if hasattr(cuda_module, "is_bf16_supported") and cuda_module.is_bf16_supported():
                    return torch_module.bfloat16
            except Exception:
                pass
        return torch_module.float16

    def _resolve_model_device(self) -> str:
        device_map = getattr(self.model, "hf_device_map", None)
        if isinstance(device_map, dict):
            for mapped_device in device_map.values():
                if isinstance(mapped_device, int):
                    return f"cuda:{mapped_device}"
                if isinstance(mapped_device, str) and mapped_device != "disk":
                    return mapped_device

        model_device = getattr(self.model, "device", None)
        if model_device is not None:
            return str(model_device)

        try:
            return str(next(self.model.parameters()).device)
        except (AttributeError, StopIteration):
            return "cpu"

    def runtime_metadata(self) -> dict[str, Any]:
        return {
            "backend_name": self.backend_name,
            "device_used": self.device_used,
            "torch_cuda_available": self.torch_cuda_available,
            "model_path": self.base_model_source,
            "adapter_path": str(self.adapter_path),
            "torch_dtype": self.runtime_torch_dtype,
            "load_in_4bit": self.load_in_4bit_effective,
            "load_in_4bit_disabled_reason": self.load_in_4bit_disabled_reason,
        }

    @staticmethod
    def _normalize_history_messages(
        conversation_history: Sequence[Mapping[str, str]] | None,
    ) -> list[dict[str, str]]:
        normalized_history: list[dict[str, str]] = []
        for message in conversation_history or ():
            role = str(message.get("role", "")).strip().lower()
            content = str(message.get("content", "")).strip()
            if role not in {"user", "assistant"}:
                raise ValueError("Conversation history roles must be 'user' or 'assistant'.")
            if not content:
                raise ValueError("Conversation history content must not be empty.")
            normalized_history.append({"role": role, "content": content})
        return normalized_history

    def _build_messages(
        self,
        user_message: str,
        menu_context: str | None = None,
        conversation_history: Sequence[Mapping[str, str]] | None = None,
        system_prompt_override: str | None = None,
    ) -> list[dict[str, str]]:
        cleaned = user_message.strip()
        if not cleaned:
            raise ValueError("User message must not be empty.")

        system_prompt = (system_prompt_override or "").strip() or SYSTEM_PROMPT
        if menu_context and not system_prompt_override:
            system_prompt = f"{system_prompt}\n{CONTEXT_GUARDRAIL}\n\nBağlam:\n{menu_context.strip()}"

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self._normalize_history_messages(conversation_history))
        messages.append({"role": "user", "content": cleaned})
        return messages

    def _build_prompt(
        self,
        user_message: str,
        menu_context: str | None = None,
        conversation_history: Sequence[Mapping[str, str]] | None = None,
        system_prompt_override: str | None = None,
    ) -> str:
        messages = self._build_messages(
            user_message,
            menu_context=menu_context,
            conversation_history=conversation_history,
            system_prompt_override=system_prompt_override,
        )
        try:
            return self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except AttributeError:
            prompt_lines = [messages[0]["content"], ""]
            for message in messages[1:]:
                speaker = "Kullanıcı" if message["role"] == "user" else "Asistan"
                prompt_lines.append(f"{speaker}: {message['content']}")
            prompt_lines.append("Asistan:")
            return "\n".join(prompt_lines)

    def generate_reply(
        self,
        user_message: str,
        menu_context: str | None = None,
        conversation_history: Sequence[Mapping[str, str]] | None = None,
        system_prompt_override: str | None = None,
    ) -> str:
        prompt = self._build_prompt(
            user_message,
            menu_context=menu_context,
            conversation_history=conversation_history,
            system_prompt_override=system_prompt_override,
        )
        inputs = self.tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"].to(self.device_used)
        attention_mask = inputs.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(self.device_used)

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
    parser.add_argument(
        "--device",
        default=DEFAULT_DEVICE,
        choices=("auto", "cuda", "cpu"),
        help="Runtime device preference (default: auto)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        backend = QwenLoraWaiterBackend(
            adapter_path=args.adapter_path,
            base_model_path=args.base_model_path,
            load_in_4bit=not args.no_4bit,
            device=args.device,
        )
        print(backend.generate_reply(args.message))
        return 0
    except Exception as exc:
        print(f"Qwen text test failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
