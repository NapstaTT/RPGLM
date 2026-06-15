"""Macro service for processing {{var}} and {{#if var}}...{{/if}} templates."""

import re
from typing import Dict, Optional, Any


class MacroService:
    """Service for applying macros to text templates."""

    SUPPORTED_MACROS = [
        "user", "char", "location", "time", "user_description",
        "system_prompt", "user_persona", "character_description",
        "location_description", "world_map", "history", "scenario"
    ]

    @staticmethod
    def apply(text: str, **context: Any) -> str:
        """
        Apply macros to the given text.

        Supports simple {{var}} replacement and conditional blocks {{#if var}}...{{/if}}.

        Args:
            text: The template string.
            **context: Key-value pairs for macro substitution.

        Returns:
            Processed string.
        """
        if not text:
            return text
        # Process conditional blocks {{#if var}}...{{/if}}
        result = MacroService._process_conditional_blocks(text, context)
        # Simple {{var}} replacement
        for key, value in context.items():
            if key in MacroService.SUPPORTED_MACROS and value is not None:
                result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

    @staticmethod
    def _process_conditional_blocks(text: str, context: Dict[str, Any]) -> str:
        """
        Remove blocks where condition is false. Supports non-nested blocks.

        Args:
            text: Input text.
            context: Context dictionary.

        Returns:
            Text with conditional blocks evaluated.
        """
        pattern = r'\{\{#if (\w+)\}\}(.*?)\{\{/if\}\}'

        def replacer(match: re.Match) -> str:
            var_name = match.group(1)
            content = match.group(2)
            if var_name in context and context[var_name]:
                return content
            else:
                return ""

        # Apply repeatedly until no more changes (simple approach)
        prev = None
        result = text
        while result != prev:
            prev = result
            result = re.sub(pattern, replacer, result, flags=re.DOTALL)
        return result

    @staticmethod
    def apply_from_dict(text: str, context: Dict[str, Optional[str]]) -> str:
        """Apply macros using a dictionary context."""
        return MacroService.apply(text, **context)