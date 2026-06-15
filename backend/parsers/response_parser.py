"""Response parser for LLM output."""

from typing import List, Dict, Any


class ResponseParser:
    """Parse LLM response into structured blocks or messages."""

    @staticmethod
    def parse_blocks(text: str) -> List[str]:
        """
        Parse the response into logical blocks.

        Args:
            text: Raw LLM response text.

        Returns:
            List of block strings.
        """
        # Placeholder implementation
        return [text]

    # DEPRECATED: Use proper splitting logic instead.
    @staticmethod
    def split_into_messages() -> None:
        """Deprecated method – do not use."""
        pass