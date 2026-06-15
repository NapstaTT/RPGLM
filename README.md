# RPGLM v0.4.5

**Version 0.4.5** – World State, Macros, Persona, and Prompt Templates.

Built as a student research project (Team No.6).  
This release adds **persistent world state**, **macro system**, **user persona management**, and **fully editable prompt templates** with conditional macros.  
The lorebook module is now integrated with chat context (but LLM prompt assembly is ready for v0.5).

---

## What’s new in v0.4.5

- **World State Panel** – right‑side panel to set current location, active character, and time string.  
  The state is saved with every user message and restored on page reload.
- **Macro Service** – supports `{{macro}}` replacement and conditional blocks `{{#if var}}...{{/if}}`.  
  Currently used in prompt templates.
- **User Persona** – separate `persona.json` file (name + description).  
  Dedicated modal (portrait icon) to edit persona; the chat displays the user’s name from persona.
- **Prompt Templates** – `prompts.json` stores three template+prompt pairs: `narrator`, `character`, `permutation`.  
  Templates support macros and conditional blocks.  
  A full UI (Settings → Edit Prompts) lets you modify them in‑browser.  
  (Still not used by the chat – will be integrated in v0.5.)
- **Codebase refactoring** – clear separation of storage (timeline, lorebook, persona, prompts), macros, managers, and LLM client.
- **Removed system `init` message** – timeline no longer contains useless system entries.

---

## What remains for v0.5

- Connect the prompt templates to real LLM generation (`ContextBuilder` + `GenerationOrchestrator`).
- Automatic character/location activation based on keywords.
- Lorebook entries insertion into prompt (depth, position, activation logic).

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

## New Features in Detail

### World State Panel
- Appears automatically on the right side of the screen.
- Dropdowns for **Location** (from lorebook) and **Active Character** (from lorebook).
- Free‑text **Time** field.
- The selected state is attached to every user message (`world_state` field in `timeline.jsonl`).
- On page load, the panel loads the last used world state from history.

### Macros
- Supported macros: `{{user_persona}}`, `{{character_description}}`, `{{location_description}}`, `{{world_map}}`, `{{history}}`, `{{scenario}}`, `{{system_prompt}}`.
- Conditional blocks: `{{#if var}}...{{/if}}` – the block is kept only if the variable exists and is truthy.
- Implemented in `backend/macros/macros_service.py`.

### Persona
- Stored in `data/worlds/<WORLD_ID>/persona.json`.
- Edit via the **portrait icon** in the header.
- Chat displays the persona’s `name` instead of “User” for all user messages.

### Prompt Templates Editor
- Click the **settings icon** (three bars) in the header → “Edit Prompts”.
- Three tabs: Narrator, Character, Permutation.
- Each has:
  - **Template** – a string with macros and `{{#if}}`.
  - **Main Prompt** – the fixed instruction appended after the template.
- Changes are saved immediately to `prompts.json` (backups kept).
- (Integration with LLM will be added in v0.5.)

---

## Project Structure (v0.4.5)

```
RPGLM/
├── backend/
│   ├── main.py
│   ├── context/                  # ContextBuilder (placeholder)
│   ├── generation/               # Orchestrator (placeholder)
│   ├── llm/                      # KoboldCppClient
│   ├── lorebook/                 # Full lorebook logic
│   ├── macros/                   # MacroService
│   ├── managers/                 # PersonaManager, PromptsManager
│   ├── parsers/                  # ResponseParser (placeholder)
│   ├── prompts/                  # default_prompts.json
│   ├── storage/                  # TimelineStorage, LorebookStorage, PersonaStorage, PromptsStorage
│   └── utils/                    # world_state helpers
├── frontend/
│   ├── index.html
│   ├── css/                      # styles.css, lorebook.css
│   ├── js/                       # chat.js, lorebook.js, world_state_panel.js, persona_modal.js, settings_modal.js, prompts_modal.js
│   └── assets/icons/
├── data/worlds/default/
│   ├── timeline.jsonl
│   ├── timeline.tmp.jsonl
│   ├── lorebook.json
│   ├── persona.json
│   ├── prompts.json
│   ├── backups/
│   ├── lorebook_backups/
│   └── persona_backups/
├── run.py
└── README.md
```

---

## API Endpoints (added in v0.4.5)

| Method | Path                         | Description                               |
|--------|------------------------------|-------------------------------------------|
| GET    | `/api/world_state/current`   | Return last saved world state             |
| POST   | `/api/rollback`              | Delete last message and restore previous state |
| GET    | `/api/persona`               | Get user persona (name, description)      |
| PUT    | `/api/persona`               | Update user persona                       |
| GET    | `/api/prompts`               | Get templates and main prompts            |
| PUT    | `/api/prompts`               | Update templates and/or main prompts      |

All existing lorebook endpoints (under `/lorebook`) remain unchanged.

---

## Known limitations (v0.4.5)

- The new prompt templates and macro system are **not yet used** for LLM generation – they will be integrated in v0.5.
- World state affects only saved messages, not yet the LLM context.
- No automatic keyword‑based activation of lorebook entries.
- No RAG or large‑entry handling.

---

## Next steps (v0.5)

- Implement `ContextBuilder` and `GenerationOrchestrator`.
- Actually use prompt templates, macros, world state, persona, and lorebook data when calling the LLM.
- Add sequential generation (narrator → character → …).
- Support abort and streaming through the orchestrator.
