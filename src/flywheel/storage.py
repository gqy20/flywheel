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

    DEFAULT_BACKUP_LIMIT = 3

    def __init__(self, path: str | None = None, backup_limit: int | None = None) -> None:
        self.path = Path(path or ".todo.json")
        self.backup_limit = backup_limit if backup_limit is not None else self.DEFAULT_BACKUP_LIMIT

    def load(self, use_backup: bool = False) -> list[Todo]:
        """Load todos from file.

        Args:
            use_backup: If True and main file is corrupted, attempt to load from backup.

        Returns:
            List of Todo objects.
        """
        if not self.path.exists():
            # Try backup if use_backup is enabled
            if use_backup:
                backup_path = self._get_backup_path()
                if backup_path.exists():
                    return self._load_from_path(backup_path)
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
            if use_backup:
                backup_path = self._get_backup_path()
                if backup_path.exists():
                    return self._load_from_path(backup_path)
            raise ValueError(
                f"Invalid JSON in '{self.path}': {e.msg}. "
                f"Check line {e.lineno}, column {e.colno}."
            ) from e

        if not isinstance(raw, list):
            raise ValueError("Todo storage must be a JSON list")
        return [Todo.from_dict(item) for item in raw]

    def save(self, todos: list[Todo], backup_limit: int | None = None) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Args:
            todos: List of Todo objects to save.
            backup_limit: Optional override for number of backups to keep.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

        # Create backup before overwriting existing file
        if self.path.exists():
            self._backup(backup_limit)

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

    def _get_backup_path(self, index: int = 0) -> Path:
        """Get backup file path for given index.

        Args:
            index: Backup index (0 for .bak, 1 for .bak.1, etc.)

        Returns:
            Path to backup file.
        """
        if index == 0:
            return self.path.parent / f"{self.path.name}.bak"
        return self.path.parent / f"{self.path.name}.bak.{index}"

    def _backup(self, backup_limit: int | None = None) -> None:
        """Create rotating backup of current file.

        Rotates existing backups and enforces the backup limit.

        Args:
            backup_limit: Optional override for number of backups to keep.
        """
        limit = backup_limit if backup_limit is not None else self.backup_limit

        # Rotate existing backups: .bak.N -> .bak.N+1
        # Start from the limit-1 and go backwards to avoid overwriting
        for i in range(limit - 1, 0, -1):
            old_backup = self._get_backup_path(i)
            new_backup = self._get_backup_path(i + 1)
            if old_backup.exists():
                shutil.copy2(old_backup, new_backup)

        # Move .bak to .bak.1
        backup_path = self._get_backup_path(0)
        backup_1 = self._get_backup_path(1)
        if backup_path.exists():
            shutil.copy2(backup_path, backup_1)

        # Copy current file to .bak
        shutil.copy2(self.path, backup_path)

        # Remove backups exceeding the limit
        # .bak.N where N >= limit should be removed
        for i in range(limit, limit + 10):  # Check a reasonable range
            old_backup = self._get_backup_path(i)
            if old_backup.exists():
                old_backup.unlink()
            else:
                break

    def _load_from_path(self, file_path: Path) -> list[Todo]:
        """Load todos from a specific file path.

        Args:
            file_path: Path to load from.

        Returns:
            List of Todo objects.
        """
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
