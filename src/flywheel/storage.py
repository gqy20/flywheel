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

    # Default backup count
    _DEFAULT_BACKUP_COUNT = 3

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or ".todo.json")
        self._backup_count = self._get_backup_count()

    def _get_backup_count(self) -> int:
        """Get the number of backups to keep from environment variable.

        Reads FLYWHEEL_BACKUP_COUNT env var and returns integer value.
        Defaults to _DEFAULT_BACKUP_COUNT if not set or invalid.
        """
        count_str = os.environ.get("FLYWHEEL_BACKUP_COUNT", str(self._DEFAULT_BACKUP_COUNT))
        try:
            count = int(count_str)
            return max(0, count)  # Ensure non-negative
        except ValueError:
            return self._DEFAULT_BACKUP_COUNT

    def _backup_file(self) -> None:
        """Create a backup of the existing file before overwriting.

        Creates a numbered .bak copy (e.g., .bak.1, .bak.2) and rotates
        to keep only _backup_count number of backups.
        """
        if not self.path.exists():
            return  # No file to backup

        # Rotate existing backups first
        self._rotate_backups()

        # Create new backup as .bak.1 (most recent)
        backup_path = self._backup_path(1)
        shutil.copy2(self.path, backup_path)

    def _backup_path(self, n: int) -> Path:
        """Get the path for the nth backup file."""
        return self.path.with_suffix(self.path.suffix + f".bak.{n}")

    def _rotate_backups(self) -> None:
        """Rotate backup files to keep only _backup_count number of backups.

        Uses numbered suffixes (e.g., .bak.1, .bak.2, .bak.3).
        .bak.1 is the most recent, .bak.N is the oldest.
        """
        if self._backup_count <= 0:
            # Remove all backups if count is 0
            for backup in self._backup_files():
                with contextlib.suppress(OSError):
                    backup.unlink()
            return

        # Get all existing backup files
        backups = sorted(self._backup_files(), key=lambda p: self._backup_number(p))

        # Rotate in reverse order (oldest to newest) to avoid conflicts
        for backup in reversed(backups):
            num = self._backup_number(backup)
            if num >= self._backup_count:
                # Remove old backup exceeding limit
                with contextlib.suppress(OSError):
                    backup.unlink()
            else:
                # Move to next number (shift away from 1 to make room for new backup)
                new_path = self._backup_path(num + 1)
                with contextlib.suppress(OSError):
                    backup.rename(new_path)

    def _backup_files(self) -> list[Path]:
        """Get all backup files for this storage."""
        return list(self.path.parent.glob(f"{self.path.name}.bak.[0-9]*"))

    def _backup_number(self, path: Path) -> int:
        """Extract the backup number from a backup file path."""
        # path.suffixes returns ['.json', '.bak', '.1'] for 'todo.json.bak.1'
        # or just ['.bak', '.1'] if using with_suffix()
        suffixes = path.suffixes
        # Find the .bak.N suffix
        for i, suffix in enumerate(suffixes):
            if suffix == ".bak" and i + 1 < len(suffixes):
                try:
                    # Strip leading dot from the number suffix
                    num_str = suffixes[i + 1].lstrip(".")
                    return int(num_str)
                except ValueError:
                    pass
        return 0

    def restore_from_backup(self) -> None:
        """Restore data from the most recent backup.

        Raises:
            ValueError: If no backup file exists.
        """
        # Look for the most recent backup
        backup_path = self._find_latest_backup()

        if backup_path is None or not backup_path.exists():
            raise ValueError(f"no backup found for '{self.path}'")

        # Copy backup to main file
        shutil.copy2(backup_path, self.path)

    def _find_latest_backup(self) -> Path | None:
        """Find the most recent backup file.

        Returns:
            Path to the most recent backup, or None if no backups exist.
        """
        # .bak.1 is always the most recent backup
        latest = self._backup_path(1)
        if latest.exists():
            return latest

        # Check all numbered backups (in case some were manually created)
        backups = self._backup_files()
        if backups:
            # Sort by number and return the highest (most recent)
            backups.sort(key=lambda p: self._backup_number(p))
            return backups[-1]

        return None

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
        """
        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

        # Create backup before overwriting existing file
        if self.path.exists():
            self._backup_file()

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
