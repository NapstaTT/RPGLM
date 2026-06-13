# RPGLM v0.4

**Version 0.4** – Lorebook module: locations, characters, and entries management.

Built as a student research project (Team No.6).  
This release adds a **full-featured Lorebook** – a standalone module for managing world locations, characters, and arbitrary lore entries.  
It includes atomic JSON storage, automatic backups, versioning, and a dedicated UI with dropdowns and checkboxes.

**Previous version (v0.3)** added streaming LLM responses, stop button, tag-based message splitting, and macro replacement.

---

## What’s new in v0.4

- **Lorebook database** – Three entity types stored in a single `lorebook.json` file:
  - **Locations** – hierarchical (parent/child), can contain characters, have flags like `is_leaf`.
  - **Characters** – have `name` instead of `title`, can be assigned to locations.
  - **Entries** – generic lore fragments, can be linked to a location.
- **Full CRUD via REST API** – endpoints for each entity type, with validation (parent existence, character references).
- **Atomic saving with delay** – Changes are saved 3 seconds after the last modification, preventing disk spam.
- **Backups & versioning** – Up to 5 automatic backups of `lorebook.json`. Version field for future migrations.
- **Dedicated UI** – Full-screen modal accessible via the book icon in the header.
  - Three tabs: Locations, Characters, Entries.
  - Cards with title, state icon, description preview.
  - Buttons: Add, Edit (✏️), Delete (🗑️).
- **Smart forms** – Dropdowns for parent locations and linked locations (no manual UUID typing).
- **Character assignment** – Checkbox group for selecting which characters appear on a location.
- **Cross-browser delete confirmation** – Custom modal dialog works in Firefox (where `confirm()` may be blocked).
- **Polymorphic backend** – Base class `BaseLorebookManager` with hooks for validation and cascade deletion.
- **Separation of concerns** – Lorebook lives in its own Python package (`backend/lorebook/`) with clear separation from chat logic.

---

## What is NOT in v0.4 (planned for v0.5+)

- Integration with chat – Lorebook data does not yet affect LLM prompts.
- Automatic character activation / location switching.
- Import from Character Card V2 (PNG).
- RAG (retrieval-augmented generation) for large entries.
- Lorebook search / filtering in UI.

---

## Requirements (unchanged)

- Python 3.10+
- A local LLM server with OpenAI‑compatible streaming API (KoboldCPP recommended).

---

## Installation & Configuration

Same as v0.3. The lorebook is automatically initialised for each world.

| Variable         | Default                          | Description                          |
|------------------|----------------------------------|--------------------------------------|
| `LLM_BASE_URL`   | `http://localhost:5001`          | Base URL of your LLM server (without `/v1`) |
| `WORLD_ID`       | `default`                        | Subdirectory inside `data/worlds/`   |

Example:
```bash
export LLM_BASE_URL="http://127.0.0.1:5001"
export WORLD_ID="my_campaign"
```

---

## Running

```bash
python run.py
```

Open `http://localhost:8000`.

Click the **book icon** in the top header to open the Lorebook.

---

## Project structure (v0.4)

```
RPGLM/
├── backend/
│   ├── main.py                 # FastAPI app, includes lorebook router
│   ├── lorebook/               # NEW: full lorebook package
│   │   ├── __init__.py
│   │   ├── storage.py          # LorebookConfig, LorebookStorage (atomic I/O, backups)
│   │   ├── base.py             # BaseLorebookManager (abstract CRUD with hooks)
│   │   ├── location.py         # LocationManager (parent validation, cascade)
│   │   ├── character.py        # CharacterManager (name required, cleanup)
│   │   ├── entry.py            # EntryManager (optional location link)
│   │   └── router.py           # FastAPI endpoints (/lorebook/*)
│   ├── llm_client.py           # (unchanged)
│   ├── storage.py              # (unchanged, for timeline)
│   └── middleware.py
├── frontend/
│   ├── index.html
│   ├── css/
│   │   ├── styles.css          # main chat styles
│   │   └── lorebook.css        # NEW: lorebook modal styles
│   ├── js/
│   │   ├── chat.js             # (unchanged)
│   │   └── lorebook.js         # NEW: LorebookUI class
│   └── assets/icons/
├── data/worlds/default/
│   ├── timeline.jsonl
│   ├── lorebook.json           # created automatically
│   ├── backups/                # timeline backups
│   └── lorebook_backups/       # lorebook backups (max 5)
├── run.py
└── README.md
```

---

## API endpoints (lorebook)

All endpoints require no authentication. Base path: `/lorebook`

| Method | Path                               | Description                               |
|--------|------------------------------------|-------------------------------------------|
| GET    | `/lorebook/locations`              | List all locations                        |
| POST   | `/lorebook/locations`              | Create a new location                     |
| PUT    | `/lorebook/locations/{id}`         | Update location                           |
| DELETE | `/lorebook/locations/{id}`         | Delete location (cascades references)     |
| GET    | `/lorebook/characters`             | List all characters                       |
| POST   | `/lorebook/characters`             | Create a new character                    |
| PUT    | `/lorebook/characters/{id}`        | Update character                          |
| DELETE | `/lorebook/characters/{id}`        | Delete character (removes from locations) |
| GET    | `/lorebook/entries`                | List all entries                          |
| POST   | `/lorebook/entries`                | Create a new entry                        |
| PUT    | `/lorebook/entries/{id}`           | Update entry                              |
| DELETE | `/lorebook/entries/{id}`           | Delete entry                              |
| POST   | `/lorebook/locations/{loc_id}/characters/{char_id}` | Assign character to location |
| DELETE | `/lorebook/locations/{loc_id}/characters/{char_id}` | Remove character from location |

---

## Data format (lorebook.json)

```json
{
  "version": 1,
  "locations": [ /* array of location objects */ ],
  "characters": [ /* array of character objects */ ],
  "entries": [ /* array of entry objects */ ]
}
```

Each object has:
- `id` (UUID)
- `title` (or `name` for characters)
- `description`
- `state` (`always_active`, `activate_on_keyword`, `deactivated`)
- `keywords` (array of strings)
- `logic` (`ANY` or `ALL`)
- `chance` (0–100)
- `depth` (0–100)
- `position` (integer, sorting order)
- `undeletable` (bool, e.g., system locations)

Location extra fields: `parent_id`, `is_leaf`, `characters_on_location` (array of character IDs).  
Entry extra field: `parent_id` (optional location ID).  
Character extra field: `name` (instead of `title`).

---

## Known limitations & quirks (v0.4)

- **No integration with chat** – Lorebook data is not yet injected into LLM context. That’s v0.5.
- **UI is basic but functional** – No drag‑and‑drop reordering, no search/filter.
- **System location is undeletable** – `id = "system_locations"` cannot be removed, but its description can be edited.
- **Character avatars** – Not stored yet; placeholder.
- **Validation** – Only basic checks (parent existence, character existence). Cycles in location hierarchy are not prevented.
- **Backups** – Created before each atomic save. Old backups are rotated (last 5 kept).
- **Delay before save** – 3 seconds after last change. If you close the browser immediately, data may not be saved. Always close the lorebook via the ✖ button to trigger an immediate save.

---

## Next steps (v0.5+)

- **Lorebook → LLM context** – Active locations, characters, and triggered entries will be inserted into the system prompt.
- **Dynamic location switching** – LLM will be able to change current location.
- **Character activation** – Characters appear based on location or keywords.
- **Import from Character Card V2** (PNG).
- **RAG (retrieval-augmented generation)** – Large entries will be selectively retrieved.
- **Configurable LLM parameters** in UI.
- **Multi‑world switching**.