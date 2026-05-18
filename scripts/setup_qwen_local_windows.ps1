$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-AdapterRoot {
    param([string]$AdapterPath)

    $directConfig = Join-Path $AdapterPath "adapter_config.json"
    if (Test-Path $directConfig) {
        return $AdapterPath
    }

    $nestedDirs = Get-ChildItem -Path $AdapterPath -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path (Join-Path $_.FullName "adapter_config.json") }

    if ($nestedDirs.Count -eq 1) {
        return $nestedDirs[0].FullName
    }

    return $AdapterPath
}

$projectRoot = Resolve-Path "."
if (-not (Test-Path (Join-Path $projectRoot "requirements.txt")) -or -not (Test-Path (Join-Path $projectRoot "robot_waiter_ai"))) {
    Write-Error "Run this script from the project root. Example: cd C:\Users\Emre\Desktop\Garson-bot"
}

$venvPython = Join-Path $projectRoot ".venv-llm\Scripts\python.exe"
$baseModelDir = Join-Path $projectRoot "robot_waiter_ai\models\Qwen2.5-3B-Instruct"
$adapterDir = Join-Path $projectRoot "robot_waiter_ai\models\qwen25_3b_waiter_v1_1_lora"

Write-Step "Checking Python 3.10"
try {
    & py -3.10 --version | Out-Host
} catch {
    Write-Error "Python 3.10 was not found via 'py -3.10'. Install Python 3.10 first, then rerun this script."
}

if (-not (Test-Path $venvPython)) {
    Write-Step "Creating .venv-llm with Python 3.10"
    & py -3.10 -m venv .venv-llm
} else {
    Write-Step ".venv-llm already exists"
}

Write-Step "Upgrading pip, setuptools, and wheel"
& $venvPython -m pip install --upgrade pip setuptools wheel

Write-Step "Installing project requirements"
& $venvPython -m pip install -r requirements.txt

Write-Step "Installing LLM requirements"
& $venvPython -m pip install -r requirements-llm.txt

Write-Step "Ensuring huggingface_hub is installed"
& $venvPython -m pip install huggingface_hub

Write-Step "Ensuring model folders exist"
New-Item -ItemType Directory -Force -Path $baseModelDir | Out-Null
New-Item -ItemType Directory -Force -Path $adapterDir | Out-Null

$adapterRoot = Get-AdapterRoot -AdapterPath $adapterDir
$adapterModelFile = Join-Path $adapterRoot "adapter_model.safetensors"
$adapterConfigFile = Join-Path $adapterRoot "adapter_config.json"

Write-Step "Checking LoRA adapter files"
if (-not (Test-Path $adapterModelFile) -or -not (Test-Path $adapterConfigFile)) {
    Write-Host "LoRA adapter files are missing." -ForegroundColor Red
    Write-Host "Unzip the Colab LoRA adapter into:" -ForegroundColor Yellow
    Write-Host "  robot_waiter_ai\models\qwen25_3b_waiter_v1_1_lora" -ForegroundColor Yellow
    Write-Host "Expected files:" -ForegroundColor Yellow
    Write-Host "  adapter_model.safetensors" -ForegroundColor Yellow
    Write-Host "  adapter_config.json" -ForegroundColor Yellow
    exit 1
}

$baseConfig = Join-Path $baseModelDir "config.json"
$baseSafetensors = Get-ChildItem -Path $baseModelDir -Filter "*.safetensors" -File -ErrorAction SilentlyContinue
$baseIndex = Join-Path $baseModelDir "model.safetensors.index.json"

if ((Test-Path $baseConfig) -and (($baseSafetensors.Count -gt 0) -or (Test-Path $baseIndex))) {
    Write-Step "Base model already exists locally"
} else {
    Write-Step "Downloading Qwen/Qwen2.5-3B-Instruct into robot_waiter_ai\models\Qwen2.5-3B-Instruct"
    & $venvPython -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Qwen/Qwen2.5-3B-Instruct', local_dir=r'robot_waiter_ai\models\Qwen2.5-3B-Instruct', local_dir_use_symlinks=False)"
}

Write-Step "Done"
Write-Host "Next commands:" -ForegroundColor Green
Write-Host "  .\scripts\check_qwen_model_files.ps1"
Write-Host "  .\.venv-llm\Scripts\python.exe -m robot_waiter_ai.inference.qwen_lora_waiter --base-model-path robot_waiter_ai\models\Qwen2.5-3B-Instruct --adapter-path robot_waiter_ai\models\qwen25_3b_waiter_v1_1_lora --message `"2 ayran istiyorum`" --no-4bit"
Write-Host "  .\.venv-llm\Scripts\python.exe -m robot_waiter_ai.demo.voice_web_demo --port 8001 --backend qwen --qwen-base-model-path robot_waiter_ai\models\Qwen2.5-3B-Instruct --qwen-adapter-path robot_waiter_ai\models\qwen25_3b_waiter_v1_1_lora --no-4bit"
Write-Host ""
Write-Host "This script only downloads local model files. It does not train, upload, or commit models."
