# GarsonBot CLI Demo Script

## Purpose
This document provides a guided demonstration script for the text-based GarsonBot Minimum Viable Product (MVP). The goal is to show stakeholders that the core dialogue management, menu parsing, and order state tracking work locally without relying on heavy external systems or dependencies.

## How to Run the CLI
1. Open a terminal in the project root directory.
2. Ensure the virtual environment is activated and dependencies are installed.
3. Run the application:
   ```bash
   python -m robot_waiter_ai.app.main
   ```

## Windows Encoding Note
If Turkish characters render incorrectly in Windows PowerShell, switch the terminal to UTF-8 before starting the demo:

```powershell
chcp 65001
```

## Example Scenarios

### Scenario 1: Greeting & Recommendation
**User:** Merhaba
**GarsonBot:** Merhaba, hoş geldiniz. Size nasıl yardımcı olabilirim?
**User:** Ne önerirsiniz?
**GarsonBot:** Öneri olarak şunları sunabilirim: Mercimek Çorbası.

### Scenario 2: Adding Items & Order Summary
**User:** Menüde neler var?
**GarsonBot:** Kategoriler: Ana Yemek, Tatlı, Çorba, İçecek
**User:** 2 Ayran istiyorum
**GarsonBot:** Ekledim: 2 x Ayran. Başka bir isteğiniz var mı?
**User:** Bir mercimek çorbası ekle
**GarsonBot:** Ekledim: 1 x Mercimek Çorbası. Başka bir isteğiniz var mı?
**User:** Siparişi özetle
**GarsonBot:**
2 x Ayran = 90.00 TL
1 x Mercimek Çorbası = 85.00 TL
Toplam: 175.00 TL
Onaylamak ister misiniz?

### Scenario 3: Removing Items & Clearing Order
**User:** Ayranı çıkar
**GarsonBot:** Çıkardım: Ayran. Başka bir isteğiniz var mı?
**User:** Siparişi temizle
**GarsonBot:** Siparişiniz temizlendi. Başka bir isteğiniz var mı?

### Scenario 4: Allergy & Caution Response
**User:** Süt ürünlerine alerjim var
**GarsonBot:** Alerji konusunda dikkatli olalım. Menü alerjenlerini kontrol edip mutfakla teyit edebilirim.

## Known Limitations
- The bot relies on keyword and rule-based matching, not natural language processing (NLP). Complex sentences or typos may confuse it.
- Intent extraction priority can misclassify queries if multiple intent keywords are present in the same sentence.
- Multi-item orders in a single sentence (for example, `1 ayran ve 1 çorba istiyorum`) are currently not fully supported by the simplistic regex extractor.

## What this MVP proves
- The system can load and interpret structured restaurant and menu data locally from YAML files.
- The dialogue manager can classify intents and route them correctly.
- The state management reliably tracks order contents and quantities across a session.
- The foundational software architecture is solid and decoupled, allowing for easier integration with speech and AI modules later.

## What it does not prove yet
- Natural language robustness (handling typos, slang, complex conversational flow).
- Voice interaction (Speech-to-Text / Text-to-Speech).
- Hardware deployment and real-time inference on edge devices like the Jetson Orin NX.
