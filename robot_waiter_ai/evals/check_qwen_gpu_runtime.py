from __future__ import annotations

import importlib
import platform
import shutil
import subprocess
import sys
from typing import Any


def _print_line(label: str, value: Any) -> None:
    print(f"{label}: {value}")


def _safe_import(module_name: str) -> tuple[bool, str]:
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"

    version = getattr(module, "__version__", "unknown")
    return True, f"ok (version={version})"


def _run_optional_command(command: list[str]) -> str:
    executable = shutil.which(command[0])
    if executable is None:
        return "not found"

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
    except Exception as exc:
        return f"failed to run ({type(exc).__name__}: {exc})"

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    body = stdout or stderr or "(no output)"
    return f"exit_code={completed.returncode}; output={body}"


def _print_torch_runtime() -> bool:
    try:
        import torch
    except Exception as exc:
        _print_line("torch import", f"failed ({type(exc).__name__}: {exc})")
        return False

    _print_line("torch version", getattr(torch, "__version__", "unknown"))
    cuda_available = bool(torch.cuda.is_available())
    _print_line("torch.cuda.is_available()", cuda_available)
    _print_line("torch.cuda.device_count()", torch.cuda.device_count())
    _print_line("CUDA version", getattr(torch.version, "cuda", None))

    if cuda_available and torch.cuda.device_count() > 0:
        try:
            _print_line("torch.cuda.get_device_name(0)", torch.cuda.get_device_name(0))
        except Exception as exc:
            _print_line("torch.cuda.get_device_name(0)", f"failed ({type(exc).__name__}: {exc})")

        try:
            free_bytes, total_bytes = torch.cuda.mem_get_info(0)
            free_gb = free_bytes / (1024**3)
            total_gb = total_bytes / (1024**3)
            _print_line("GPU memory", f"free={free_gb:.2f} GiB total={total_gb:.2f} GiB")
        except Exception:
            try:
                props = torch.cuda.get_device_properties(0)
                total_gb = props.total_memory / (1024**3)
                _print_line("GPU memory", f"total={total_gb:.2f} GiB")
            except Exception as exc:
                _print_line("GPU memory", f"unavailable ({type(exc).__name__}: {exc})")
    else:
        _print_line("torch.cuda.get_device_name(0)", "n/a")
        _print_line("GPU memory", "n/a")

    return cuda_available


def _is_probable_jetson() -> bool:
    return platform.machine().lower() in {"aarch64", "arm64"} and (
        shutil.which("nvpmodel") is not None or shutil.which("jetson_clocks") is not None
    )


def main() -> int:
    _print_line("Python version", sys.version.replace("\n", " "))
    _print_line("Platform", platform.platform())

    cuda_available = _print_torch_runtime()

    transformers_ok, transformers_status = _safe_import("transformers")
    _print_line("transformers import", transformers_status)

    peft_ok, peft_status = _safe_import("peft")
    _print_line("peft import", peft_status)

    _print_line("nvidia-smi", _run_optional_command(["nvidia-smi"]))
    _print_line("nvcc --version", _run_optional_command(["nvcc", "--version"]))

    if _is_probable_jetson():
        _print_line("nvpmodel -q", _run_optional_command(["nvpmodel", "-q"]))
        jetson_clocks_output = _run_optional_command(["jetson_clocks", "--show"])
        _print_line("jetson_clocks --show", jetson_clocks_output)
        _print_line("MAXN active", "MAXN" if "MAXN" in jetson_clocks_output.upper() else "not detected")
    else:
        _print_line("nvpmodel -q", "not a Jetson environment")
        _print_line("jetson_clocks --show", "not a Jetson environment")
        _print_line("MAXN active", "not a Jetson environment")

    return 0 if transformers_ok and peft_ok and (cuda_available or True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
