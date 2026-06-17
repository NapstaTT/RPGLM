import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .middleware import NoCacheMiddleware
from .storage.timeline_storage import StorageConfig, TimelineStorage
from .llm.llm_client import KoboldCppClient
from .utils.world_state import get_empty_world_state, get_last_world_state

from .lorebook import LorebookConfig, LorebookStorage
from .lorebook.location import LocationManager
from .lorebook.character import CharacterManager
from .lorebook.entry import EntryManager
from .lorebook.router import router as lorebook_router

from .managers.persona_manager import PersonaManager
from .managers.prompts_manager import PromptsManager
from .context.context_builder import ContextBuilder
from .parsers.response_parser import ResponseParser
from .generation.orchestrator import GenerationOrchestrator
from .utils.entry_activator import EntryActivator

# Environment Configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:5001")
WORLD_ID = "default"
SAVE_INTERVAL_SECONDS = 3

# LLM Settings (hardcoded for now)
LLM_SETTINGS = {
    "max_length": 100,
    "temperature": 0.7,
    "stop": ["**User:"],  # Stop if LLM tries to write user's lines
}

# Storage Layer Initialization
storage_config = StorageConfig()
timeline_storage = TimelineStorage(world_id=WORLD_ID, config=storage_config)

# LLM Client
llm_client = KoboldCppClient(base_url=LLM_BASE_URL)

# Thread/Async Safety Locks
_version_lock = asyncio.Lock()
_storage_lock = asyncio.Lock()
_next_version = 1

# Global orchestrator for abort
_current_orchestrator = None


async def init_version_counter() -> None:
    """Initialize the message version counter from existing history."""
    global _next_version
    async with _storage_lock:
        all_msgs = timeline_storage.get_sorted_history()
    if all_msgs:
        max_ver = max((msg.get("ver", 0) for msg in all_msgs), default=0)
        _next_version = max_ver + 1
    else:
        _next_version = 1
    print(f"[Server] Version counter initialized. Next version: {_next_version}")


async def get_next_version() -> int:
    """Return the next sequential version number."""
    global _next_version
    async with _version_lock:
        ver = _next_version
        _next_version += 1
        return ver


async def periodic_save_task() -> None:
    """Background task that periodically flushes the temporary buffer to main storage."""
    while True:
        await asyncio.sleep(SAVE_INTERVAL_SECONDS)
        try:
            async with _storage_lock:
                timeline_storage.flush_tmp_to_main()
        except Exception as e:
            print(f"[Background Task Error] Failed to flush buffer: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    async with _storage_lock:
        timeline_storage.recover_if_needed()
    await init_version_counter()
    bg_task = asyncio.create_task(periodic_save_task())

    # --- Lorebook initialization ---
    lorebook_config = LorebookConfig()
    lorebook_storage = LorebookStorage(world_id=WORLD_ID, config=lorebook_config)
    app.state.lorebook_storage = lorebook_storage
    app.state.lorebook_managers = {
        "locations": LocationManager(lorebook_storage),
        "characters": CharacterManager(lorebook_storage),
        "entries": EntryManager(lorebook_storage),
    }

    # --- Managers ---
    persona_manager = PersonaManager(world_id=WORLD_ID)
    prompts_manager = PromptsManager(world_id=WORLD_ID)
    app.state.persona_manager = persona_manager
    app.state.prompts_manager = prompts_manager

    # --- Context Builder ---
    entry_activator = EntryActivator(lorebook_storage)
    context_builder = ContextBuilder(
        lorebook_storage=lorebook_storage,
        timeline_storage=timeline_storage,
        entry_activator=entry_activator,
    )
    app.state.context_builder = context_builder

    # --- Response Parser (stateless) ---
    response_parser = ResponseParser()
    app.state.response_parser = response_parser

    print(f"[Server] RGPLM Backend v0.5 active. LLM: {LLM_BASE_URL}")
    yield

    bg_task.cancel()
    await lorebook_storage.shutdown()
    print("[Server] RGPLM Backend shutting down.")


app = FastAPI(lifespan=lifespan)
app.add_middleware(NoCacheMiddleware)


class MessageRequest(BaseModel):
    text: str
    world_state: Optional[dict] = None


class HistoryResponse(BaseModel):
    messages: list
    latest_version: int


@app.get("/api/history", response_model=HistoryResponse)
async def get_history():
    """Return the full message history."""
    async with _storage_lock:
        sorted_msgs = timeline_storage.get_sorted_history()
    latest_version = sorted_msgs[-1]["ver"] if sorted_msgs else 0
    return HistoryResponse(messages=sorted_msgs, latest_version=latest_version)


@app.get("/api/world_state/current")
async def get_current_world_state():
    """Return the world state from the last message, or empty."""
    async with _storage_lock:
        state = get_last_world_state(timeline_storage)
    return state


@app.post("/api/rollback")
async def rollback_last_message():
    """Delete the last message from tmp (or main) and return the updated world state."""
    async with _storage_lock:
        tmp_msgs = timeline_storage.read_tmp()
        if tmp_msgs:
            tmp_msgs.pop()
            tmp_path = timeline_storage.config.get_tmp_path(timeline_storage.world_id)
            if tmp_path.exists():
                tmp_path.unlink()
            for msg in tmp_msgs:
                timeline_storage.append_to_tmp(msg)
        else:
            main_msgs = timeline_storage.read_main()
            if not main_msgs:
                raise HTTPException(400, "No messages to rollback")
            main_msgs.pop()
            timeline_storage.create_backup()
            timeline_storage.atomic_save_main(main_msgs)

        new_state = get_last_world_state(timeline_storage)
        return new_state


# ---- Prompts endpoints ----
@app.get("/api/prompts")
async def get_prompts(request: Request):
    mgr = request.app.state.prompts_manager
    return {
        "templates": mgr.storage.get_templates(),
        "prompts": mgr.storage.get_prompts()
    }


@app.put("/api/prompts")
async def update_prompts(data: dict, request: Request):
    mgr = request.app.state.prompts_manager
    try:
        if "templates" in data:
            mgr.storage.update_templates(data["templates"])
        if "prompts" in data:
            mgr.storage.update_prompts(data["prompts"])
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(400, str(e))


# ---- Main send endpoint ----
@app.post("/api/send")
async def send_message(req: Request, msg: MessageRequest):

    print(f"[Main] Received message: {msg.text[:50]}...")

    user_text = msg.text.strip()
    if not user_text:
        raise HTTPException(400, "Message cannot be empty")

    # Get persona
    persona = await req.app.state.persona_manager.get_persona()
    user_role = persona.get("name", "User")

    # Save user message
    user_ver = await get_next_version()
    user_msg = {
        "ver": user_ver,
        "role": user_role,
        "content": user_text,
        "timestamp": datetime.now().isoformat(),
        "mutations": [],
    }
    async with _storage_lock:
        timeline_storage.append_to_tmp(user_msg, world_state=msg.world_state)

    print("[Main] Creating orchestrator...")

    # Create orchestrator
    orchestrator = GenerationOrchestrator(
        llm_client=llm_client,
        context_builder=req.app.state.context_builder,
        prompts_manager=req.app.state.prompts_manager,
        response_parser=req.app.state.response_parser,
        lorebook_storage=req.app.state.lorebook_storage,
        persona_storage=req.app.state.persona_manager._storage,
        llm_settings=LLM_SETTINGS,
        max_retries=1,
        max_blocks=3,
    )

    global _current_orchestrator
    _current_orchestrator = orchestrator

    try:
        print("[Main] Starting orchestrator.run()...")
        generated_messages = await orchestrator.run(
            user_message=user_text,
            world_state=msg.world_state or {},
            persona=persona,
        )
        print(f"[Main] Orchestrator returned {len(generated_messages)} messages")
    except Exception as e:
        print(f"[Main] Orchestrator error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        _current_orchestrator = None

    print("[Main] Saving messages...")
    # Save generated messages
    async with _storage_lock:
        for m in generated_messages:
            m["ver"] = await get_next_version()
            m["timestamp"] = datetime.now().isoformat()
            m["mutations"] = []
            timeline_storage.append_to_tmp(m, world_state=m.get("world_state"))
    print("[Main] Messages saved, returning response")

    return {"messages": generated_messages}


# ---- Abort endpoint ----
@app.post("/api/abort")
async def abort_generation():
    """Stop the ongoing LLM generation."""
    global _current_orchestrator
    if _current_orchestrator:
        _current_orchestrator.abort()
        return {"aborted": True}
    return {"aborted": False}


# ---- Persona endpoints ----
@app.get("/api/persona")
async def get_persona(request: Request):
    return await request.app.state.persona_manager.get_persona()


@app.put("/api/persona")
async def update_persona(data: dict, request: Request):
    try:
        result = await request.app.state.persona_manager.update_persona(data)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


app.include_router(lorebook_router)

# --- Static Files and Frontend Routing ---
PROJECT_ROOT = Path(__file__).parent.parent
frontend_path = PROJECT_ROOT / "frontend"

if frontend_path.exists():
    @app.get("/")
    async def read_index():
        return FileResponse(frontend_path / "index.html")
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
else:
    print(f"[Warning] Frontend resource directory not found at: {frontend_path}")