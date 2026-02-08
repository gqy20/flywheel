"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path

from .todo import Todo

# Maximum JSON file size to prevent DoS attacks (10MB)
_MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024


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

    def __init__(self, path: str | None = None, backup_limit: int = 3) -> None:
        self.path = Path(path or ".todo.json")
        self.backup_limit = backup_limit

    def load(self, use_backup: bool = False) -> list[Todo]:
        """Load todos from file, with optional fallback to backup.

        Args:
            use_backup: If True, fall back to most recent backup when main file is corrupted.

        Returns:
            List of Todo objects.

        Raises:
            ValueError: If file is corrupted and no backup is available.
        """
        try:
            return self._load_from_path(self.path)
        except (ValueError, json.JSONDecodeError, OSError):
            if use_backup:
                backup_path = self._get_backup_path(0)
                if backup_path.exists():
                    return self._load_from_path(backup_path)
            raise

    def _load_from_path(self, file_path: Path) -> list[Todo]:
        """Load todos from a specific file path."""
        if not file_path.exists():
            return []

        # Security: Check file size before loading to prevent DoS
        file_size = file_path.stat().st_size
        if file_size > _MAX_JSON_SIZE_BYTES:
            size_mb = file_size / (1024 * 1024)
            limit_mb = _MAX_JSON_SIZE_BYTES / (1024 * 1024)
            raise ValueError(
                f"JSON file too large ({size_mb:.1f}MB > {limit_mb:.0f}MB limit). "
                f"This protects against denial-of-service attacks."
            )

        try:
            raw = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in '{file_path}': {e.msg}. "
                f"Check line {e.lineno}, column {e.colno}."
            ) from e

        if not isinstance(raw, list):
            raise ValueError("Todo storage must be a JSON list")
        return [Todo.from_dict(item) for item in raw]

    def _get_backup_path(self, index: int) -> Path:
        """Get backup file path for given index.

        Args:
            index: 0 for most recent backup, 1 for second most recent, etc.

        Returns:
            Path to backup file.
        """
        if index == 0:
            return self.path.with_suffix(self.path.suffix + ".bak")
        return self.path.with_suffix(f"{self.path.suffix}.bak.{index}")

    def _rotate_backups(self) -> None:
        """Rotate existing backups to make room for new backup.

        Implements a rotation scheme where:
        - .bak is the most recent backup
        - .bak.1 is the second most recent
        - .bak.2 is the third most recent
        - etc.

        When backup_limit is exceeded, the oldest backup is deleted.
        """
        # Rotate existing backups: .bak.N -> .bak.N+1
        for i in range(self.backup_limit - 1, 0, -1):
            old_backup = self._get_backup_path(i - 1)
            new_backup = self._get_backup_path(i)
            if old_backup.exists():
                shutil.copy2(old_backup, new_backup)

        # Delete the oldest backup if we've exceeded the limit
        oldest_backup = self._get_backup_path(self.backup_limit)
        if oldest_backup.exists():
            oldest_backup.unlink()

    def _backup(self) -> None:
        """Create backup of current file before save.

        Copies the current file to a backup location and rotates
        existing backups to stay within backup_limit.
        """
        if not self.path.exists():
            return

        # Rotate existing backups first
        self._rotate_backups()

        # Copy current file to primary backup location
        backup_path = self._get_backup_path(0)
        shutil.copy2(self.path, backup_path)

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        # Create backup of current file before overwriting
        self._backup()

        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

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

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
