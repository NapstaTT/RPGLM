# RPGLM v0.1

**Version 0.1** – Minimal chat proxy between a web interface and a local LLM.

This is the very first working iteration. It does **exactly one thing**:  
forwards each user message to an LLM endpoint and displays the reply.

---

## What is actually implemented

- A clean chat UI (HTML/CSS/JS).
- A FastAPI backend that accepts `POST /api/send` with `{"text": "..."}`.
- The backend forwards the request to an OpenAI‑compatible LLM endpoint.
- The LLM response is returned as `{"reply": "..."}` and shown in the chat.
- No message persistence – history lives only in the browser's memory. Reload the page – chat disappears.
- No settings file – all LLM parameters are hardcoded in the backend.
- The only configurable thing is the LLM endpoint (via environment variable).

---

## What is NOT in v0.1

- Saving chat history.
- Configurable temperature, Top-P, Top-A, etc. (hardcoded: `temperature=0.7`, `max_tokens=512`).
- Atomic writes, versioning, backups.
- Characters, locations, world state.
- Streaming, rich formatting, undo, mutations.
- Any kind of settings UI or config file.

---

## Requirements

- Python 3.10+
- A local LLM server with an OpenAI‑compatible API (e.g., KoboldCPP with `--openai`, oobabooga, llama.cpp server).
- Modern web browser.

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/RPGLM.git
   cd RPGLM
   ```

2. Install Python dependencies:
   ```bash
   pip install fastapi uvicorn httpx pydantic
   ```

3. Start your LLM server (example with KoboldCPP):
   ```bash
   ./koboldcpp --api --openai your-model.gguf
   ```
   Default endpoint: `http://localhost:5001/v1/chat/completions`

---

## Running

1. Start the backend:
   ```bash
   uvicorn backend.main:app --reload
   ```

2. Open `http://localhost:8000` in your browser.

3. Type a message and press Enter or click the send button.  
   Wait for the LLM to generate a reply (no timeout, may take a while).

---

## Configuration (the only one)

You can change the LLM endpoint by setting an environment variable **before** starting the backend:

```bash
export LLM_ENDPOINT="http://127.0.0.1:1234/v1/chat/completions"
python backend/main.py
```

Default: `http://localhost:5001/v1/chat/completions`

All other LLM parameters are hardcoded in `backend/main.py`:
- `model`: `"local-model"`
- `temperature`: `0.7`
- `max_tokens`: `512`
- `stream`: `False`

---

## Project structure (real)

```
RPGLM/
├── backend/
│   └── main.py          # FastAPI server, hardcoded LLM proxy
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   └── js/chat.js
└── README.md
```

---

## Limitations (honest)

- **No persistence** – refresh the page and all messages are gone.
- **No settings** – want a different temperature? Edit the code and restart.
- **No error recovery** – if the LLM returns malformed JSON, you'll see an error message.
- **No streaming** – the entire reply is fetched before display.
- **Single conversation** – just you and the LLM, no characters or world or... past messages.

---

## Next steps (v0.2)

- Save chat history to `timeline.jsonl` with atomic writes
- Read LLM parameters from `config/config.json`.
- Basic backup and versioning.

---

## Contributing

Team No.6 student project. Code style:
- Python: PEP 8 + Google docstrings (English).
- JS: ES6, JSDoc, `const`/`let`, semicolons.
- CSS: 2‑space indentation.
