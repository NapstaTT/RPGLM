"""Generation orchestrator for coordinating LLM calls and post-processing."""

from typing import List, Dict, Any, Optional
from ..llm.llm_client import KoboldCppClient


class GenerationOrchestrator:
    """Coordinates the generation flow: context building, LLM call, parsing."""

    def __init__(self, llm_client: KoboldCppClient):
        """
        Initialize the orchestrator.

        Args:
            llm_client: The LLM client to use for generation.
        """
        self.llm_client = llm_client

    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Generate a full response using the LLM client.

        Args:
            messages: List of conversation messages.

        Returns:
            Generated text.
        """
        return await self.llm_client.generate_full(messages)