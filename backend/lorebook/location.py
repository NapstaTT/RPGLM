"""Manager for location entities."""

from typing import Dict, List
from .base import BaseLorebookManager
from .storage import LorebookStorage


class LocationManager(BaseLorebookManager):
    """Manages location entities with hierarchical parent-child relationship."""

    def __init__(self, storage: LorebookStorage):
        super().__init__(storage, "locations")

    def validate_create(self, data: Dict) -> None:
        """Ensure parent_id refers to an existing location if provided."""
        parent_id = data.get("parent_id")
        if parent_id:
            locations = self._get_locations_collection()
            if not any(loc["id"] == parent_id for loc in locations):
                raise ValueError(f"Parent location {parent_id} does not exist")

    def before_delete(self, entity: Dict) -> None:
        """Cascade: clear parent_id in child locations and entries."""
        loc_id = entity["id"]
        # Child locations
        locations = self._get_locations_collection()
        for loc in locations:
            if loc.get("parent_id") == loc_id:
                loc["parent_id"] = None
        # Entries referencing this location
        entries = self._get_entries_collection()
        for entry in entries:
            if entry.get("parent_id") == loc_id:
                entry["parent_id"] = None


async def add_character_to_location(self, location_id: str, character_id: str) -> None:
    """Add a character to a location's list."""
    async with self._storage._data_lock:
        locations = self._get_collection()
        for loc in locations:
            if loc["id"] == location_id:
                if "characters_on_location" not in loc:
                    loc["characters_on_location"] = []
                if character_id not in loc["characters_on_location"]:
                    loc["characters_on_location"].append(character_id)
                    self._storage._schedule_save()
                return
        raise ValueError(f"Location {location_id} not found")


async def remove_character_from_location(self, location_id: str, character_id: str) -> None:
    """Remove a character from a location's list."""
    async with self._storage._data_lock:
        locations = self._get_collection()
        for loc in locations:
            if loc["id"] == location_id:
                if character_id in loc.get("characters_on_location", []):
                    loc["characters_on_location"].remove(character_id)
                    self._storage._schedule_save()
                return
        raise ValueError(f"Location {location_id} not found")