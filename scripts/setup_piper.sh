#!/usr/bin/env bash
# scripts/setup_piper.sh — W-BOT Piper TTS runtime kurulumu (tekrar-üretilebilir).
#
# NEDEN: pip "piper-tts" 1.4.2 (GPL-3.0, OHF-voice/piper1-gpl) Türkçe
# fonemizasyonu bozuk — temiz UTF-8 girdide bile espeak fonemleri İngilizce'ye
# düşüyor (kwˈɔːtə/plˈʌs/mˈaɪnəs) ve akıcı-ama-yanlış "garble" ses üretiyor.
# Üretim bunun yerine arşivlenmiş MIT rhasspy/piper binary'sini <project>/piper/
# altında kullanır (tts.py _PIPER_BINARY_CANDIDATES onu PATH'ten önce dener).
# Bu binary + dfki-medium stok sesi gitignore'lu (repoda YOK) — her makinede
# (dev, Jetson) bu script ile kurulur.
#
# KULLANIM:  bash scripts/setup_piper.sh
#
# KURAR:
#   <project>/piper/                                     MIT rhasspy/piper (arch'e göre)
#   robot_waiter_ai/models/tr_TR-dfki-medium.onnx(.json) stok fallback ses (MIT)
# KURMAZ (özel, ayrıca sağlanmalı):
#   robot_waiter_ai/models/wbot_tr.onnx(.json)           W-BOT özel sesi (Drive/dev'den kopyala)
set -euo pipefail

PIPER_RELEASE="2023.11.14-2"   # rhasspy/piper son MIT sürümü (repo Ekim 2025'te arşivlendi)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIPER_DIR="$PROJECT_ROOT/piper"
MODELS_DIR="$PROJECT_ROOT/robot_waiter_ai/models"

dl() {  # dl <url> <dest>
  if command -v curl >/dev/null 2>&1; then curl -fL --retry 3 -o "$2" "$1"
  else wget -O "$2" "$1"; fi
}

# --- arch → release asset ---
ARCH="$(uname -m)"
case "$ARCH" in
  aarch64|arm64) ASSET="piper_linux_aarch64.tar.gz" ;;   # Jetson
  x86_64|amd64)  ASSET="piper_linux_x86_64.tar.gz" ;;
  *) echo "HATA: desteklenmeyen mimari: $ARCH (Windows için ZIP'i elle kur)" >&2; exit 1 ;;
esac

# --- 1) piper binary ---
if [ -x "$PIPER_DIR/piper" ]; then
  echo "✓ piper binary zaten kurulu: $PIPER_DIR/piper"
else
  echo "▶ piper binary indiriliyor ($ASSET, MIT rhasspy/piper $PIPER_RELEASE)..."
  TMP="$(mktemp -d)"
  dl "https://github.com/rhasspy/piper/releases/download/$PIPER_RELEASE/$ASSET" "$TMP/piper.tgz"
  tar -xzf "$TMP/piper.tgz" -C "$PROJECT_ROOT"   # tarball 'piper/' dizinine açılır
  rm -rf "$TMP"
  chmod +x "$PIPER_DIR/piper" 2>/dev/null || true
  echo "✓ piper binary kuruldu: $PIPER_DIR/piper"
fi

# --- 2) dfki-medium stok ses (MIT, kalan tek tr_TR stok Piper sesi) ---
mkdir -p "$MODELS_DIR"
DFKI_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium/tr_TR-dfki-medium.onnx"
if [ -f "$MODELS_DIR/tr_TR-dfki-medium.onnx" ]; then
  echo "✓ dfki-medium zaten kurulu"
else
  echo "▶ dfki-medium indiriliyor (~63 MB)..."
  dl "$DFKI_URL"        "$MODELS_DIR/tr_TR-dfki-medium.onnx"
  dl "$DFKI_URL.json"   "$MODELS_DIR/tr_TR-dfki-medium.onnx.json"
  echo "✓ dfki-medium kuruldu"
fi

# --- 3) doğrulama smoke-testi ---
echo ""
echo "=== doğrulama (tek Türkçe cümle) ==="
if echo "Künefede fındık ve süt var." | "$PIPER_DIR/piper" \
     --model "$MODELS_DIR/tr_TR-dfki-medium.onnx" \
     --output_file /tmp/piper_setup_test.wav --quiet 2>/tmp/piper_setup_err.txt; then
  SZ="$(stat -c%s /tmp/piper_setup_test.wav 2>/dev/null || echo '?')"
  echo "✓ /tmp/piper_setup_test.wav üretildi ($SZ byte) — doğru sürede WAV = fonemizasyon sağlıklı"
else
  echo "✗ Test sentezi başarısız. stderr:"; cat /tmp/piper_setup_err.txt >&2
  echo "  (Linux'ta lib yükleme sorunuysa: LD_LIBRARY_PATH=$PIPER_DIR deneyin)" >&2
  exit 1
fi

echo ""
echo "NOT: W-BOT özel sesi (wbot_tr.onnx) bu script'e DAHİL DEĞİL — özel/indirilemez."
echo "     robot_waiter_ai/models/wbot_tr.onnx olarak ayrıca kopyalayın (Drive/dev)."
echo "     wbot_tr yoksa üretim otomatik dfki-medium'a düşer (fallback)."
