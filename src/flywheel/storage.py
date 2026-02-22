"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path

from .todo import Todo

# Maximum JSON file size to prevent DoS attacks (10MB)
_MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024

# Default number of backups to keep
_DEFAULT_MAX_BACKUPS = 3


def _ensure_parent_directory(file_path: Path) -> None:
    """Safely ensure parent directory exists for file_path.

    Validates that:
    1. All parent path components either don't exist or are directories (not files)
    2. Creates parent directories if needed
    3. Provides clear error messages for permission issues

    Raises:
        ValueError: If any parent path component exists but is a file
        OSError: If directory creation fails due to permissions
    """
    parent = file_path.parent

    # Check all parent components (excluding the file itself) for file-as-directory confusion
    # This handles cases like: /path/to/file.json/subdir/db.json
    # where 'file.json' exists as a file but we need it to be a directory
    for part in list(file_path.parents):  # Only check parents, not file_path itself
        if part.exists() and not part.is_dir():
            raise ValueError(
                f"Path error: '{part}' exists as a file, not a directory. "
                f"Cannot use '{file_path}' as database path."
            )

    # Create parent directory if it doesn't exist
    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=False)  # exist_ok=False since we validated above
        except OSError as e:
            raise OSError(
                f"Failed to create directory '{parent}': {e}. "
                f"Check permissions or specify a different location with --db=path/to/db.json"
            ) from e


class TodoStorage:
    """Persistent storage for todos."""

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or ".todo.json")

    def load(self) -> list[Todo]:
        if not self.path.exists():
            return []

        # Security: Check file size before loading to prevent DoS
        file_size = self.path.stat().st_size
        if file_size > _MAX_JSON_SIZE_BYTES:
            size_mb = file_size / (1024 * 1024)
            limit_mb = _MAX_JSON_SIZE_BYTES / (1024 * 1024)
            raise ValueError(
                f"JSON file too large ({size_mb:.1f}MB > {limit_mb:.0f}MB limit). "
                f"This protects against denial-of-service attacks."
            )

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in '{self.path}': {e.msg}. Check line {e.lineno}, column {e.colno}."
            ) from e

        if not isinstance(raw, list):
            raise ValueError("Todo storage must be a JSON list")
        return [Todo.from_dict(item) for item in raw]

    def save(
        self,
        todos: list[Todo],
        *,
        backup_before_save: bool = False,
        max_backups: int = _DEFAULT_MAX_BACKUPS,
    ) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.

        Args:
            todos: List of Todo objects to save.
            backup_before_save: If True, create a backup before overwriting.
            max_backups: Maximum number of backup files to keep (default 3).
        """
        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

        # Create backup before save if enabled and file exists
        if backup_before_save and self.path.exists():
            self._create_backup(max_backups)

        payload = [todo.to_dict() for todo in todos]
        content = json.dumps(payload, ensure_ascii=False, indent=2)

        # Create temp file in same directory as target for atomic rename
        # Use tempfile.mkstemp for unpredictable name and O_EXCL semantics
        fd, temp_path = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            text=False,  # We'll write binary data to control encoding
        )

        try:
            # Set restrictive permissions (owner read/write only)
            # This protects against other users reading temp file before rename
            os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)  # 0o600 (rw-------)

            # Write content with proper encoding
            # Use os.write instead of Path.write_text for more control
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)

            # Atomic rename (os.replace is atomic on both Unix and Windows)
            os.replace(temp_path, self.path)
        except OSError:
            # Clean up temp file on error
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
            raise

    def _get_backup_paths(self) -> list[Path]:
        """Get all backup file paths sorted by modification time (newest first)."""
        # Pattern: <filename>.bak.<n> where n is 0, 1, 2, ...
        pattern = re.compile(rf"^{re.escape(self.path.name)}\.bak(?:\.\d+)?$")
        backup_files = []

        if self.path.parent.exists():
            for f in self.path.parent.iterdir():
                if pattern.match(f.name):
                    backup_files.append(f)

        # Sort by modification time, newest first
        backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return backup_files

    def _create_backup(self, max_backups: int) -> None:
        """Create a backup of the current file and rotate old backups.

        Args:
            max_backups: Maximum number of backup files to keep.
        """
        # Get existing backups
        existing_backups = self._get_backup_paths()

        # Determine the new backup path
        if existing_backups:
            # Find the highest index
            highest_idx = 0
            for backup in existing_backups:
                match = re.search(r"\.bak\.(\d+)$", backup.name)
                if match:
                    idx = int(match.group(1))
                    highest_idx = max(highest_idx, idx)
            new_backup_path = self.path.with_suffix(f"{self.path.suffix}.bak.{highest_idx + 1}")
        else:
            # First backup uses .bak.0
            new_backup_path = self.path.with_suffix(f"{self.path.suffix}.bak.0")

        # Copy current file to new backup
        import shutil

        shutil.copy2(self.path, new_backup_path)

        # Rotate: delete oldest backups if we exceed max_backups
        all_backups = self._get_backup_paths()
        while len(all_backups) > max_backups:
            all_backups[-1].unlink()
            all_backups = self._get_backup_paths()

    def load_backup(self, n: int = 0) -> list[Todo]:
        """Load todos from the nth most recent backup.

        Args:
            n: Which backup to load (0 = most recent, 1 = second most recent, etc.)

        Returns:
            List of Todo objects from the backup.

        Raises:
            FileNotFoundError: If no backup file exists or n is too large.
        """
        backups = self._get_backup_paths()

        if not backups:
            raise FileNotFoundError(f"No backup file found for {self.path}")

        if n >= len(backups):
            raise FileNotFoundError(
                f"Backup #{n} not found. Only {len(backups)} backup(s) available."
            )

        backup_path = backups[n]

        # Reuse load logic by temporarily replacing path
        original_path = self.path
        try:
            self.path = backup_path
            return self.load()
        finally:
            self.path = original_path

    def restore_backup(self, n: int = 0) -> None:
        """Restore the database from the nth most recent backup.

        Args:
            n: Which backup to restore (0 = most recent, 1 = second most recent, etc.)

        Raises:
            FileNotFoundError: If no backup file exists or n is too large.
        """
        backups = self._get_backup_paths()

        if not backups:
            raise FileNotFoundError(f"No backup file found for {self.path}")

        if n >= len(backups):
            raise FileNotFoundError(
                f"Backup #{n} not found. Only {len(backups)} backup(s) available."
            )

        backup_path = backups[n]

        # Copy backup to main file
        import shutil

        shutil.copy2(backup_path, self.path)

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
