#!/usr/bin/env bash
# Jetson Orin NX için Piper TTS kurulum scripti
# Çalıştır: bash scripts/setup_jetson_piper.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MODELS_DIR="$PROJECT_ROOT/robot_waiter_ai/models"
PIPER_DIR="$PROJECT_ROOT/piper"

echo "=== Jetson Piper TTS Kurulum ==="
echo "Proje kökü: $PROJECT_ROOT"

# ── 1. Piper binary (aarch64) ──────────────────────────────────────────────
PIPER_VERSION="2023.11.14-2"
PIPER_ARCHIVE="piper_linux_aarch64.tar.gz"
PIPER_URL="https://github.com/rhasspy/piper/releases/download/${PIPER_VERSION}/${PIPER_ARCHIVE}"

if [ -f "$PIPER_DIR/piper" ]; then
    echo "[1/2] Piper binary zaten mevcut: $PIPER_DIR/piper"
else
    echo "[1/2] Piper binary indiriliyor (aarch64)..."
    mkdir -p "$PIPER_DIR"
    curl -L "$PIPER_URL" -o "/tmp/$PIPER_ARCHIVE"
    tar -xzf "/tmp/$PIPER_ARCHIVE" -C "$PIPER_DIR" --strip-components=1
    chmod +x "$PIPER_DIR/piper"
    rm "/tmp/$PIPER_ARCHIVE"
    echo "    ✅ Piper kuruldu: $PIPER_DIR/piper"
fi

# ── 2. Türkçe model ────────────────────────────────────────────────────────
MODEL_BASE="tr_TR-fahrettin-medium"
MODEL_ONNX="$MODELS_DIR/${MODEL_BASE}.onnx"
MODEL_JSON="$MODELS_DIR/${MODEL_BASE}.onnx.json"
HF_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/refs%2Fpr%2F25/tr/tr_TR/fahrettin/medium"

mkdir -p "$MODELS_DIR"

if [ -f "$MODEL_ONNX" ] && [ -f "$MODEL_JSON" ]; then
    echo "[2/2] Türkçe model zaten mevcut: $MODEL_ONNX"
else
    echo "[2/2] Türkçe Piper modeli indiriliyor (~65 MB)..."
    curl -L "${HF_BASE}/${MODEL_BASE}.onnx"      -o "$MODEL_ONNX"
    curl -L "${HF_BASE}/${MODEL_BASE}.onnx.json" -o "$MODEL_JSON"
    echo "    ✅ Model kuruldu: $MODEL_ONNX"
fi

# ── 3. Test ────────────────────────────────────────────────────────────────
echo ""
echo "=== Hızlı test ==="
echo "Merhaba, ben Garson robotuyum." | \
    "$PIPER_DIR/piper" \
    --model "$MODEL_ONNX" \
    --output_file /tmp/piper_test.wav 2>/dev/null && \
    echo "✅ Piper çalışıyor → /tmp/piper_test.wav" || \
    echo "⚠️  Piper testi başarısız — yukarıdaki hataları incele"

echo ""
echo "=== Benchmark için ==="
echo "python scripts/benchmark_tts.py --engines piper"
