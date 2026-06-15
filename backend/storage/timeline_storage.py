import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, List


class StorageConfig:
    """Configuration class for managing world storage paths."""

    def __init__(self, base_data_dir: str = "data/worlds"):
        self.base_dir = Path(base_data_dir)

    def get_world_dir(self, world_id: str) -> Path:
        return self.base_dir / world_id

    def get_main_path(self, world_id: str) -> Path:
        return self.get_world_dir(world_id) / "timeline.jsonl"

    def get_tmp_path(self, world_id: str) -> Path:
        return self.get_world_dir(world_id) / "timeline.tmp.jsonl"

    def get_backup_dir(self, world_id: str) -> Path:
        return self.get_world_dir(world_id) / "backups"


class TimelineStorage:
    """Handles atomic storage operations and backup rotations for a specific world instance."""

    def __init__(self, world_id: str, config: StorageConfig):
        self.world_id = world_id
        self.config = config
        self._ensure_main_file()

    def _read_jsonl(self, file_path: Path) -> List[Dict[str, Any]]:
        """Helper method to safely read and parse JSONL files line by line."""
        if not file_path.exists():
            return []
        
        lines = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    lines.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"[Error] File {file_path}, line {line_num}: {e}")
                    continue
        return lines

    def _ensure_main_file(self) -> None:
        """Guarantees the existence of the main timeline file or restores it from backups."""
        main_path = self.config.get_main_path(self.world_id)
        if main_path.exists():
            return

        backup_dir = self.config.get_backup_dir(self.world_id)
        backups = sorted(backup_dir.glob("timeline_*.jsonl"))
        
        if backups:
            latest_backup = backups[-1]
            main_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(latest_backup, main_path)
            print(f"[Storage] Restored main timeline from backup: {latest_backup}")
            return

    def read_main(self) -> List[Dict[str, Any]]:
        """Read all messages from the main persistent storage."""
        return self._read_jsonl(self.config.get_main_path(self.world_id))

    def read_tmp(self) -> List[Dict[str, Any]]:
        """Read all messages from the temporary write buffer."""
        return self._read_jsonl(self.config.get_tmp_path(self.world_id))

    def append_to_tmp(self, message: Dict[str, Any], world_state: Optional[Dict] = None) -> None:
        """Append a new message to the temporary transaction log file."""
        tmp_path = self.config.get_tmp_path(self.world_id)
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        if world_state:
            message["world_state"] = world_state.copy()
        with open(tmp_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(message, ensure_ascii=False) + "\n")
            f.flush()

    def clear_tmp(self) -> None:
        """Safely delete the temporary buffer file."""
        tmp_path = self.config.get_tmp_path(self.world_id)
        if tmp_path.exists():
            tmp_path.unlink()

    def atomic_save_main(self, messages: List[Dict[str, Any]]) -> None:
        """Overwrite the main file atomically using a temporary clone to prevent data corruption."""
        main_path = self.config.get_main_path(self.world_id)
        main_path.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_file_path = tempfile.mkstemp(
            dir=main_path.parent, prefix="timeline_tmp_", suffix=".jsonl"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for msg in messages:
                    f.write(json.dumps(msg, ensure_ascii=False) + "\n")
            os.replace(tmp_file_path, main_path)
        except Exception:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
            raise

    def create_backup(self) -> None:
        """Create a timed snapshot backup of the main file (retains up to 10 files)."""
        main_path = self.config.get_main_path(self.world_id)
        if not main_path.exists():
            return

        backup_dir = self.config.get_backup_dir(self.world_id)
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        backup_path = backup_dir / f"timeline_{timestamp}.jsonl"
        shutil.copy2(main_path, backup_path)

        # Rotate old backups
        backups = sorted(backup_dir.glob("timeline_*.jsonl"))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                old_backup.unlink()

    def get_sorted_history(self) -> List[Dict[str, Any]]:
        """DRY Principle: Merges main and tmp buffers, removes duplicates by version, and sorts entries."""
        main_msgs = self.read_main()
        tmp_msgs = self.read_tmp()

        combined = {msg["ver"]: msg for msg in main_msgs}
        for msg in tmp_msgs:
            combined[msg["ver"]] = msg

        return [combined[v] for v in sorted(combined.keys())]

    def flush_tmp_to_main(self) -> None:
        """Commit temporary transactions into the main timeline file."""
        tmp_msgs = self.read_tmp()
        if not tmp_msgs:
            return

        sorted_all = self.get_sorted_history()
        self.create_backup()
        self.atomic_save_main(sorted_all)
        self.clear_tmp()
        print(f"[Storage] World '{self.world_id}': successfully flushed {len(tmp_msgs)} messages.")

    def recover_if_needed(self) -> None:
        """Crash recovery procedure executed at server startup."""
        if self.read_tmp():
            print(f"[Storage] Unsaved logs detected for world '{self.world_id}'. Running recovery...")
            self.flush_tmp_to_main()

