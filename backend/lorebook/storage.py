"""
Low-level file storage for lorebook.json with atomic writes, backups, and versioning.
"""

import asyncio
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class LorebookConfig:
    def __init__(self, base_data_dir: str = "data/worlds"):
        self.base_dir = Path(base_data_dir)

    def get_world_dir(self, world_id: str) -> Path:
        return self.base_dir / world_id

    def get_main_path(self, world_id: str) -> Path:
        return self.get_world_dir(world_id) / "lorebook.json"

    def get_backup_dir(self, world_id: str) -> Path:
        return self.get_world_dir(world_id) / "lorebook_backups"


class LorebookStorage:
    """
    Handles persistent storage of lorebook data.
    Provides methods to get/set collections, atomic saving with delay, backups.
    """

    DEFAULT_DATA = {
        "version": 1,
        "locations": [
            {
                "id": "system_locations",
                "title": "System Locations Index",
                "description": "Auto-generated list of all locations (editable).",
                "state": "always_active",
                "keywords": [],
                "logic": "ANY",
                "chance": 100,
                "depth": 0,
                "position": 0,
                "parent_id": None,
                "is_leaf": False,
                "characters_on_location": [],
                "undeletable": True,
            }
        ],
        "characters": [],
        "entries": [],
    }

    def __init__(self, world_id: str, config: Optional[LorebookConfig] = None):
        self.world_id = world_id
        self.config = config or LorebookConfig()
        self._data: Dict[str, Any] = {}
        self._data_lock = asyncio.Lock()
        self._save_task: Optional[asyncio.Task] = None
        self._dirty = False
        self._load()

    def _load(self) -> None:
        """Load lorebook.json, create default if missing, handle corruption."""
        main_path = self.config.get_main_path(self.world_id)
        if not main_path.exists():
            self._data = self.DEFAULT_DATA.copy()
            self._save_atomic(self._data)
            return

        try:
            with open(main_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[Lorebook] Error loading {main_path}: {e}. Trying backup...")
            self._restore_from_backup()
            return

        if loaded.get("version", 0) != self.DEFAULT_DATA["version"]:
            print(f"[Lorebook] Version mismatch: {loaded.get('version')} -> {self.DEFAULT_DATA['version']}. Migrating.")
            loaded = self._migrate(loaded)

        self._data = loaded

    def _restore_from_backup(self) -> None:
        backup_dir = self.config.get_backup_dir(self.world_id)
        backups = sorted(backup_dir.glob("lorebook_*.json"), reverse=True)
        if backups:
            shutil.copy2(backups[0], self.config.get_main_path(self.world_id))
            print(f"[Lorebook] Restored from {backups[0]}")
            self._load()
        else:
            print("[Lorebook] No backup found, creating default.")
            self._data = self.DEFAULT_DATA.copy()
            self._save_atomic(self._data)

    def _migrate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        for key in ["locations", "characters", "entries"]:
            if key not in data:
                data[key] = []
        sys_exists = any(loc.get("id") == "system_locations" for loc in data["locations"])
        if not sys_exists:
            data["locations"].insert(0, self.DEFAULT_DATA["locations"][0])
        data["version"] = 1
        return data

    def _backup(self) -> None:
        main_path = self.config.get_main_path(self.world_id)
        if not main_path.exists():
            return
        backup_dir = self.config.get_backup_dir(self.world_id)
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"lorebook_{timestamp}.json"
        shutil.copy2(main_path, backup_path)
        # Keep only last 5
        backups = sorted(backup_dir.glob("lorebook_*.json"))
        if len(backups) > 5:
            for old in backups[:-5]:
                old.unlink()

    def _save_atomic(self, data: Dict[str, Any]) -> None:
        main_path = self.config.get_main_path(self.world_id)
        main_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=main_path.parent, prefix="lorebook_tmp_", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, main_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    async def _do_save(self) -> None:
        async with self._data_lock:
            self._backup()
            self._save_atomic(self._data)
            self._dirty = False

    async def _delayed_save(self) -> None:
        await asyncio.sleep(3)
        if self._dirty:
            await self._do_save()

    def _schedule_save(self) -> None:
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
        self._dirty = True
        self._save_task = asyncio.create_task(self._delayed_save())

    async def shutdown(self) -> None:
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
        if self._dirty:
            await self._do_save()

    # Public accessors for collections (for managers)
    def get_collection(self, entity_type: str) -> List[Dict]:
        """Return a reference to the collection list (internal use only)."""
        if entity_type not in self._data:
            self._data[entity_type] = []
        return self._data[entity_type]

    def set_collection(self, entity_type: str, collection: List[Dict]) -> None:
        """Replace entire collection (used by managers)."""
        self._data[entity_type] = collection