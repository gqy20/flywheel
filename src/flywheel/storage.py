"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import stat
import tempfile
import time
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
    """Persistent storage for todos with optional backup support."""

    def __init__(
        self,
        path: str | None = None,
        backup_before_save: bool = False,
        max_backups: int = 3,
    ) -> None:
        self.path = Path(path or ".todo.json")
        self.backup_before_save = backup_before_save
        self.max_backups = max_backups

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
                f"Invalid JSON in '{self.path}': {e.msg}. "
                f"Check line {e.lineno}, column {e.colno}."
            ) from e

        if not isinstance(raw, list):
            raise ValueError("Todo storage must be a JSON list")
        return [Todo.from_dict(item) for item in raw]

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.

        If backup_before_save is enabled, creates a timestamped backup of the
        existing file before overwriting, and rotates old backups.
        """
        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

        # Create backup before save if enabled and file exists
        if self.backup_before_save and self.path.exists():
            self._create_backup()

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

    def _create_backup(self) -> None:
        """Create a timestamped backup of the current file and rotate old backups."""
        timestamp = int(time.time() * 1000000)  # Microsecond precision for uniqueness
        backup_path = self.path.parent / f"{self.path.name}.bak.{timestamp}"

        # Copy current file to backup (atomic read + write)
        current_content = self.path.read_bytes()
        backup_path.write_bytes(current_content)

        # Rotate backups if max_backups > 0
        if self.max_backups > 0:
            self._rotate_backups()

    def _rotate_backups(self) -> None:
        """Remove oldest backups if count exceeds max_backups."""
        backup_pattern = f"{self.path.name}.bak.*"
        backups = sorted(
            self.path.parent.glob(backup_pattern),
            key=lambda p: p.name,
            reverse=True,  # Newest first
        )

        # Remove backups exceeding max_backups
        for old_backup in backups[self.max_backups :]:
            with contextlib.suppress(OSError):
                old_backup.unlink()

    def load_backup(self, n: int = 0) -> list[Todo]:
        """Load todos from the nth most recent backup.

        Args:
            n: Which backup to load (0 = most recent, 1 = second most recent, etc.)

        Returns:
            List of Todo objects from the backup.

        Raises:
            FileNotFoundError: If no backup files exist or n is too large.
            ValueError: If the backup file contains invalid JSON or data.
        """
        backup_pattern = f"{self.path.name}.bak.*"
        backups = sorted(
            self.path.parent.glob(backup_pattern),
            key=lambda p: p.name,
            reverse=True,  # Newest first
        )

        if not backups:
            raise FileNotFoundError(f"No backup files found for '{self.path}'")

        if n >= len(backups):
            raise FileNotFoundError(
                f"Backup index {n} out of range. Only {len(backups)} backup(s) available."
            )

        backup_path = backups[n]

        # Security: Check file size before loading
        file_size = backup_path.stat().st_size
        if file_size > _MAX_JSON_SIZE_BYTES:
            size_mb = file_size / (1024 * 1024)
            limit_mb = _MAX_JSON_SIZE_BYTES / (1024 * 1024)
            raise ValueError(
                f"Backup file too large ({size_mb:.1f}MB > {limit_mb:.0f}MB limit)."
            )

        try:
            raw = json.loads(backup_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in backup '{backup_path}': {e.msg}. "
                f"Check line {e.lineno}, column {e.colno}."
            ) from e

        if not isinstance(raw, list):
            raise ValueError("Backup storage must be a JSON list")
        return [Todo.from_dict(item) for item in raw]

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
