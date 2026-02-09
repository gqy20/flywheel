"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import stat
import tempfile
from datetime import datetime
from pathlib import Path

from .todo import Todo

# Maximum JSON file size to prevent DoS attacks (10MB)
_MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024

# Default maximum number of backups to keep
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

    def __init__(self, path: str | None = None, max_backups: int = _DEFAULT_MAX_BACKUPS) -> None:
        self.path = Path(path or ".todo.json")
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

        Before overwriting the existing file, creates a backup with .bak extension
        to protect against data corruption bugs and accidental deletion.
        """
        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

        # Create backup if file exists
        if self.path.exists():
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

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1

    def _create_backup(self) -> None:
        """Create a backup of the existing file with timestamp.

        Backup files are named with the pattern: <basename>.<timestamp>.bak
        Example: .todo.json.20250209_123456.123456.bak
        """
        # Use microseconds to ensure unique backup filenames even within same second
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S.%f")
        backup_name = f"{self.path.name}.{timestamp}.bak"
        backup_path = self.path.parent / backup_name

        # Copy current file to backup
        import shutil
        shutil.copy2(self.path, backup_path)

        # Cleanup old backups, keeping only max_backups most recent
        self._cleanup_old_backups()

    def _cleanup_old_backups(self) -> None:
        """Remove old backups, keeping only max_backups most recent ones."""
        backups = self._get_backup_files()
        # Sort by modification time (newest first)
        backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        # Remove excess backups
        for old_backup in backups[self.max_backups:]:
            with contextlib.suppress(OSError):
                old_backup.unlink()

    def _get_backup_files(self) -> list[Path]:
        """Get all backup files for this storage, sorted by modification time (newest first)."""
        pattern = f"{self.path.name}.*.bak"
        backups = list(self.path.parent.glob(pattern))
        backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return backups

    def list_backups(self) -> list[Path]:
        """List all backup files for this storage.

        Returns:
            List of backup file paths, sorted from newest to oldest.
        """
        return self._get_backup_files()

    def restore_from_backup(self, backup_path: str | Path) -> None:
        """Restore data from a backup file.

        Args:
            backup_path: Path to the backup file to restore from.

        Raises:
            FileNotFoundError: If the backup file doesn't exist.
            ValueError: If the backup file contains invalid data.
        """
        backup = Path(backup_path)
        if not backup.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Validate backup contains valid data before restoring
        try:
            backup_content = backup.read_text(encoding="utf-8")
            raw = json.loads(backup_content)
            if not isinstance(raw, list):
                raise ValueError("Backup must contain a list of todos")
        except (json.JSONDecodeError, OSError) as e:
            raise ValueError(f"Invalid backup file: {e}") from e

        # Create backup of current file before restoring
        if self.path.exists():
            self._create_backup()

        # Copy backup to main file
        import shutil
        shutil.copy2(backup, self.path)
