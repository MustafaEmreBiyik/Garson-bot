# -*- coding: utf-8 -*-
"""Tek bir cihazdan N saniye kayıt alıp peak/rms ölçer + WAV'a kaydeder.
test_all_mics.py ile adayı bulduktan sonra, o cihazı tek başına, sürekli
konuşarak doğrulamak için kullanılır.

Kullanım:
    python scripts/test_mic_level.py --device 14
    python scripts/test_mic_level.py --device 14 --seconds 4 --out deneme.wav
"""
import argparse
import wave

import numpy as np
import sounddevice as sd

parser = argparse.ArgumentParser()
parser.add_argument("--device", type=int, required=True)
parser.add_argument("--seconds", type=float, default=3.0)
parser.add_argument("--out", type=str, default="mic_test.wav")
args = parser.parse_args()

info = sd.query_devices(args.device)
sr = int(info["default_samplerate"])
print(f"[{args.device}] {info['name']}  ({sr} Hz)")
print(f"{args.seconds}sn kayıt başlıyor — SÜREKLİ konuşun...\n")

rec = sd.rec(int(args.seconds * sr), samplerate=sr, channels=1, dtype="int16", device=args.device)
sd.wait()

peak = int(np.abs(rec).max())
rms = int(np.sqrt(np.mean(rec.astype(np.float64) ** 2)))
pct = peak / 32767 * 100

print(f"peak = {peak:5d}  (%{pct:5.1f})")
print(f"rms  = {rms:5d}")

if pct < 15:
    print("\n⚠ Seviye düşük görünüyor (< %15). Windows Ses Ayarları → Kayıt cihazları →")
    print("  bu cihazı seç → Özellikler → Seviyeler sekmesinden Mikrofon/Boost'u")
    print("  artırmayı deneyin, ya da mikrofona daha yakın konuşun.")
elif pct > 90:
    print("\n⚠ Seviye çok yüksek, clipping riski var — mikrofonu biraz uzaklaştırın")
    print("  veya Windows'ta seviyeyi düşürün.")
else:
    print("\n✓ Seviye makul aralıkta.")

with wave.open(args.out, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sr)
    wf.writeframes(rec.tobytes())
print(f"\nKaydedildi: {args.out} (dinlemek için çift tıklayın)")
