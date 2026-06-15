# backend/utils/world_state.py
"""Helper functions for world state handling."""

from typing import Dict, Optional

def get_empty_world_state() -> Dict[str, Optional[str]]:
    """Return an empty world state dict with default None values."""
    return {
        "location_id": None,
        "active_character_id": None,
        "time_string": None,
    }

def get_last_world_state(timeline_storage) -> Dict:
    """Extract world state from last message in history, or empty if none."""
    history = timeline_storage.get_sorted_history()
    if not history:
        return get_empty_world_state()
    last_msg = history[-1]
    return last_msg.get("world_state", get_empty_world_state())