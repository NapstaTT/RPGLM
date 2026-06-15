import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
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

# Environment Configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:5001")   # without /v1
WORLD_ID = "default"
SAVE_INTERVAL_SECONDS = 3

# Storage Layer Initialization
storage_config = StorageConfig()
timeline_storage = TimelineStorage(world_id=WORLD_ID, config=storage_config)

# LLM Client
llm_client = KoboldCppClient(base_url=LLM_BASE_URL)

# Thread/Async Safety Locks
_version_lock = asyncio.Lock()
_storage_lock = asyncio.Lock()
_next_version = 1


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

    app.state.persona_manager = PersonaManager(world_id=WORLD_ID)
    app.state.prompts_manager = PromptsManager(world_id=WORLD_ID)

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
        # First check tmp
        tmp_msgs = timeline_storage.read_tmp()
        if tmp_msgs:
            # Delete last message from tmp (overwrite tmp file)
            tmp_msgs.pop()
            # Rewrite tmp file
            tmp_path = timeline_storage.config.get_tmp_path(timeline_storage.world_id)
            if tmp_path.exists():
                tmp_path.unlink()
            for msg in tmp_msgs:
                timeline_storage.append_to_tmp(msg)  # world_state already inside message
        else:
            # No tmp – delete from main
            main_msgs = timeline_storage.read_main()
            if not main_msgs:
                raise HTTPException(400, "No messages to rollback")
            main_msgs.pop()
            timeline_storage.create_backup()
            timeline_storage.atomic_save_main(main_msgs)

        # Return new last world_state
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


# ---- Legacy non-streaming endpoint ----
@app.post("/api/send")
async def send_message(request: MessageRequest) -> Dict[str, str]:
    """Send a message and receive a full (non-streaming) response."""
    user_text = request.text.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    user_ver = await get_next_version()
    user_msg = {
        "ver": user_ver,
        "role": "user",
        "content": user_text,
        "timestamp": datetime.now().isoformat(),
        "mutations": [],
    }
    async with _storage_lock:
        timeline_storage.append_to_tmp(user_msg, world_state=request.world_state)
        sorted_all = timeline_storage.get_sorted_history()

    context_msgs = sorted_all[-20:] if len(sorted_all) > 20 else sorted_all
    messages_for_llm = [
        {"role": m["role"], "content": m["content"]}
        for m in context_msgs
        if m["role"] in ("user", "assistant", "system")
    ]

    try:
        llm_reply = await llm_client.generate_full(messages_for_llm)
    except Exception as e:
        llm_reply = f"[LLM Error: {e}]"

    assistant_ver = await get_next_version()
    assistant_msg = {
        "ver": assistant_ver,
        "role": "assistant",
        "content": llm_reply,
        "timestamp": datetime.now().isoformat(),
        "mutations": [],
    }
    async with _storage_lock:
        timeline_storage.append_to_tmp(assistant_msg)

    return {"reply": llm_reply}


# ---- Streaming endpoint with message splitting ----
@app.post("/api/send/stream")
async def send_message_stream(request: MessageRequest, raw_request: Request):
    """Stream the LLM response and split it into separate messages by **Name:** tags."""
    user_text = request.text.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Save user message
    user_ver = await get_next_version()
    user_msg = {
        "ver": user_ver,
        "role": "user",
        "content": user_text,
        "timestamp": datetime.now().isoformat(),
        "mutations": [],
    }
    async with _storage_lock:
        timeline_storage.append_to_tmp(user_msg)

    # Get conversation history for context
    async with _storage_lock:
        sorted_all = timeline_storage.get_sorted_history()
    context_msgs = sorted_all[-20:] if len(sorted_all) > 20 else sorted_all

    # Convert history for LLM
    messages_for_llm = []
    for m in context_msgs:
        role = "user" if m["role"] == "user" else "assistant"
        content = m["content"]
        content = content.replace("{{user}}", "User").replace("{{char}}", "Assistant")
        messages_for_llm.append({"role": role, "content": content})

    # System prompt in English
    system_prompt = {
        "role": "system",
        "content": (
            "You are the game master and all characters in the world. Respond using the format:\n"
            "**Character name:** their line or action.\n"
            "You may give multiple such blocks in a row. Stop when you encounter the word **User:** "
            "(this is a stop signal, do not include it in the response)."
        )
    }
    messages_for_llm.insert(0, system_prompt)

    async def event_generator():
        full_reply = ""
        queue = asyncio.Queue()

        def on_chunk(chunk: str):
            asyncio.create_task(queue.put(chunk))

        gen_task = asyncio.create_task(
            llm_client.generate_stream(messages_for_llm, on_chunk)
        )

        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(queue.get(), timeout=0.1)
                    full_reply += chunk
                    yield f"data: {chunk}\n\n"
                except asyncio.TimeoutError:
                    if gen_task.done():
                        break
                    # Check if client disconnected
                    if await raw_request.is_disconnected():
                        print("[Stream] Client disconnected, aborting LLM...")
                        await llm_client.abort()
                        break
                    continue
        except asyncio.CancelledError:
            print("[Stream] Generator cancelled")
        except Exception as e:
            print(f"[Stream] Error: {e}")
        finally:
            # Always save accumulated reply (unless empty)
            if full_reply:
                print(f"[Stream] Saving partial/full reply ({len(full_reply)} chars)")
                # Trim stop word
                stop_word = "**User:**"
                if stop_word in full_reply:
                    full_reply = full_reply.split(stop_word)[0].rstrip()
                # TODO: Implement proper splitting into messages by **Name:**
                # For now, save as a single assistant message
                assistant_ver = await get_next_version()
                assistant_msg = {
                    "ver": assistant_ver,
                    "role": "assistant",
                    "content": full_reply,
                    "timestamp": datetime.now().isoformat(),
                    "mutations": [],
                }
                async with _storage_lock:
                    timeline_storage.append_to_tmp(assistant_msg)
                print("[Stream] Saved as single assistant message")
            # Send completion signal to client
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ---- Abort generation endpoint ----
@app.post("/api/abort")
async def abort_generation():
    """Stop the ongoing LLM generation."""
    success = await llm_client.abort()
    return {"aborted": success}


# ---- Persona endpoints ----
@app.get("/api/persona")
async def get_persona(request: Request):
    """Get user persona."""
    return await request.app.state.persona_manager.get_persona()


@app.put("/api/persona")
async def update_persona(data: dict, request: Request):
    """Update user persona."""
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