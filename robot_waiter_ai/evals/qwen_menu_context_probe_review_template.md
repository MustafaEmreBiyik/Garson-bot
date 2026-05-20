# Qwen Menu Context Probe Review

## Test amacı

Bu çalışma production logic değildir. Deterministic sipariş motorunun yerine geçmez.
Amaç, mevcut eğitilmiş garson modeline sabit bir menü context'i verildiğinde müşteriyle
garson gibi Türkçe, kısa ve doğal biçimde konuşup konuşamadığını manuel olarak gözlemlemektir.

## Menü context'i

- Dosya: `robot_waiter_ai/evals/sample_menu_context.json`
- Restoran: `Garson Bot Bistro`
- Para birimi: `TL`
- Menü öğeleri: `İskender`, `Adana Kebap`, `Mercimek Çorbası`, `Fırın Sütlaç`, `Ayran`, `Limonata`

## Senaryolar

- `supported_order_with_total`
- `add_more_item`
- `remove_item`
- `unsupported_item`
- `price_question`
- `menu_question`
- `allergy_question`
- `off_topic_rejection`

## Manuel değerlendirme kriterleri

- Menüdeki ürünü doğru kabul ediyor mu?
- Menü dışı ürünü reddediyor mu?
- Fiyat uyduruyor mu?
- Toplam hesap doğru mu?
- Sipariş geçmişini takip ediyor mu?
- Alerjen güvenli mi?
- Garson rolünden çıkıyor mu?
- Türkçe doğal mı?

## Sonuç tablosu

| Scenario | Pass | Partial | Fail | Notlar |
|---|---|---|---|---|
| supported_order_with_total |  |  |  |  |
| add_more_item |  |  |  |  |
| remove_item |  |  |  |  |
| unsupported_item |  |  |  |  |
| price_question |  |  |  |  |
| menu_question |  |  |  |  |
| allergy_question |  |  |  |  |
| off_topic_rejection |  |  |  |  |
