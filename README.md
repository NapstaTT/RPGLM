## RPGLM v0.5 BETA

**Version 0.5** – Complete conversational AI with lorebook integration, world state, persona, macro system, and sequential LLM generation.

Built as a student research project (Team No.6).  
This release integrates **all previously prepared components** into a working pipeline, though some edge cases require hotfixes.

---

## What’s new in v0.5 (BETA)

- **Full LLM integration** – prompts, macros, world state, persona, lorebook data are all fed into the model.
- **Sequential generation** – narrator writes a scene, then each character speaks in turn (optional).
- **Retry on invalid character** – if LLM invents a non‑existent character name, the system cuts off and asks for correction.
- **Stop sequences** – `stop=["###", "\n{{user}}:", "\n**{{user}}:**"]` prevents the model from impersonating the user.
- **Improved UI** – persona modal, world state panel, settings with prompt editor, message menu (rollback).
- **Robust storage** – timeline (JSONL), lorebook (JSON), persona, prompts, all with atomic writes and backups.
- **Abort support** – user can stop generation at any time; partial results are saved.

---

## Known Issues & Limitations (BETA)

- **KoboldCPP compatibility** – the client uses the OpenAI‑compatible endpoint (`/v1/chat/completions`). Some KoboldCPP builds may have quirks with `stop` arrays.  
  **Workaround:** set `stop` as a string rather than a list in `llm_settings`.
- **Character phase** may not trigger reliably; sometimes the LLM stops early or fails to switch context.
- **Retry logic** on invalid characters is basic – may loop indefinitely if LLM consistently invents names.
- **Rollback** only deletes the last message; does not handle editing or restoring arbitrary states.
- **No streaming** of character responses – the user sees a loading spinner until all messages are generated.
- **Memory usage** – the entire timeline is loaded; large histories may impact performance.
- **No automatic keyword‑based activation** of lorebook entries (planned for v0.6).

---

## Requirements

- Python 3.10+
- A local LLM server with OpenAI‑compatible API (KoboldCPP recommended).

---

## Installation & Configuration

Same as before.

| Variable         | Default                          | Description                          |
|------------------|----------------------------------|--------------------------------------|
| `LLM_BASE_URL`   | `http://localhost:5001`          | Base URL of your LLM server (without `/v1`) |
| `WORLD_ID`       | `default`                        | Subdirectory inside `data/worlds/`   |

```bash
export LLM_BASE_URL="http://127.0.0.1:5001"
export WORLD_ID="my_campaign"
python run.py
```

Open `http://localhost:8000`.

---

## How it works (simplified)

1. **User sends a message** – together with current world state (location, active character, time).
2. **Orchestrator** builds prompt via `ContextBuilder` using the selected prompt template (`narrator`).
3. **LLM generates narrative** – can contain `**CharacterName:**` tags.
4. **Response parser** splits the text into narrative and character blocks.  
   - If an invalid character name appears, the system retries after cutting off the response at that point.  
   - Valid character blocks are saved as separate messages.
5. **For each character block**, orchestrator optionally calls the LLM again (character phase) to generate a detailed reply, stopping at `**narrative:**`.
6. All generated messages are saved to `timeline.jsonl` with proper versions and world state.
7. The frontend reloads the history and displays the conversation.

---

## API Endpoints

All endpoints from v0.4.5 remain. New or modified:

| Method | Path                         | Description                               |
|--------|------------------------------|-------------------------------------------|
| POST   | `/api/send/stream`           | Main streaming endpoint (uses orchestrator) |
| POST   | `/api/send`                  | Non‑streaming fallback (also uses orchestrator) |
| POST   | `/api/abort`                 | Stops current generation                  |
| POST   | `/api/rollback`              | Deletes last message and restores world state |

All lorebook (`/lorebook/...`) and persona (`/api/persona`), prompts (`/api/prompts`) endpoints unchanged.

---

## Project Structure (v0.5)

```
RPGLM/
├── backend/
│   ├── main.py                     # FastAPI app with all endpoints
│   ├── context/                    # ContextBuilder – builds prompt from data
│   ├── generation/                 # GenerationOrchestrator – sequential LLM calls
│   ├── llm/                        # KoboldCppClient (OpenAI‑compatible)
│   ├── lorebook/                   # Full lorebook logic (locations, characters, entries)
│   ├── macros/                     # MacroService ({{var}}, {{#if var}})
│   ├── managers/                   # PersonaManager, PromptsManager
│   ├── parsers/                    # ResponseParser (narrator, character modes)
│   ├── prompts/                    # default_prompts.json
│   ├── storage/                    # TimelineStorage, LorebookStorage, PersonaStorage, PromptsStorage
│   └── utils/                      # world_state helpers
├── frontend/
│   ├── index.html
│   ├── css/                        # styles.css, lorebook.css
│   ├── js/                         # chat.js, lorebook.js, world_state_panel.js, persona_modal.js, settings_modal.js, prompts_modal.js, message_menu.js
│   └── assets/icons/
├── data/worlds/default/
│   ├── timeline.jsonl
│   ├── timeline.tmp.jsonl
│   ├── lorebook.json
│   ├── persona.json
│   ├── prompts.json
│   ├── backups/                    # timeline backups
│   ├── lorebook_backups/           # lorebook backups (max 5)
│   └── persona_backups/            # persona backups (max 2)
├── run.py
└── README.md
```

---

## Hotfix notes (v0.5.1 planned)

- **Fix KoboldCPP `stop` parameter** – ensure `stop` is passed as a single string in settings to avoid `TypeError`.
- **Improve retry loop** – limit retries and skip invalid character blocks if they persist.
- **Add fallback** for when character phase fails – fall back to narrative-only response.
- **Optimise memory** – implement pagination or rolling window for history.

---

## Next steps (v0.6)

- **Permutations** – rewrite messages in different styles.
- **True streaming** of character responses (token‑by‑token).
- **RAG** for large entries.
- **Multi‑world switching**.

---

**Disclaimer:** This is a **BETA** release. While the core logic is functional, llm request logic still under construction and debugging. RPGLM still requires many hotfixes