from __future__ import annotations

import uuid
from abc import ABC
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..storage.lorebook_storage import LorebookStorage


class BaseLorebookManager(ABC):
    """Abstract base manager for lorebook entities (locations, characters, entries)."""

    def __init__(self, storage: 'LorebookStorage', entity_type: str):
        """Initialize the manager.

        Args:
            storage: The storage instance to persist data.
            entity_type: One of 'locations', 'characters', 'entries'.
        """
        self._storage = storage
        self._entity_type = entity_type

    @property
    def entity_type(self) -> str:
        """Return the entity type handled by this manager."""
        return self._entity_type

    def _get_collection(self) -> List[Dict]:
        """Return the raw collection list (internal use only)."""
        return self._storage.get_collection(self._entity_type)

    def _set_collection(self, coll: List[Dict]) -> None:
        """Replace the entire collection (internal use only)."""
        self._storage.set_collection(self._entity_type, coll)

    async def get_all(self) -> List[Dict]:
        """Return a copy of all entities of this type."""
        async with self._storage._data_lock:
            return [item.copy() for item in self._get_collection()]

    async def get_by_id(self, entity_id: str) -> Optional[Dict]:
        """Return a copy of the entity with the given ID, or None."""
        async with self._storage._data_lock:
            for item in self._get_collection():
                if item.get("id") == entity_id:
                    return item.copy()
        return None

    async def create(self, data: Dict) -> Dict:
        """Create a new entity.

        Args:
            data: The entity data (must not contain 'id').

        Returns:
            The created entity with assigned 'id' and 'position'.
        """
        async with self._storage._data_lock:
            coll = self._get_collection()
            self.validate_create(data)
            new_id = str(uuid.uuid4())
            max_pos = max((item.get("position", 0) for item in coll), default=0)
            new_item = {
                "id": new_id,
                **data,
                "position": max_pos + 100,
                "undeletable": False,
            }
            coll.append(new_item)
            self._storage._schedule_save()
            return new_item.copy()

    async def update(self, entity_id: str, data: Dict) -> Dict:
        """Update an existing entity.

        Args:
            entity_id: ID of the entity to update.
            data: Partial data to merge.

        Returns:
            The updated entity.
        """
        async with self._storage._data_lock:
            coll = self._get_collection()
            for idx, item in enumerate(coll):
                if item["id"] == entity_id:
                    if item.get("undeletable") and data.get("undeletable") is False:
                        raise ValueError("Cannot remove undeletable flag")
                    updated = {**item, **data}
                    updated["id"] = entity_id
                    if item.get("undeletable"):
                        updated["undeletable"] = True
                    self.validate_update(updated)
                    coll[idx] = updated
                    self._storage._schedule_save()
                    return updated.copy()
            raise ValueError(f"{self._entity_type} with id {entity_id} not found")

    async def delete(self, entity_id: str) -> None:
        """Delete an entity by ID.

        Args:
            entity_id: ID of the entity to delete.

        Raises:
            ValueError: If the entity is undeletable or not found.
        """
        async with self._storage._data_lock:
            coll = self._get_collection()
            for idx, item in enumerate(coll):
                if item["id"] == entity_id:
                    if item.get("undeletable"):
                        raise ValueError(
                            f"Cannot delete undeletable {self._entity_type} {entity_id}"
                        )
                    self.before_delete(item)
                    del coll[idx]
                    self._storage._schedule_save()
                    return
            raise ValueError(f"{self._entity_type} with id {entity_id} not found")

    # Hooks (synchronous, do not acquire locks)
    def validate_create(self, data: Dict) -> None:
        """Validate data before creation. Override in subclasses."""
        pass

    def validate_update(self, data: Dict) -> None:
        """Validate data before update. Override in subclasses."""
        self.validate_create(data)

    def before_delete(self, entity: Dict) -> None:
        """Perform cleanup before deletion. Override in subclasses."""
        pass

    # Helpers for accessing other collections (read-only)
    def _get_locations_collection(self) -> List[Dict]:
        return self._storage.get_collection("locations")

    def _get_characters_collection(self) -> List[Dict]:
        return self._storage.get_collection("characters")

    def _get_entries_collection(self) -> List[Dict]:
        return self._storage.get_collection("entries")