"""
Response parser for LLM output in narrator and character modes.
Stateless – all inputs are passed as arguments.
"""

import re
from typing import List, Dict, Any, Optional


class ResponseParser:
    """
    Parses LLM responses into narrative and character blocks.
    """

    def parse_narrator(
        self,
        text: str,
        character_names: List[str],
        max_blocks: int = 3
    ) -> Dict[str, Any]:
        """
        Parse narrator response.

        Args:
            text: raw LLM output (may be incomplete).
            character_names: list of existing character names (lowercase).
            max_blocks: maximum number of blocks to return.

        Returns:
            dict with status:
                - "complete": no masks found, or all masks valid and within limit
                - "invalid_character": character name doesn't exist
                - "limit_exceeded": more than max_blocks found, returns first max_blocks
        """
        if not text:
            return {"status": "complete", "blocks": []}

        names_set = set(character_names)
        pattern = r'\*\*([^*]+?):\*\*'
        matches = list(re.finditer(pattern, text))

        if not matches:
            return {"status": "complete", "blocks": [{"type": "narrative", "content": text.strip()}]}

        blocks = []
        last_end = 0

        for i, match in enumerate(matches):
            start = match.start()
            name = match.group(1).strip().lower()

            # Narrative before this tag
            if start > last_end:
                narrative_text = text[last_end:start].strip()
                if narrative_text:
                    blocks.append({"type": "narrative", "content": narrative_text})
                    if len(blocks) >= max_blocks:
                        return {"status": "limit_exceeded", "blocks": blocks}

            # Validate character name
            if name not in names_set:
                return {
                    "status": "invalid_character",
                    "character_name": name,
                    "at_position": start,
                    "text_before": text[:start].rstrip()   # everything before **
                }

            # Determine end of this character block
            if i + 1 < len(matches):
                end = matches[i+1].start()
            else:
                end = len(text)

            content = text[match.end():end].strip()
            blocks.append({"type": "character", "name": name, "content": content})
            if len(blocks) >= max_blocks:
                return {"status": "limit_exceeded", "blocks": blocks}

            last_end = end

        # Remaining text after last match
        if last_end < len(text):
            remaining = text[last_end:].strip()
            if remaining:
                blocks.append({"type": "narrative", "content": remaining})
                if len(blocks) >= max_blocks:
                    return {"status": "limit_exceeded", "blocks": blocks}

        return {"status": "complete", "blocks": blocks}

    def parse_character(
        self,
        text: str,
        character_name: str,
        character_names: List[str],
        stop_marker: str = "**narrative:**"
    ) -> Dict[str, Any]:
        """
        Parse character response.

        Args:
            text: raw LLM output (may be incomplete).
            character_name: name of the character currently speaking.
            character_names: list of existing character names (lowercase).
            stop_marker: string that indicates end of character speech.

        Returns:
            dict with status:
                - "complete": no stop marker, no other character tags
                - "stop_marker_found": stop marker encountered
                - "invalid_character": invalid character name appeared
                - "character_switch": valid other character appeared
        """
        if not text:
            return {"status": "complete", "content": ""}

        names_set = set(character_names)
        current_name_lower = character_name.lower()

        # 1. Check stop marker first
        marker_pos = text.find(stop_marker)
        if marker_pos != -1:
            trimmed = text[:marker_pos].rstrip()
            return {"status": "stop_marker_found", "content": trimmed}

        # 2. Check for character tags
        pattern = r'\*\*([^*]+?):\*\*'
        matches = list(re.finditer(pattern, text))

        for match in matches:
            other_name = match.group(1).strip().lower()
            if other_name != current_name_lower:
                if other_name not in names_set:
                    return {
                        "status": "invalid_character",
                        "character_name": other_name,
                        "at_position": match.start(),
                        "text_before": text[:match.start()].rstrip()
                    }
                return {
                    "status": "character_switch",
                    "new_character": other_name,
                    "text_before": text[:match.start()].rstrip()
                }

        # 3. No stop marker, no other characters
        return {"status": "complete", "content": text.strip()}