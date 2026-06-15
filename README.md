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