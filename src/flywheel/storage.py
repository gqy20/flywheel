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


def _get_backup_count() -> int:
    """Get the maximum number of backups to keep from environment variable.

    Returns:
        int: Number of backups to keep (0 = disabled, default = 3)
    """
    try:
        count = os.getenv("FLYWHEEL_BACKUP_COUNT", "3")
        return max(0, int(count))
    except ValueError:
        return 3  # Default if env var is invalid


class TodoStorage:
    """Persistent storage for todos."""

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or ".todo.json")

    def _backup_file(self) -> None:
        """Create a backup of the existing file before overwriting.

        Copies the current file to a .bak backup with numbered suffix.
        Implements rotation to keep only N backups (configurable via
        FLYWHEEL_BACKUP_COUNT env var, default=3).

        If FLYWHEEL_BACKUP_COUNT is 0, no backup is created.
        """
        backup_count = _get_backup_count()
        if backup_count == 0:
            return

        if not self.path.exists():
            return

        # Find existing backup files (use relative pattern for Python 3.13+)
        backup_pattern = f"{self.path.name}.*.bak"
        existing_backups = sorted(
            self.path.parent.glob(backup_pattern),
            key=lambda p: p.stat().st_mtime,
        )

        # Create new backup with numbered suffix
        # Use next number in sequence (1-indexed)
        next_num = len(existing_backups) + 1
        backup_path = self.path.parent / f"{self.path.name}.{next_num}.bak"

        # Copy file preserving metadata
        shutil.copy2(self.path, backup_path)

        # Rotate: remove oldest backups if we have too many
        all_backups = sorted(
            self.path.parent.glob(backup_pattern),
            key=lambda p: p.stat().st_mtime,
        )
        while len(all_backups) > backup_count:
            oldest = all_backups.pop(0)
            with contextlib.suppress(OSError):
                oldest.unlink()

    def restore_from_backup(self) -> None:
        """Restore the most recent backup file.

        Raises:
            FileNotFoundError: If no backup file exists
        """
        backup_pattern = f"{self.path.name}.*.bak"
        backups = sorted(
            self.path.parent.glob(backup_pattern),
            key=lambda p: p.stat().st_mtime,
        )

        if not backups:
            raise FileNotFoundError(f"No backup file found for '{self.path}'")

        # Use the most recent backup (last in sorted list)
        shutil.copy2(backups[-1], self.path)

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

        Automatically creates a backup of the existing file before overwriting,
        keeping N backups (configurable via FLYWHEEL_BACKUP_COUNT, default=3).

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
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

            # Create backup of existing file before overwriting
            self._backup_file()

            # Atomic rename (os.replace is atomic on both Unix and Windows)
            os.replace(temp_path, self.path)
        except OSError:
            # Clean up temp file on error
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
            raise

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
