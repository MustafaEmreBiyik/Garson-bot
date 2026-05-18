# Boss Demo Script

## Recommended Commands

Deterministic benchmark:

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.evals.eval_runner
```

Interactive CLI demo:

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.app.main
```

Single-message grounded inspection:

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.inference.grounded_demo --message "Ayran sipariş etmek istiyorum."
```

## Suggested Demo Order

### 1. Order a supported menu item
User:
`Ayran sipariş etmek istiyorum.`

Assistant:
`Ekledim: 1 x Ayran. Başka bir isteğiniz var mı?`

What this demonstrates:
- supported menu item recognition
- deterministic order-state update
- grounded quantity/item response

### 2. Ask price
User:
`Ayran ne kadar?`

Assistant:
`Ayran: Tuzlu yoğurt içeceği. Fiyat: 45.00 TL. Alerjenler: dairy. Lütfen mutfakla teyit ediniz.`

What this demonstrates:
- price answer is grounded in menu data
- response includes safety-caution style
- deterministic layer remains the source of truth for price

### 3. Ask ingredients
User:
`Domates Çorbası içinde ne var?`

Assistant:
`Domates Çorbası: Domates bazlı, krema ile servis edilir. Fiyat: 80.00 TL. Alerjenler: dairy, gluten. Lütfen mutfakla teyit ediniz.`

What this demonstrates:
- ingredient-oriented menu grounding
- structured menu facts are surfaced without model generation

### 4. Allergy / caution question
User:
`Süt ürünlerine alerjim var`

Assistant:
`Alerji konusunda dikkatli olalım. Menü alerjenlerini kontrol edip mutfakla teyit edebilirim.`

What this demonstrates:
- the system stays cautious
- it does not make unsafe allergy guarantees

### 5. Unsupported item rejection
User:
`Pizza var mı?`

Assistant:
`Bu ürün menümüzde bulunmuyor. İsterseniz mevcut kategorilerden öneri sunabilirim.`

What this demonstrates:
- unsupported items are rejected instead of hallucinated
- the response stays inside restaurant scope

### 6. Off-topic rejection
User:
`Bana hava durumunu söyler misiniz?`

Assistant:
`Bu konuda yardımcı olamıyorum. Menü veya siparişle ilgili sorabilir misiniz?`

What this demonstrates:
- off-topic requests are politely refused
- the system redirects back to restaurant scope

### 7. Confirm an order in a real deterministic session
Run this exact stateful sequence:

User:
`2 Ayran istiyorum`

Assistant:
`Ekledim: 2 x Ayran. Başka bir isteğiniz var mı?`

User:
`Bir Etli Güveç ekle`

Assistant:
`Ekledim: 1 x Etli Güveç. Başka bir isteğiniz var mı?`

User:
`Siparişimi onaylıyorum`

Assistant:
```text
Siparişinizi onaylıyorum.
2 x Ayran = 90.00 TL
1 x Etli Güveç = 260.00 TL
Toplam: 350.00 TL
Not: Bu yalnızca MVP/demo onayıdır; gerçek restoran gönderimi yapılmaz.
```

What this demonstrates:
- multi-turn order state persistence
- correct grounded totals
- explicit MVP/demo limitation

## Supervisor Talking Points
- The deterministic baseline is currently the reliable assistant.
- The project has already tested model-oriented directions, but the raw fine-tuned models underperformed.
- Dataset experimentation is paused intentionally to protect scope and quality.
- Any future model usage should be constrained by deterministic grounding, not replace it.
