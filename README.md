# RPGLM v0.3

**Version 0.3** – "Rich" text formatting, macro substitution, and "character‑aware" chat(at least something).

Building on the persistent storage of v0.2, this release adds **inline macros**, **system‑enforced message styling** (character names, actions, dialogue, thoughts, code blocks), and a **lexical parser** that transforms raw LLM output into a beautifully styled chat view.

---

## What’s new in v0.3

- **Macro compilation** – `{{user}}` and `{{char}}` are replaced with actual names (`Artem` / `Mia`) both in user input and in the system prompt.
- **Structured formatting rules** – The LLM receives a system instruction that forces it to use:
  - `**Name:**` for character speech headers
  - `*narrative*` for actions / descriptions
  - `"dialogue"` for spoken words
  - `` `thoughts` `` for internal monologue
  - ` ```code``` ` for stats, technical blocks
- **Lexical parser (frontend)** – `parseDialogue()` safely converts those patterns into styled HTML without breaking nested structures.
- **Dedicated CSS styles** – `.char-name`, `.narrative`, `.speech`, `.thoughts`, `.code-block` – all defined in `textstyles.css`.
- **Sender‑specific left borders** – User messages get a teal border, World messages a grey border.
- **Optimistic rendering** – Your own message appears immediately with macro substitution applied client‑side.
- **Backward compatibility** – All v0.2 storage (atomic JSONL, versioning, backups, crash recovery) remains intact.

---

## What is NOT in v0.3 (yet)

- **No editable character names** – `User` and `Assistant` are still hardcoded in `backend/main.py`.
- **No UI for formatting rules** – The prompt is hardcoded.
- **No mutations / world state** – The `mutations` field exists but is unused.
- **No streaming** – Same as before.
- **No multi‑world UI** – Only one world (`default`) is active.

---

## Requirements

- Python 3.10+
- A local LLM server with an OpenAI‑compatible API (KoboldCPP, oobabooga, llama.cpp server)
- Modern web browser (ES6 support)

---

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/RPGLM.git
   cd RPGLM
   ```

2. **Install dependencies**
   ```bash
   pip install fastapi uvicorn httpx pydantic
   ```

3. **Start your LLM server** (example with KoboldCPP)
   ```bash
   ./koboldcpp --api --openai --port 5001 ./models/your-model.gguf
   ```

---

## Configuration

Still via environment variables (no config file yet).

| Variable         | Default                                      | Description                          |
|------------------|----------------------------------------------|--------------------------------------|
| `LLM_ENDPOINT`   | `http://localhost:5001/v1/chat/completions` | OpenAI‑compatible chat completion URL |
| `WORLD_ID`       | `default`                                    | Subdirectory inside `data/worlds/`   |

LLM parameters (temperature, max_tokens) are still hardcoded in `backend/main.py`.  
**Character names** are also hardcoded in `send_message()`:
```python
USER_NAME = "User"
CHAR_NAME = "Assistant"
```

You can change them directly in the source – a future version will move them to config or UI.

---

## Running

```bash
python run.py
```

Then open `http://localhost:8000` in your browser.

- All chat history is stored in `data/worlds/<WORLD_ID>/timeline.jsonl` and backed up automatically.
- Formatting instructions are sent with every request – the LLM “learns” the style.

---

## How the formatting works

1. **User types** `"Hello, {{char}}!"` → macro compiles to `"Hello, Assistant!"` (client‑side and server‑side).
2. **System prompt** (hardcoded) tells the LLM to output:
   ```
   **Mia:** *She looks up from her book* "Oh, hello Artem!" `Why is he here so late?`
   ```
3. **Frontend parser** (`parseDialogue`) converts that into:
   - `<span class="char-name">Assistant:</span>`
   - `<span class="narrative">*She looks up from her book*</span>`
   - `<span class="speech">"Oh, hello User!"</span>`
   - `<span class="thoughts">`Why is he here so late?`</span>`

No HTML injection – all user/LLM text is escaped before parsing.

---

## Project structure (v0.3)

```
RPGLM/
├── backend/
│   ├── main.py           # FastAPI app, macro compilation, system prompt, LLM proxy
│   ├── storage.py        # Atomic JSONL, versioning, backups, crash recovery
│   └── middleware.py     # NoCacheMiddleware
├── frontend/
│   ├── index.html
│   ├── css/
│   │   ├── styles.css    # Layout (header, footer, chat window, buttons)
│   │   └── textstyles.css# Lexical highlighting (names, narrative, speech, etc.)
│   ├── js/
│   │   └── chat.js       # loadHistory, sendMessage, parseDialogue, optimistic render
│   └── assets/icons/     # SVG sprite (expected, not shown in your snippet)
├── tests/
│   └── test_storage.py
├── run.py                # Entry point
└── README.md
```

---

## API endpoints (unchanged from v0.2)

| Method | Path           | Description                                 |
|--------|----------------|---------------------------------------------|
| GET    | `/api/history` | Returns sorted messages with version numbers |
| POST   | `/api/send`    | Accepts `{"text": "..."}`, compiles macros, calls LLM, stores both messages |
| GET    | `/`            | Serves the chat UI (`index.html`)          |

---

## Limitations in v0.3 (honest)

- **Hardcoded character names** – change `USER_NAME` / `CHAR_NAME` in `backend/main.py` to customize.
- **System prompt is fixed** – you cannot edit formatting rules via UI.
- **No “regenerate” or “edit”** – you cannot delete or correct a message.
- **No streaming** – still waits for full LLM response.
- **No support for multiple worlds in frontend** – only the `default` world is used.
- **The `mutations` field** is a placeholder for future world‑state changes.

---

## Development & contribution

Team No.6 student project. Code style remains:

- **Python**: PEP 8, Google docstrings, type hints.
- **JavaScript**: ES6, `const`/`let`, semicolons, JSDoc comments.
- **CSS**: 2‑space indentation, BEM‑ish class naming.

To test storage manually:
```bash
python tests/test_storage.py
```

---

## Next steps (v0.4)

- Move character names and system prompt to a configuration file or UI.
- Add **world state** (characters, locations, inventory) with mutation tracking.
- **Streaming responses**.
- **Message editing / deletion**.
- **Multi‑world selection** in the frontend.
