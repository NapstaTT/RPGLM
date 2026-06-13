"""Manager for generic lore entries."""

from typing import Dict
from .base import BaseLorebookManager
from .storage import LorebookStorage


class EntryManager(BaseLorebookManager):
    """Manages lore entry entities."""

    def __init__(self, storage: LorebookStorage):
        super().__init__(storage, "entries")

    def validate_create(self, data: Dict) -> None:
        """Ensure parent_id refers to an existing location if provided."""
        parent_id = data.get("parent_id")
        if parent_id:
            locations = self._get_locations_collection()
            if not any(loc["id"] == parent_id for loc in locations):
                raise ValueError(f"Parent location {parent_id} does not exist")