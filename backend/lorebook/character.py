"""Manager for character entities. Characters use 'name' instead of 'title'."""

from typing import Dict
from .base import BaseLorebookManager
from .storage import LorebookStorage


class CharacterManager(BaseLorebookManager):
    """Manages character entities."""

    def __init__(self, storage: LorebookStorage):
        super().__init__(storage, "characters")

    def validate_create(self, data: Dict) -> None:
        """Ensure character name is non-empty."""
        if not data.get("name", "").strip():
            raise ValueError("Character name cannot be empty")

    def before_delete(self, entity: Dict) -> None:
        """Remove this character from all locations' characters_on_location lists."""
        char_id = entity["id"]
        locations = self._get_locations_collection()
        for loc in locations:
            if char_id in loc.get("characters_on_location", []):
                loc["characters_on_location"].remove(char_id)