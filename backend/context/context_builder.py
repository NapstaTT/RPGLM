"""
ContextBuilder assembles raw data blocks for PromptsManager.
It does NOT apply macros – that is PromptsManager's responsibility.
"""

from typing import Dict, Any, Optional, List

from ..storage.lorebook_storage import LorebookStorage
from ..storage.timeline_storage import TimelineStorage
from ..utils.entry_activator import EntryActivator


class ContextBuilder:
    """
    Collects all context data and formats it into blocks for PromptsManager.
    """

    def __init__(
        self,
        lorebook_storage: LorebookStorage,
        timeline_storage: TimelineStorage,
        entry_activator: EntryActivator,
    ):
        self.lorebook = lorebook_storage
        self.timeline = timeline_storage
        self.entry_activator = entry_activator

    def _get_location_by_id(self, location_id: str) -> Optional[Dict[str, Any]]:
        """Return location dict or None."""
        locations = self.lorebook.get_collection("locations")
        for loc in locations:
            if loc.get("id") == location_id:
                return loc
        return None

    def _get_character_by_id(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Return character dict or None."""
        characters = self.lorebook.get_collection("characters")
        for char in characters:
            if char.get("id") == character_id:
                return char
        return None

    def _get_history_messages(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return last N non‑system messages."""
        all_msgs = self.timeline.get_sorted_history()
        # Filter out system messages
        filtered = [msg for msg in all_msgs if msg.get("role") != "system"]
        if limit > 0 and len(filtered) > limit:
            return filtered[-limit:]
        return filtered

    def _get_activated_entries(self, history_msgs: List[Dict[str, Any]]) -> str:
        """
        Get activated entries as a formatted string.
        """
        activated = self.entry_activator.activate(history_msgs)
        if not activated:
            return ""
        lines = []
        for entry in activated:
            title = entry.get("title", "Untitled")
            desc = entry.get("description", "")
            lines.append(f"**{title}:** {desc}")
        return "\n".join(lines)

    def build_prompt(
        self,
        prompt_type: str,
        world_state: Dict[str, Any],
        persona: Dict[str, Any],
        history_limit: int = 20,
        system_prompt: str = "",
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Build blocks dictionary for PromptsManager.

        Args:
            prompt_type: 'narrator', 'character', or 'permutation'
            world_state: dict with location_id, active_character_id, time_string
            persona: dict with name and description
            history_limit: number of recent messages to include
            system_prompt: main prompt text (from prompts_manager)
            extra_context: additional context for specific prompt types

        Returns:
            Dict[str, Dict[str, Any]] with keys:
                - system_prompt
                - user_persona
                - location_description
                - character_description
                - world_map
                - scenario
                - activated_entries
                - history
        """
        blocks = {}

        # 1. System prompt
        blocks["system_prompt"] = {"text": system_prompt, "context": {}}

        # 2. User persona
        user_name = persona.get("name", "User")
        user_desc = persona.get("description", "")
        blocks["user_persona"] = {
            "text": user_desc,
            "context": {"user": user_name},
        }

        # 3. Location description
        location_id = world_state.get("location_id")
        location_text = ""
        location_name = ""
        if location_id:
            loc = self._get_location_by_id(location_id)
            if loc:
                location_text = loc.get("description", "")
                location_name = loc.get("title", "")
        blocks["location_description"] = {
            "text": location_text,
            "context": {"location": location_name},
        }

        # 4. Character description
        char_id = world_state.get("active_character_id")
        char_text = ""
        char_name = ""
        if char_id:
            char = self._get_character_by_id(char_id)
            if char:
                char_text = char.get("description", "")
                char_name = char.get("name", "")
        blocks["character_description"] = {
            "text": char_text,
            "context": {"char": char_name},
        }

        # 5. World map (list of all locations)
        locations = self.lorebook.get_collection("locations")
        map_lines = []
        for loc in locations:
            title = loc.get("title", "Unnamed")
            loc_id = loc.get("id", "")
            map_lines.append(f"- {title} (id: {loc_id})")
        blocks["world_map"] = {"text": "\n".join(map_lines), "context": {}}

        # 6. Scenario (short summary)
        scenario_parts = []
        if location_name:
            scenario_parts.append(f"Location: {location_name}")
        if char_name:
            scenario_parts.append(f"Active character: {char_name}")
        time_str = world_state.get("time_string")
        if time_str:
            scenario_parts.append(f"Time: {time_str}")
        blocks["scenario"] = {"text": ". ".join(scenario_parts), "context": {}}

        # 7. Activated entries
        history_msgs = self._get_history_messages(history_limit)
        activated_text = self._get_activated_entries(history_msgs)
        blocks["activated_entries"] = {
            "text": activated_text,
            "context": {},
        }

        # 8. History (formatted)
        history_lines = []
        for msg in history_msgs:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "narrator":
                history_lines.append(content)
            else:
                history_lines.append(f"**{role}:** {content}")
        blocks["history"] = {
            "text": "\n".join(history_lines),
            "context": {"user": user_name, "char": char_name},
        }

        # 9. Extra context for specific prompt types
        if extra_context:
            for key, value in extra_context.items():
                if key not in blocks:
                    blocks[key] = {"text": str(value), "context": {}}

        return blocks