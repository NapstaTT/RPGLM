"""Client for KoboldCPP API with streaming and abort support."""

import json
import httpx
from typing import List, Dict, Any, Optional, Union, AsyncGenerator


class KoboldCppClient:
    """Client for KoboldCPP with streaming and abort support."""

    def __init__(self, base_url: str, model: str = "local-model", timeout: float = 120.0):
        """
        Initialize the client.

        Args:
            base_url: Base URL of KoboldCPP server (e.g., 'http://localhost:5001').
            model: Model name to use (default 'local-model').
            timeout: Request timeout in seconds (default 120.0).
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self._abort_requested = False

    async def generate_full(
        self,
        messages: List[Dict[str, str]],
        stop: Optional[Union[str, List[str]]] = None
    ) -> str:
        """Generate a complete response without streaming."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "max_tokens": 512,
            "temperature": 0.7,
        }
        if stop:
            payload["stop"] = stop
        async with httpx.AsyncClient(timeout=self.timeout, proxy=None) as client:
            resp = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        settings: Optional[Dict[str, Any]] = None,
        stop: Optional[Union[str, List[str]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a response with streaming (async generator).

        Yields:
            Text chunks as they arrive.
        """
        self._abort_requested = False
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "max_tokens": 512,
            "temperature": 0.7,
        }
        if settings:
            payload.update(settings)
        if stop:
            payload["stop"] = stop

        async with httpx.AsyncClient(timeout=self.timeout, proxy=None) as client:
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
                            yield delta["content"]
                    except json.JSONDecodeError:
                        continue

    async def abort(self) -> bool:
        """Send an abort command to stop generation."""
        self._abort_requested = True
        try:
            async with httpx.AsyncClient(timeout=5.0, proxy=None) as client:
                resp = await client.post(f"{self.base_url}/api/extra/abort")
                return resp.status_code == 200
        except Exception:
            return False