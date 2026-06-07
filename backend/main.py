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

# Global safe counters and locks
_version_lock = asyncio.Lock()
_storage_lock = asyncio.Lock()
_next_version = 1


async def init_version_counter() -> None:
    """
    Initializes the message version counter by scanning existing
    timeline files to prevent duplicate version assignments.
    """
    global _next_version
    async with _storage_lock:
        all_msgs = world_storage.get_sorted_history()
    if all_msgs:
        max_ver = max((msg.get("ver", 0) for msg in all_msgs), default=0)
        _next_version = max_ver + 1
    else:
        _next_version = 1


async def get_next_version() -> int:
    """
    Provides a thread-safe incremented version identifier for new messages.
    """
    global _next_version
    async with _version_lock:
        ver = _next_version
        _next_version += 1
        return ver


async def periodic_save_task() -> None:
    """
    Background worker loop that commits temporary logs into the main
    stable database timeline file at fixed intervals.
    """
    while True:
        await asyncio.sleep(SAVE_INTERVAL_SECONDS)
        try:
            async with _storage_lock:
                world_storage.flush_tmp_to_main()
        except Exception as e:
            print(f"[Buffer Save Error] {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages startup and shutdown lifecycles of the application,
    recovering files and initializing active background tasks.
    """
    async with _storage_lock:
        world_storage.recover_if_needed()
    await init_version_counter()
    bg_task = asyncio.create_task(periodic_save_task())
    yield
    bg_task.cancel()


app = FastAPI(lifespan=lifespan)
app.add_middleware(NoCacheMiddleware)


class MessageRequest(BaseModel):
    text: str


class HistoryResponse(BaseModel):
    messages: list
    latest_version: int


@app.get("/api/history", response_model=HistoryResponse)
async def get_history():
    """
    API endpoint returning compiled, deduplicated, and sorted
    message logs to synchronize the frontend history UI.
    """
    async with _storage_lock:
        sorted_msgs = world_storage.get_sorted_history()
    latest_version = sorted_msgs[-1]["ver"] if sorted_msgs else 0
    return HistoryResponse(messages=sorted_msgs, latest_version=latest_version)


def compile_macros(text: str, user_name: str, char_name: str) -> str:
    """
    Replaces template macros ({{user}}, {{char}}) with defined values
    at compile-time before pipeline routing.
    """
    return text.replace("{{user}}", user_name).replace("{{char}}", char_name)


@app.post("/api/send")
async def send_message(request: MessageRequest) -> Dict[str, str]:
    """
    Handles incoming player statements, updates buffers, compiles contextual schemas,
    triggers inference, and commits LLM responses to storage.
    """
    user_text = request.text.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Dynamic target identities (mock states to be replaced with profiles in v0.4)
    USER_NAME = "User"
    CHAR_NAME = "Assistant"

    # Pre-compile macros inside user input
    user_text = compile_macros(user_text, USER_NAME, CHAR_NAME)

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

    # System instruction template forcing structural separation
    raw_instruction = (
        "You are a roleplay engine. User: '{{user}}', Assistant Persona: '{{char}}'.\n"
        "FORMATTING RULES:\n"
        "1. Start your response paragraph with '**{{char}}:**' if it represents your actions or speech.\n"
        "2. Wrap narrative/actions in asterisks: *She walks into the room.*\n"
        "3. Wrap spoken dialogue in double quotes: \"Hello!\"\n"
        "4. Wrap character's inner thoughts/monologue in single backticks: `Why is he looking at me like that?`.\n"
        "5. Wrap stats, technical parameters, or code blocks in triple backticks:"
    )