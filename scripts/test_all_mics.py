# -*- coding: utf-8 -*-
"""Her giriş cihazından 1.5sn kayıt alıp RMS/peak ölçer — hangi cihaz gerçekten
ses alıyor, isme değil ölçüme göre bulmak için."""
import sounddevice as sd
import numpy as np
import time

RATE = 44100
DUR = 1.5

devs = sd.query_devices()
candidates = [(i, d) for i, d in enumerate(devs) if d['max_input_channels'] > 0]

print(f"{len(candidates)} giriş cihazı bulundu. Her biri için {DUR}sn kayıt alınacak.")
print("KONUŞUN / SES YAPIN test sırasında (her cihaz denenirken birkaç saniye sürer)!\n")
time.sleep(1)

results = []
for i, d in candidates:
    name = d['name']
    sr = int(d['default_samplerate'])
    try:
        rec = sd.rec(int(DUR * sr), samplerate=sr, channels=1, dtype='int16', device=i)
        print(f"[{i}] {name[:45]:45} kaydediliyor...", end="", flush=True)
        sd.wait()
        peak = int(np.abs(rec).max())
        rms = int(np.sqrt(np.mean(rec.astype(np.float64) ** 2)))
        pct = peak / 32767 * 100
        results.append((i, name, peak, rms, pct))
        print(f" peak={peak:5d} (%{pct:4.1f})  rms={rms:5d}")
    except Exception as e:
        print(f" HATA: {e}")
        results.append((i, name, -1, -1, -1))

print("\n=== ÖZET (peak %'e göre sıralı, en yüksek = muhtemelen aktif mikrofon) ===")
for i, name, peak, rms, pct in sorted(results, key=lambda r: -r[4]):
    flag = "  <-- MUHTEMELEN BU" if pct > 5 else ""
    print(f"[{i:2d}] {name[:45]:45} peak=%{pct:5.1f}  rms={rms:5d}{flag}")
