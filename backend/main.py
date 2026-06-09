import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .middleware import NoCacheMiddleware
from .storage import StorageConfig, WorldStorage

# Environment Configuration
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "http://localhost:5001/v1/chat/completions")
WORLD_ID = "default"
SAVE_INTERVAL_SECONDS = 3

# Storage Layer Initialization
storage_config = StorageConfig()
world_storage = WorldStorage(world_id=WORLD_ID, config=storage_config)

# Thread/Async Safety Locks
_version_lock = asyncio.Lock()
_storage_lock = asyncio.Lock()
_next_version = 1


async def init_version_counter() -> None:
    """Scans the timeline history to determine the starting index for sequential message versioning."""
    global _next_version
    async with _storage_lock:
        all_msgs = world_storage.get_sorted_history()
    
    if all_msgs:
        max_ver = max((msg.get("ver", 0) for msg in all_msgs), default=0)
        _next_version = max_ver + 1
    else:
        _next_version = 1
    print(f"[Server] Version counter initialized. Next version: {_next_version}")


async def get_next_version() -> int:
    """Thread-safe generator for sequential unique version numbers."""
    global _next_version
    async with _version_lock:
        ver = _next_version
        _next_version += 1
        return ver


async def periodic_save_task() -> None:
    """Background loop that periodically flushes the memory-efficient append-only log to disk."""
    while True:
        await asyncio.sleep(SAVE_INTERVAL_SECONDS)
        try:
            async with _storage_lock:
                world_storage.flush_tmp_to_main()
        except Exception as e:
            print(f"[Background Task Error] Failed to flush buffer: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Events
    async with _storage_lock:
        world_storage.recover_if_needed()
    await init_version_counter()
    
    bg_task = asyncio.create_task(periodic_save_task())
    print(f"[Server] RGPLM Backend v0.2 active. Connected LLM: {LLM_ENDPOINT}")
    
    yield
    # Shutdown Events
    bg_task.cancel()
    print("[Server] RGPLM Backend shutting down.")


app = FastAPI(lifespan=lifespan)
app.add_middleware(NoCacheMiddleware)


class MessageRequest(BaseModel):
    text: str


class HistoryResponse(BaseModel):
    messages: list
    latest_version: int


@app.get("/api/history", response_model=HistoryResponse)
async def get_history():
    """Fetches the complete sorted message timeline for the frontend."""
    async with _storage_lock:
        sorted_msgs = world_storage.get_sorted_history()
        
    latest_version = sorted_msgs[-1]["ver"] if sorted_msgs else 0
    return HistoryResponse(messages=sorted_msgs, latest_version=latest_version)


@app.post("/api/send")
async def send_message(request: MessageRequest) -> Dict[str, str]:
    """Handles incoming user messages, appends to log, and triggers the LLM group pipeline."""
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
        world_storage.append_to_tmp(user_msg)
        sorted_all = world_storage.get_sorted_history()

    # Extract conversation context (Latest 20 messages for prompt efficiency)
    context_msgs = sorted_all[-20:] if len(sorted_all) > 20 else sorted_all
    messages_for_llm = [
        {"role": m["role"], "content": m["content"]}
        for m in context_msgs
        if m["role"] in ("user", "assistant", "system")
    ]

    payload = {
        "model": "local-model",
        "messages": messages_for_llm,
        "stream": False,
        "max_tokens": 512,
        "temperature": 0.7,
    }

    # Request prediction from the local LLM cluster
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(LLM_ENDPOINT, json=payload)
            response.raise_for_status()
            data = response.json()
            llm_reply = data["choices"][0]["message"]["content"]
        except Exception as e:
            llm_reply = f"[LLM Node Error: {e}]"

    assistant_ver = await get_next_version()
    assistant_msg = {
        "ver": assistant_ver,
        "role": "assistant",
        "content": llm_reply,
        "timestamp": datetime.now().isoformat(),
        "mutations": [],
    }
    
    async with _storage_lock:
        world_storage.append_to_tmp(assistant_msg)

    return {"reply": llm_reply}


# --- Static Files and Frontend Routing ---
PROJECT_ROOT = Path(__file__).parent.parent
frontend_path = PROJECT_ROOT / "frontend"

if frontend_path.exists():
    # Serve index.html explicitly at the root URL
    @app.get("/")
    async def read_index():
        """Serves the main application landing page."""
        return FileResponse(frontend_path / "index.html")

    # Mount the frontend directory to the root path.
    # html=True allows it to resolve relative sub-paths like css/styles.css automatically.
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
else:
    print(f"[Warning] Frontend resource directory not found at: {frontend_path}")