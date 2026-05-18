# Voice Web Demo

This directory contains a demo-only local browser wrapper around the current
deterministic waiter assistant.

## Purpose
- microphone input through the browser
- local speech-to-text through browser Web Speech API
- deterministic assistant response from the existing Python runtime
- browser text-to-speech output through the computer speakers

This is **not** a production speech stack.

## What It Does Not Add
- no model download
- no LLM runtime integration
- no training
- no processed dataset changes
- no FastAPI dependency

## Run

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.demo.voice_web_demo
```

Then open:

```text
http://localhost:8000
```

If port `8000` is already occupied, run:

```powershell
.venv\Scripts\python.exe -m robot_waiter_ai.demo.voice_web_demo --port 8001
```

Then open:

```text
http://localhost:8001
```

## Browser Notes
- Chrome or Edge is recommended for best Web Speech API support.
- Allow microphone permission when the browser prompts for it.
- Speech recognition is requested with language `tr-TR`.
- Speech synthesis is requested with language `tr-TR` when a Turkish voice is available.

## UI Notes
The page shows:
- `Konuş` button
- demo phrase buttons
- recognized text area
- assistant response area
- `Cevabı seslendir` fallback button
- status panel with current project status

## Backend Route
- `POST /chat`
- request body: `{"message": "..."}`
- response body: `{"message": "...", "response": "...", "intent": "...", "metadata": {...}}`

The backend reuses the existing deterministic grounded demo path. Business logic is not duplicated.
