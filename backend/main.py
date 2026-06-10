import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .middleware import NoCacheMiddleware
from .storage import StorageConfig, WorldStorage
from .llm_client import KoboldCppClient, split_into_messages

# Environment Configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:5001")   # без /v1
WORLD_ID = "default"
SAVE_INTERVAL_SECONDS = 3

# Storage Layer Initialization
storage_config = StorageConfig()
world_storage = WorldStorage(world_id=WORLD_ID, config=storage_config)

# LLM Client
llm_client = KoboldCppClient(base_url=LLM_BASE_URL)

# Thread/Async Safety Locks
_version_lock = asyncio.Lock()
_storage_lock = asyncio.Lock()
_next_version = 1


async def init_version_counter() -> None:
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
    global _next_version
    async with _version_lock:
        ver = _next_version
        _next_version += 1
        return ver


async def periodic_save_task() -> None:
    while True:
        await asyncio.sleep(SAVE_INTERVAL_SECONDS)
        try:
            async with _storage_lock:
                world_storage.flush_tmp_to_main()
        except Exception as e:
            print(f"[Background Task Error] Failed to flush buffer: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with _storage_lock:
        world_storage.recover_if_needed()
    await init_version_counter()
    bg_task = asyncio.create_task(periodic_save_task())
    print(f"[Server] RGPLM Backend v0.3 active. LLM: {LLM_BASE_URL}")
    yield
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
    async with _storage_lock:
        sorted_msgs = world_storage.get_sorted_history()
    latest_version = sorted_msgs[-1]["ver"] if sorted_msgs else 0
    return HistoryResponse(messages=sorted_msgs, latest_version=latest_version)


# ---- старый эндпоинт (без стриминга, для совместимости) ----
@app.post("/api/send")
async def send_message(request: MessageRequest) -> Dict[str, str]:
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
        world_storage.append_to_tmp(assistant_msg)

    return {"reply": llm_reply}


# ---- новый стриминговый эндпоинт с разбиением по тегам ----
@app.post("/api/send/stream")
async def send_message_stream(request: MessageRequest, raw_request: Request):
    user_text = request.text.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Сохраняем сообщение пользователя
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

    # Получаем историю для контекста
    async with _storage_lock:
        sorted_all = world_storage.get_sorted_history()
    context_msgs = sorted_all[-20:] if len(sorted_all) > 20 else sorted_all

    # Преобразуем историю для LLM
    messages_for_llm = []
    for m in context_msgs:
        role = "user" if m["role"] == "user" else "assistant"
        content = m["content"]
        content = content.replace("{{user}}", "User").replace("{{char}}", "Assistant")
        messages_for_llm.append({"role": role, "content": content})

    # Системный промпт
    system_prompt = {
        "role": "system",
        "content": (
            "Ты — мастер игры и все персонажи мира. Отвечай, используя формат:\n"
            "**Имя персонажа:** его реплика или действие.\n"
            "Ты можешь давать несколько таких блоков подряд. "
            "Заканчивай ответ, когда встречаешь слово **User:** (это сигнал остановки, его не включай в ответ)."
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
                    # Проверяем, не отключился ли клиент
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
            # ВСЕГДА сохраняем то, что накопили (даже пустую строку не сохраняем)
            if full_reply:
                print(f"[Stream] Saving partial/full reply ({len(full_reply)} chars)")
                # Обрезаем по стоп-слову
                stop_word = "**User:**"
                if stop_word in full_reply:
                    full_reply = full_reply.split(stop_word)[0].rstrip()
                # Разбиваем на сообщения
                parsed_msgs = split_into_messages(full_reply)
                if parsed_msgs:
                    async with _storage_lock:
                        for msg in parsed_msgs:
                            assistant_ver = await get_next_version()
                            assistant_msg = {
                                "ver": assistant_ver,
                                "role": msg["role"],
                                "content": msg["content"],
                                "timestamp": datetime.now().isoformat(),
                                "mutations": [],
                            }
                            world_storage.append_to_tmp(assistant_msg)
                    print(f"[Stream] Saved {len(parsed_msgs)} messages")
                else:
                    # Если не удалось разбить по тегам, сохраняем как есть с role="assistant"
                    assistant_ver = await get_next_version()
                    assistant_msg = {
                        "ver": assistant_ver,
                        "role": "assistant",
                        "content": full_reply,
                        "timestamp": datetime.now().isoformat(),
                        "mutations": [],
                    }
                    async with _storage_lock:
                        world_storage.append_to_tmp(assistant_msg)
                    print("[Stream] Saved as single assistant message")
            # Отправляем сигнал завершения клиенту
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ---- остановка генерации ----
@app.post("/api/abort")
async def abort_generation():
    success = await llm_client.abort()
    return {"aborted": success}


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