"""Prompts storage with atomic writes and defaults."""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any


class PromptsStorage:
    """Storage for prompt templates and main prompts."""

    def __init__(self, world_id: str, base_data_dir: str = "data/worlds", defaults_path: str = None):
        """
        Initialize prompts storage.

        Args:
            world_id: World identifier.
            base_data_dir: Base data directory.
            defaults_path: Path to default prompts JSON file.
        """
        self.world_dir = Path(base_data_dir) / world_id
        self.prompts_file = self.world_dir / "prompts.json"
        self.backup_dir = self.world_dir / "prompts_backups"
        self.defaults_path = defaults_path or (Path(__file__).parent.parent / "prompts" / "default_prompts.json")
        self._ensure_exists()

    def _ensure_exists(self) -> None:
        """Create default prompts file if missing."""
        if not self.prompts_file.exists():
            self.world_dir.mkdir(parents=True, exist_ok=True)
            default_data = self._load_defaults()
            self._save_atomic(default_data)

    def _load_defaults(self) -> Dict:
        """Load default prompts from file or fallback."""
        if self.defaults_path.exists():
            with open(self.defaults_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # Built-in defaults (in case file is missing)
            return {
                "version": 1,
                "templates": {
                    "narrator": "{{#if system_prompt}}{{system_prompt}}\n{{/if}}{{#if user_persona}}User persona: {{user_persona}}\n{{/if}}{{#if character_description}}Active character: {{character_description}}\n{{/if}}{{#if location_description}}Location: {{location_description}}\n{{/if}}{{#if world_map}}Known locations: {{world_map}}\n{{/if}}{{#if scenario}}Scenario: {{scenario}}\n{{/if}}{{#if history}}Conversation history:\n{{history}}{{/if}}",
                    "character": "{{#if character_description}}{{character_description}}\n{{/if}}{{#if scenario}}Scenario: {{scenario}}\n{{/if}}",
                    "permutation": "{{#if instruction}}{{instruction}}\n{{/if}}{{#if text}}{{text}}{{/if}}"
                },
                "prompts": {
                    "narrator": "You are the game master. Describe the world, NPCs, and events vividly. Do not speak for the user. Stay in character.",
                    "character": "Stay in character. Respond as the character. Do not narrate for the user. Be creative.",
                    "permutation": "Rewrite the following text in a different style while preserving its meaning."
                }
            }

    def _save_atomic(self, data: Dict) -> None:
        """Atomically write prompts.json."""
        fd, tmp_path = tempfile.mkstemp(dir=self.world_dir, prefix="prompts_tmp_", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.prompts_file)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def _create_backup(self) -> None:
        """Create a backup of the current prompts file (keep last 2)."""
        if not self.prompts_file.exists():
            return
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"prompts_{timestamp}.json"
        shutil.copy2(self.prompts_file, backup_path)
        # keep last 2
        backups = sorted(self.backup_dir.glob("prompts_*.json"))
        if len(backups) > 2:
            for old in backups[:-2]:
                old.unlink()

    def _load(self) -> Dict:
        """Load prompts data from file."""
        try:
            with open(self.prompts_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return self._load_defaults()

    def get_templates(self) -> Dict:
        """Return all templates."""
        return self._load().get("templates", {})

    def get_prompts(self) -> Dict:
        """Return all main prompts."""
        return self._load().get("prompts", {})

    def get_template(self, prompt_type: str) -> str:
        """Return a specific template by type."""
        return self.get_templates().get(prompt_type, "")

    def get_prompt(self, prompt_type: str) -> str:
        """Return a specific main prompt by type."""
        return self.get_prompts().get(prompt_type, "")

    def update_templates(self, templates: Dict) -> None:
        """Update the templates section."""
        data = self._load()
        data["templates"] = templates
        self._create_backup()
        self._save_atomic(data)

    def update_prompts(self, prompts: Dict) -> None:
        """Update the main prompts section."""
        data = self._load()
        data["prompts"] = prompts
        self._create_backup()
        self._save_atomic(data)

    def save(self) -> None:
        """Compatibility method – does nothing."""
        pass