# RPGLM v0.2

**Version 0.2** – Persistent chat with atomic message storage, crash recovery, and versioned timeline.

Built as a student research project (Team No.6).  
This release adds **durable storage**, **backup rotation**, **version‑aware message history**, and a background flush task – all while keeping the simple web UI.

---

## What’s new in v0.2

- **Persistent chat history** – messages survive server restarts and browser refreshes.
- **Append‑only JSONL storage** + atomic file writes (no corruption on crash).
- **Automatic crash recovery** – unsaved writes are flushed at next startup.
- **Version numbering** – each message gets a unique sequential `ver` field.
- **Background flush** – temporary buffer saved every 3 seconds.
- **Backup rotation** – up to 10 timestamped backups of the timeline.
- **No‑cache middleware** – forces browser to always fetch fresh assets (great for development and mobile testing).
- **Modular storage layer** – `storage.py` manages worlds, backups, and merging.
- **Run script** – `python run.py` starts the server without messing with PYTHONPATH.

The core chat experience remains the same: type a message → LLM replies.  
But now the **entire conversation is safely stored on disk** and reloaded when you revisit the page.

---

## What is NOT in v0.2 (yet)

- World state, characters, locations, inventory, mutations (planned for v0.3).
- Configurable LLM parameters in a UI (still hardcoded in `backend/main.py` except the endpoint).
- Streaming responses.
- Multi‑world switching in the frontend.
- User accounts or authentication.

---

## Requirements

- Python 3.10+
- A local LLM server with an OpenAI‑compatible API, e.g.:
  - [KoboldCPP](https://github.com/LostRuins/koboldcpp) (start with `--api --openai`)
  - [oobabooga text‑generation‑webui](https://github.com/oobabooga/text-generation-webui) (OpenAI extension)
  - [llama.cpp server](https://github.com/ggerganov/llama.cpp) (with `--host 0.0.0.0 --port 5001`)
- Modern web browser

---

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/RPGLM.git
   cd RPGLM
   ```

2. **Install Python dependencies**
   ```bash
   pip install fastapi uvicorn httpx pydantic
   ```

3. **Start your LLM server**  
   Example with KoboldCPP (adjust model path):
   ```bash
   ./koboldcpp --api --openai --port 5001 ./models/your-model.gguf
   ```

---

## Configuration

All settings are read from environment variables (no config file yet).

| Variable         | Default                                      | Description                          |
|------------------|----------------------------------------------|--------------------------------------|
| `LLM_ENDPOINT`   | `http://localhost:5001/v1/chat/completions` | OpenAI‑compatible chat completion URL |
| `WORLD_ID`       | `default`                                    | Subdirectory inside `data/worlds/`   |

**Example** (run before starting the server):
```bash
export LLM_ENDPOINT="http://127.0.0.1:1234/v1/chat/completions"
export WORLD_ID="my_campaign"
```

LLM parameters are still hardcoded in `backend/main.py`:
- `model`: `"local-model"`
- `temperature`: `0.7`
- `max_tokens`: `512`
- `stream`: `False`

---

## Running

Start the FastAPI server from the project root:

```bash
python run.py
```

Then open `http://localhost:8000` in your browser.

- The backend listens on `127.0.0.1:8000` (change in `run.py` if needed).
- History is stored in `data/worlds/<WORLD_ID>/timeline.jsonl` and `.tmp.jsonl`.
- Backups go to `data/worlds/<WORLD_ID>/backups/`.

---

## Project structure (v0.2)

```
RPGLM/
├── backend/
│   ├── main.py           # FastAPI app, LLM proxy, versioning, background flush
│   ├── storage.py        # WorldStorage, atomic JSONL operations, backup rotation
│   └── middleware.py     # NoCacheMiddleware for development
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   ├── js/chat.js        # Loads /api/history and sends messages
│   └── assets/icons/     # SVG sprite (not shown in your snippet)
├── tests/
│   └── test_storage.py   # Basic storage sanity check
├── run.py                # Entry point (sets PYTHONPATH, runs uvicorn)
└── README.md
```

---

## API endpoints

| Method | Path           | Description                                 |
|--------|----------------|---------------------------------------------|
| GET    | `/api/history` | Returns `{"messages": [...], "latest_version": N}` |
| POST   | `/api/send`    | Accepts `{"text": "..."}` → replies with `{"reply": "..."}` |
| GET    | `/`            | Serves the chat UI (`index.html`)          |

All other paths serve static files from `frontend/`.

---

## Limitations in v0.2

- **No mutations** – the `mutations` field exists in the message schema but is never used.
- **No character/world UI** – just a plain chat window.
- **LLM parameters are hardcoded** – change `temperature` etc. requires editing `main.py`.
- **No streaming** – the entire reply is fetched before display.
- **Single world at a time** – changing `WORLD_ID` requires restarting the server.

---

## Next steps

- Editable LLM parameters (temperature, top‑p, etc.) from the frontend.
- Character&world definitions and world state.
- Basic mutation system (append‑only changes).
- Multi‑world selection UI.
## v0.3. What's NEXT?
- Streaming
- Clearly devide by code where's character speech, where's narrative, where is user's speech
- Create Tags: locations, characters, ect. Make up the system, that will be transformed into search by key-words in future update
