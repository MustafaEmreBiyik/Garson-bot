# Codex Review

Tarih: 1 Haziran 2026

## Yapilan Degisiklikler

1. `scripts/demo_usb.py`
   - Ubuntu host cihazda demo stabilitesi icin `WHISPER_MODEL` degeri `medium` yerine `small` yapildi.
   - Not: `medium` karari tamamen terk edilmedi; Jetson Orin NX 16GB entegrasyonunda tekrar acilmak uzere bekletiliyor.

2. `robot_waiter_ai/inference/qwen3_backend.py`
   - `stream_reply()` icindeki `temperature` degeri `0.7` yerine `0.55` yapildi.
   - Boylece demo akisi, `generate_reply()` ve belgelerdeki v4.6 decoding ayarlariyla hizalandi.

## Gozlemler

- Ubuntu host cihazda gorulen `STT hatasi: CUDA failed with error out of memory` hatasinin ana nedeni ayni anda `Qwen3-4B transformers 4-bit` ve `Whisper medium CUDA float16` calistirilmasi.
- Host cihaz ciktisinda gorulen `5.64 GB` toplam VRAM, bu kombinasyon icin dar kaliyor. `Whisper small` bu nedenle host demo icin daha guvenli secim.
- Jetson Orin NX 16GB tarafinda ayni risk daha dusuk; hedef backend `llama_cpp_backend.py + GGUF Q4_K_M` oldugu icin LLM bellek profili daha hafif. Bu yuzden `Whisper medium` Jetson asamasinda tekrar denenebilir.
- Baglam penceresi genisletme isi PC/Qwen transformers tarafinda yapilmis durumda: `_MAX_HIST_CHARS = 12000`.
- Jetson/llama.cpp tarafinda `_MAX_HIST_CHARS = 1400` kalmasi bilincli gorunuyor; `n_ctx=1536` nedeniyle sistem promptu ve cevap tokenlari disinda daha dar konusma gecmisi butcesi var.
- Cevap cesitliligi isi buyuk olcude tamamlanmis durumda:
  - Greedy decoding yerine sampling kullaniliyor.
  - `temperature=0.55`, `top_p=0.9`, `repetition_penalty/repeat_penalty=1.15` ayarlari hedeflenmis.
  - Prompt icindeki birebir kaliplar daha yapisal ve varyasyona izin veren kurallara cevrilmis.
- Kucuk tutarsizlik giderildi: transformers streaming yolu daha once `temperature=0.7` kullaniyordu; artik `0.55`.

## Mevcut Oncelik

Ubuntu host cihazda oncelik, demo akisini OOM olmadan calistirmak:

1. `Whisper small` ile wake word -> VAD kayit -> STT -> LLM -> TTS zincirini dogrula.
2. Cevap cesitliligi ve baglam davranisini gercek demo turlarinda gozlemle.
3. `Whisper medium` testini Jetson Orin NX entegrasyonuna ertele.
