"""Prompts manager for handling templates and prompts with macro expansion."""

from typing import Dict, Any
from ..storage.prompts_storage import PromptsStorage
from ..macros.macros_service import MacroService


class PromptsManager:
    """Manages prompt templates and applies macros."""

    def __init__(self, world_id: str):
        """Initialize with storage and macro service."""
        self.storage = PromptsStorage(world_id)
        self.macro_service = MacroService()

    def build_prompt(self, prompt_type: str, context: Dict[str, Any]) -> str:
        """
        Build a final prompt by applying macros to the template and appending the main prompt.

        Args:
            prompt_type: Type of prompt (e.g., 'narrator', 'character').
            context: Context dictionary for macro substitution.

        Returns:
            Fully processed prompt string.
        """
        template = self.storage.get_template(prompt_type)
        prompt_text = self.storage.get_prompt(prompt_type)
        if not template or not prompt_text:
            return ""  # fallback
        processed_template = self.macro_service.apply(template, **context)
        return f"{processed_template}\n\n{prompt_text}".strip()