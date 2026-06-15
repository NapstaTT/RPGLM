# backend/storage/persona_storage.py
"""Persona storage with atomic writes and backups."""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any


class PersonaStorage:
    """Handles persistent storage of user persona data."""

    DEFAULT_PERSONA = {
        "name": "Player",
        "description": "",
        "avatar": None,
    }

    def __init__(self, world_id: str, base_data_dir: str = "data/worlds"):
        """
        Initialize persona storage for a world.

        Args:
            world_id: World identifier.
            base_data_dir: Base data directory.
        """
        self.world_dir = Path(base_data_dir) / world_id
        self.persona_path = self.world_dir / "persona.json"
        self.backup_dir = self.world_dir / "persona_backups"
        self._ensure_exists()

    def _ensure_exists(self) -> None:
        """Create default persona file if missing."""
        if not self.persona_path.exists():
            self.world_dir.mkdir(parents=True, exist_ok=True)
            self._save_atomic(self.DEFAULT_PERSONA)

    def _save_atomic(self, data: Dict[str, Any]) -> None:
        """Atomically write persona.json."""
        self.world_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=self.world_dir, prefix="persona_tmp_", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.persona_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def _create_backup(self) -> None:
        """Create a backup before writing (keep up to 2 backups)."""
        if not self.persona_path.exists():
            return
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"persona_{timestamp}.json"
        shutil.copy2(self.persona_path, backup_path)
        # Keep only last 2
        backups = sorted(self.backup_dir.glob("persona_*.json"))
        if len(backups) > 2:
            for old in backups[:-2]:
                old.unlink()

    def get(self) -> Dict[str, Any]:
        """Return current persona data."""
        try:
            with open(self.persona_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return self.DEFAULT_PERSONA.copy()

    def update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update persona (validates and saves)."""
        # Validate
        if "name" in data and not data["name"].strip():
            raise ValueError("Name cannot be empty")
        # Merge with existing
        current = self.get()
        current.update(data)
        if "name" in current:
            current["name"] = current["name"].strip()
        # Save with backup
        self._create_backup()
        self._save_atomic(current)
        return current

    def shutdown(self) -> None:
        """No-op for compatibility."""
        pass