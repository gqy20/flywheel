"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import stat
import tempfile
from datetime import datetime
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

    def __init__(self, path: str | None = None, max_backups: int = 3) -> None:
        self.path = Path(path or ".todo.json")
        self.max_backups = max_backups
        self._backup_dir = self.path.parent / ".flywheel" / "backups"

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

    def _create_backup(self) -> None:
        """Create a backup of the existing file before overwriting.

        Backup files are stored in .flywheel/backups/ with timestamp suffix.
        Old backups are automatically cleaned up when exceeding max_backups.
        Failed backups don't prevent the main save operation.
        """
        if self.max_backups <= 0:
            return

        if not self.path.exists():
            return

        try:
            # Ensure backup directory exists
            self._backup_dir.mkdir(parents=True, exist_ok=True)

            # Create timestamped backup filename
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_name = f"{self.path.name}.backup.{timestamp}"
            backup_path = self._backup_dir / backup_name

            # Copy current file to backup location
            shutil.copy(self.path, backup_path)

            # Clean up old backups exceeding max_backups
            self._cleanup_old_backups()
        except OSError:
            # Backup failure should not prevent the main save operation
            # (per acceptance criteria: "Failed backups don't prevent the main save operation")
            pass

    def _cleanup_old_backups(self) -> None:
        """Remove old backups when exceeding max_backups limit.

        Keeps only the most recent max_backups files, sorted by modification time.
        """
        if self.max_backups <= 0:
            return

        # Get all backup files for this database
        pattern = f"{self.path.name}.backup.*"
        backups = sorted(self._backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime)

        # Remove oldest backups if we have too many
        while len(backups) > self.max_backups:
            oldest = backups.pop(0)
            with contextlib.suppress(OSError):
                oldest.unlink()

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.

        Backup: Creates timestamped backup before overwriting existing file.
        """
        # Create backup before overwriting (if file exists and backups enabled)
        self._create_backup()

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
