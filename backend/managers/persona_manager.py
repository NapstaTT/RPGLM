# backend/managers/persona_manager.py
"""Persona manager for user persona data."""

from typing import Dict, Any
from ..storage.persona_storage import PersonaStorage


class PersonaManager:
    """High-level manager for user persona."""

    def __init__(self, world_id: str):
        """Initialize with the given world ID."""
        self._storage = PersonaStorage(world_id)

    async def get_persona(self) -> Dict[str, Any]:
        """Return current persona."""
        return self._storage.get()

    async def update_persona(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update persona with validation."""
        return self._storage.update(data)