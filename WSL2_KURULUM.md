# W-BOT — WSL2 Geliştirme Ortamı Kurulum Kılavuzu

> Bu kılavuz Ubuntu dual-boot'u kaldırıp Windows 11 + WSL2 üzerinde geliştirmeye devam etmek için hazırlanmıştır.
> Demo (mikrofon + hoparlör) testleri Jetson Orin NX üzerinde yapılır.

---

## 1. Windows Tarafı Hazırlık

### 1.1 WSL2 Kur

PowerShell'i **yönetici olarak** aç:

```powershell
wsl --install
# Zaten kuruluysa sadece Ubuntu ekle:
wsl --install -d Ubuntu-22.04
wsl --set-default-version 2
```

Kurulum sonrası bilgisayarı yeniden başlat.

### 1.2 NVIDIA CUDA (WSL2)

WSL2 CUDA için Windows tarafında NVIDIA sürücüsü yeterli — WSL2 içine ayrıca CUDA toolkit kurma, karışıklık çıkarır.

1. [nvidia.com/drivers](https://www.nvidia.com/drivers) adresinden Windows için en güncel Game Ready veya Studio Driver'ı kur
2. WSL2'de kontrol et:

```bash
nvidia-smi
# "CUDA Version: 12.x" görünüyorsa hazır
```

---

## 2. WSL2 Ubuntu Ortamı

### 2.1 Temel Paketler

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.10 python3.10-venv python3.10-dev python3-pip \
    git build-essential cmake ffmpeg portaudio19-dev libsndfile1
```

### 2.2 Projeyi Klonla

```bash
cd ~
git clone https://github.com/MustafaEmreBiyik/Garson-bot.git
cd Garson-bot
```

### 2.3 Virtual Environment Oluştur

```bash
python3.10 -m venv venv_wakeword
source venv_wakeword/bin/activate
pip install --upgrade pip
```

> Bundan sonraki tüm `pip install` komutları bu venv aktifken çalıştırılacak.

---

## 3. Python Paketleri

### 3.1 PyTorch (CUDA 12.1)

```bash
pip install torch==2.5.1+cu121 torchaudio==2.5.1+cu121 \
    --index-url https://download.pytorch.org/whl/cu121
```

Kontrol et:
```bash
python3 -c "import torch; print(torch.cuda.is_available())"
# True çıkmalı
```

### 3.2 faster-whisper

```bash
pip install faster-whisper==1.2.1
pip install ctranslate2==4.7.2
pip install onnxruntime-gpu==1.23.2
```

### 3.3 llama-cpp-python (CUDA)

```bash
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --upgrade --force-reinstall --no-cache-dir
```

> Bu komut derleme yaptığından 5-10 dakika sürebilir. CUDA_HOME ortam değişkeni gerekmez, WSL2 otomatik bulur.

Kontrol et:
```bash
python3 -c "from llama_cpp import Llama; print('llama-cpp-python OK')"
```

### 3.4 OpenWakeWord

```bash
pip install -e ./openWakeWord
```

### 3.5 Genel Gereksinimler

```bash
pip install -r requirements.txt
pip install sounddevice PyAudio
```

### 3.6 Opsiyonel — Fine-tune / Eğitim Paketleri

```bash
pip install -r requirements-llm.txt
```

---

## 4. Google Drive'dan İndirilecek Dosyalar

> Repo klonlandıktan sonra bu dosyaları Drive'dan indirip aşağıdaki dizinlere koy.

### 4.1 wbot_v3 Adapter (fine-tuned model ağırlıkları)

**Drive klasörü:** [adapter](https://drive.google.com/drive/folders/1_0IDHoP7LZHJ2RzN4392Q89y85D68iU7)

İndirilecek dosyalar ve hedef dizin:

```
~/Garson-bot/robot_waiter_ai/training/artifacts/wbot_v3_qlora/adapter/
├── adapter_model.safetensors   ← 253 MB
├── adapter_config.json
├── tokenizer.json
├── tokenizer_config.json
├── chat_template.jinja
└── README.md
```

```bash
mkdir -p ~/Garson-bot/robot_waiter_ai/training/artifacts/wbot_v3_qlora/adapter
# Dosyaları indirip bu dizine koy
```

### 4.2 GGUF Modeli (opsiyonel — sadece WSL2'de eval çalıştırmak istersen)

**Drive klasörü:** [wbot_v3](https://drive.google.com/drive/folders/1uUkr2DlBo7lnDE9rBQWF3mfzHrCgj_9D)

İndirilecek dosya: `Qwen3-4B-wbot_v3-Q4_K_M.gguf` (2.33 GB)

```bash
mkdir -p ~/models
# Dosyayı ~/models/ dizinine koy
```

> **Not:** Demo (demo_usb.py) Jetson'da çalışır, GGUF orada zaten var. WSL2'de sadece `eval_gguf.py` çalıştıracaksan gerekli.

---

## 5. Piper TTS

### 5.1 Piper Binary

Piper binary'si repo içinde `piper/` dizininde bulunuyor (Linux ARM binary değil, x86_64 binary gerekiyor).

```bash
# Piper'ın çalışıp çalışmadığını test et
./piper/piper --version
```

Eğer çalışmazsa (farklı mimari):
```bash
# x86_64 Linux binary indir
wget https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz
tar -xzf piper_linux_x86_64.tar.gz -C piper/ --strip-components=1
```

### 5.2 Piper Türkçe Ses Modeli

Ses modeli `.gitignore`'da olduğundan repoda yok, manuel indirilmesi gerekiyor.

**Hedef dizin:**
```
~/Garson-bot/robot_waiter_ai/models/
├── tr_TR-fahrettin-medium.onnx       ← 61 MB
└── tr_TR-fahrettin-medium.onnx.json  ← config
```

```bash
cd ~/Garson-bot/robot_waiter_ai/models

# Ses modelini indir
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/fahrettin/medium/tr_TR-fahrettin-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/fahrettin/medium/tr_TR-fahrettin-medium.onnx.json
```

Kontrol et:
```bash
echo "test" | ~/Garson-bot/piper/piper \
  --model ~/Garson-bot/robot_waiter_ai/models/tr_TR-fahrettin-medium.onnx \
  --output_file /tmp/test.wav
# /tmp/test.wav oluştuysa TTS çalışıyor
```

---

## 6. Günlük Kullanım İş Akışı

### WSL2'de başlat

```bash
# WSL2 terminalini aç (Windows'ta "Ubuntu" uygulaması)
cd ~/Garson-bot
source venv_wakeword/bin/activate
```

### Kod geliştir → Push → Jetson'da test et

```bash
# 1. Kod yaz (VS Code veya terminal)
# 2. Push et
git add .
git commit -m "feat: ..."
git push

# 3. Jetson'da (SSH veya fiziksel terminal)
#    git pull
#    python3 scripts/demo_usb.py
```

### Jetson'a SSH bağlantısı

```bash
ssh emk@<jetson-ip>
# Örnek: ssh emk@192.168.1.42
```

Dosya kopyalamak için:
```bash
scp scripts/demo_usb.py emk@<jetson-ip>:~/Desktop/Garson-bot/Garson-bot/scripts/
```

### Eval testleri (WSL2'de, GPU ile)

```bash
# LLM eval — Jetson'daki GGUF'u kullanmak yerine lokal GGUF gerekir
# Jetson'dan kopyala veya Colab'dan indir
python3 scripts/eval_gguf.py --model /path/to/Qwen3-4B-wbot_v3-Q4_K_M.gguf
```

---

## 7. VS Code Entegrasyonu (Önerilen)

Windows'ta VS Code kur, WSL2 eklentisi ile WSL içindeki projeyi doğrudan düzenle:

1. VS Code → Extensions → "Remote - WSL" kur
2. WSL terminalinde proje dizininde: `code .`
3. VS Code Windows'ta açılır ama dosyalar WSL içinde çalışır

---

## 8. Sık Karşılaşılan Sorunlar

| Sorun | Çözüm |
|---|---|
| `nvidia-smi` bulunamıyor | Windows NVIDIA sürücüsünü güncelle (WSL2 CUDA için ayrıca kurulum gerekmez) |
| `llama-cpp-python` CUDA kullanmıyor | `CMAKE_ARGS="-DGGML_CUDA=on"` ile yeniden kur |
| `sounddevice` mikrofon bulamıyor | Beklenen davranış — USB ses WSL2'de çalışmaz, testleri Jetson'da yap |
| `piper` binary çalışmıyor | x86_64 Linux binary'sini indir (yukarıdaki komut) |
| `git push` yetki hatası | `git config --global credential.helper store` ve bir kez şifre gir |

---

## 9. Ne Jetson'da Yapılır, Ne WSL2'de

| Görev | Ortam |
|---|---|
| Kod yazma, düzenleme | WSL2 |
| Git push/pull | WSL2 |
| eval_gguf.py (lokal GGUF ile) | WSL2 veya Jetson |
| Fine-tune eğitimi | Google Colab (A100) |
| demo_usb.py (mikrofon+hoparlör) | **Jetson** |
| Wake word testi | **Jetson** |
| Gürültülü ortam testi | **Jetson** |

---

## 10. Proje Özet Bilgileri

- **Repo:** https://github.com/MustafaEmreBiyik/Garson-bot
- **Model (GGUF):** `Qwen3-4B-wbot_v3-Q4_K_M.gguf` — Jetson'da `/home/emk/models/`
- **Piper ses:** `tr_TR-fahrettin-medium.onnx`
- **Wake word:** `hey_garson.onnx`
- **Güncel durum:** `PROJE_DURUMU.md`
