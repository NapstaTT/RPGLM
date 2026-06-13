import json
import re
import httpx
from typing import List, Dict, Any, Callable, Optional


class KoboldCppClient:
    """Client for KoboldCPP with streaming and abort support."""

    def __init__(self, base_url: str, model: str = "local-model", timeout: float = 120.0):
        """Initialize the client.

        Args:
            base_url: Base URL of KoboldCPP server (e.g., 'http://localhost:5001').
            model: Model name to use (default 'local-model').
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self._abort_requested = False

    async def generate_full(self, messages: List[Dict[str, str]]) -> str:
        """Generate a complete response without streaming (fallback mode).

        Args:
            messages: List of message dicts with 'role' and 'content'.

        Returns:
            The generated text content.

        Raises:
            httpx.HTTPStatusError: If the request fails.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "max_tokens": 512,
            "temperature": 0.7,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def generate_stream(self, messages: List[Dict[str, str]],
                              on_chunk: Callable[[str], None]) -> str:
        """Generate a response with streaming.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            on_chunk: Callback that receives each text fragment.

        Returns:
            The full accumulated response string.
        """
        self._abort_requested = False
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "max_tokens": 512,
            "temperature": 0.7,
        }
        full_text = ""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", f"{self.base_url}/v1/chat/completions",
                                     json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if self._abort_requested:
                        break
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta:
                            content = delta["content"]
                            full_text += content
                            on_chunk(content)
                    except json.JSONDecodeError:
                        continue
        return full_text

    async def abort(self) -> bool:
        """Send an abort command to stop generation.

        Returns:
            True if the abort request succeeded, False otherwise.
        """
        self._abort_requested = True
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(f"{self.base_url}/api/extra/abort")
                return resp.status_code == 200
        except Exception:
            return False


def split_into_messages(full_response: str) -> List[Dict[str, str]]:
    """Split LLM response into individual messages using **Name:** tags.

    Args:
        full_response: The raw response from the LLM.

    Returns:
        A list of dicts with 'role' (the name) and 'content' (the text).
    """
    pattern = r'\*\*([^:]+):\*\*\s*'
    parts = re.split(pattern, full_response)
    messages = []
    for i in range(1, len(parts), 2):
        role = parts[i].strip()
        content = parts[i+1].strip() if i+1 < len(parts) else ''
        if content:
            messages.append({"role": role, "content": content})
    return messages