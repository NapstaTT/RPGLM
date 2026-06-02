"""
Backend server for RPGLM v0.1.
Accepts user messages, forwards to local LLM (KoboldCPP compatible),
and returns generated reply.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import httpx

app = FastAPI()

# Endpoint of the local LLM (can be overridden by env variable)
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "http://localhost:5001/v1/chat/completions")


class MessageRequest(BaseModel):
    """Request model for /api/send endpoint."""
    text: str


@app.post("/api/send")
async def send_message(request: MessageRequest) -> dict:
    """
    Send user message to local LLM and return the generated reply.

    Args:
        request (MessageRequest): Contains the user's text.

    Returns:
        dict: A dictionary with a 'reply' key containing LLM response or error message.
    """
    payload = {
        "model": "local-model",
        "messages": [{"role": "user", "content": request.text}],
        "stream": False,
        "max_tokens": 512,
        "temperature": 0.7,
    }

    async with httpx.AsyncClient(timeout=None) as client:
        try:
            response = await client.post(LLM_ENDPOINT, json=payload)
            response.raise_for_status()
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            reply = f"LLM HTTP error: {e.response.status_code}"
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            reply = f"LLM response format error: {e}"
        except Exception as e:  # Keep a generic fallback
            reply = f"Unexpected error: {e}"

    return {"reply": reply}


# Serve static frontend files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)