# RPGLM v0.3

**Version 0.3** – Streaming, stop generation, tag-based message splitting, and contextual interrupts.

Built as a student research project (Team No.6).  
This release adds **streaming LLM responses**, **stop button with partial reply saving**, **automatic splitting of assistant replies into separate messages by `**Name:**` tags**, and **hardcoded macro replacement (`{{user}}` → `User`, `{{char}}` → `Assistant`)** – all while keeping the atomic JSONL storage and crash recovery from v0.2.

---

## What’s new in v0.3

- **Streaming (with fallback)** – LLM replies are generated token by token, displayed only when complete (or interrupted).  
  If streaming is not supported by the LLM server, the system falls back to non‑streaming mode.
- **Stop generation** – User can interrupt the reply mid‑generation. The partial text is saved to storage and displayed in chat.
- **Tag‑based message splitting** – Assistant responses containing `**Name:**` blocks are split into separate chat messages, each with its own `role = Name` (e.g., `**Alice:**` becomes a message from Alice).  
  This allows multiple characters to speak in one LLM turn.
- **Stop word trimming** – If the LLM outputs `**User:**`, everything after that is discarded (prevents the model from impersonating the user).
- **Macro placeholders** – In context, `{{user}}` is replaced with `User`, `{{char}}` with `Assistant` (hardcoded for now – will be configurable in v0.4).
- **New endpoints:**
  - `POST /api/send/stream` – streaming version with tag splitting.
  - `POST /api/abort` – tells KoboldCPP to stop current generation.
- **UI improvements:**
  - Send button turns into a white square (stop) during generation.
  - Text input remains editable; only sending is blocked.
  - Partial replies appear after stopping, then full history reloads.

---

## What is NOT in v0.3 (yet)

- Editable character/location/world definitions (v0.4).
- Mutations (v0.6).
- Configurable LLM parameters in UI.
- Persistent character names – `User` and `Assistant` are still hardcoded.
- Multi‑world switching.
- Proper error recovery for all LLM backends (only KoboldCPP is well tested).

---

## Requirements (unchanged)

- Python 3.10+
- A local LLM server with **OpenAI‑compatible streaming API** (KoboldCPP recommended).  
  For KoboldCPP, start with `--api --openai`.

---

## Installation & Configuration

Same as v0.2, but note the new environment variable:

| Variable         | Default                          | Description                          |
|------------------|----------------------------------|--------------------------------------|
| `LLM_BASE_URL`   | `http://localhost:5001`          | Base URL of your LLM server (without `/v1`) |
| `WORLD_ID`       | `default`                        | Subdirectory inside `data/worlds/`   |

Example:
```bash
export LLM_BASE_URL="http://127.0.0.1:5001"
export WORLD_ID="my_campaign"
```

If you were using `LLM_ENDPOINT` before, replace it with `LLM_BASE_URL`.

---

## Running

```bash
python run.py
```

Open `http://localhost:8000`.

---

## Project structure (v0.3)

```
RPGLM/
├── backend/
│   ├── main.py           # Two endpoints: /api/send (legacy) and /api/send/stream (new)
│   ├── llm_client.py     # KoboldCppClient with streaming, abort, and message splitting
│   ├── storage.py        # Unchanged from v0.2
│   └── middleware.py
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   ├── js/chat.js        # Handles streaming, stop button, history reload
│   └── assets/icons/     # Added icon-stop symbol
├── run.py
└── README.md
```

---

## API endpoints (v0.3)

| Method | Path               | Description                                                          |
|--------|--------------------|----------------------------------------------------------------------|
| GET    | `/api/history`     | Returns all messages (with `role` as name for assistant messages).   |
| POST   | `/api/send`        | Legacy non‑streaming endpoint (returns full reply in one chunk).     |
| POST   | `/api/send/stream` | Streaming endpoint. Response is SSE. Splits `**Name:**` blocks.      |
| POST   | `/api/abort`       | Tells KoboldCPP to abort current generation.                         |
| GET    | `/`                | Serves the chat UI.                                                  |

---

## Known limitations & quirks (v0.3)

- **Macros are hardcoded** – `{{user}}` → `User`, `{{char}}` → `Assistant`. No UI to change them yet. Somewhere is broken.
- **Stop word trimming** – The stop word is `**User:**` (exactly). If the LLM writes `**User:**`, everything after is cut off. This may cut legitimate text if the model talks about the user.
- **Partial replies on stop** – When stopping, the server saves whatever text has been generated, even if it doesn't contain a full `**Name:**` tag. That message gets `role = "assistant"` and appears without a character name.
- **Only KoboldCPP tested** – Abort uses `/api/extra/abort`. Other backends (Oobabooga, llama.cpp) may not support graceful stop.
- **Streaming detection** – The system does not auto‑detect streaming support; it always tries `stream=True`. If your LLM server returns an error, you'll need to use the legacy `/api/send`.
- **UI state** – The stop button is white, field is not blocked; but if you send a new message while generation is still ongoing, the old generation is aborted (expected).

---

## Next steps (v0.4+)

- **Configurable character names** – Replace hardcoded `User`/`Assistant` with actual names from character definitions.
- **Character/location/world JSON storage** – CRUD for entities, attach state and avatar.
- **Macro system** – Expand `{{user}}`, `{{char}}`, `{{location}}`, `{{var:...}}` from world state.
- **Context injection** – Insert active characters, location description, and triggered notes into the LLM prompt.
- **Mutation planning** – Second low‑temperature call to modify world state.
