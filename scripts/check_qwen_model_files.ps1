$ErrorActionPreference = "Stop"

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
$baseModelDir = Join-Path $projectRoot "robot_waiter_ai\models\Qwen2.5-3B-Instruct"
$adapterDir = Join-Path $projectRoot "robot_waiter_ai\models\qwen25_3b_waiter_v1_1_lora"
$adapterRoot = Get-AdapterRoot -AdapterPath $adapterDir

$baseExists = Test-Path $baseModelDir
$adapterExists = Test-Path $adapterDir
$adapterModelExists = Test-Path (Join-Path $adapterRoot "adapter_model.safetensors")
$adapterConfigExists = Test-Path (Join-Path $adapterRoot "adapter_config.json")
$baseConfigExists = Test-Path (Join-Path $baseModelDir "config.json")
$baseSafetensors = Get-ChildItem -Path $baseModelDir -Filter "*.safetensors" -File -ErrorAction SilentlyContinue
$baseIndexExists = Test-Path (Join-Path $baseModelDir "model.safetensors.index.json")
$baseWeightsExist = ($baseSafetensors.Count -gt 0) -or $baseIndexExists

Write-Host "Base model folder exists: $baseExists"
Write-Host "LoRA adapter folder exists: $adapterExists"
Write-Host "adapter_model.safetensors exists: $adapterModelExists"
Write-Host "adapter_config.json exists: $adapterConfigExists"
Write-Host "Base model config.json exists: $baseConfigExists"
Write-Host "Base model safetensors files exist: $baseWeightsExist"

if (-not $adapterExists -or -not $adapterModelExists -or -not $adapterConfigExists) {
    Write-Host ""
    Write-Host "Next action: unzip or copy the LoRA adapter into robot_waiter_ai\models\qwen25_3b_waiter_v1_1_lora" -ForegroundColor Yellow
}

if (-not $baseExists -or -not $baseConfigExists -or -not $baseWeightsExist) {
    Write-Host ""
    Write-Host "Next action: run .\scripts\setup_qwen_local_windows.ps1 to download Qwen/Qwen2.5-3B-Instruct locally." -ForegroundColor Yellow
}

if ($adapterExists -and $adapterModelExists -and $adapterConfigExists -and $baseExists -and $baseConfigExists -and $baseWeightsExist) {
    Write-Host ""
    Write-Host "Qwen local model files look ready." -ForegroundColor Green
}
