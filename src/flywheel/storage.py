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

    def __init__(self, path: str | None = None, keep_backups: int = 0) -> None:
        self.path = Path(path or ".todo.json")
        self.keep_backups = keep_backups

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

        # Create backup if enabled and file exists
        if self.keep_backups > 0 and self.path.exists():
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
        """Create a backup of the existing file with rotation.

        Implements rotation scheme: .bak, .bak.1, .bak.2, etc.
        Keeps only self.keep_backups most recent backups.
        """
        if not self.path.exists():
            return

        # Rotate existing backups (highest number first)
        # .bak.N -> .bak.(N+1), ... .bak.1 -> .bak.2, .bak -> .bak.1
        for i in range(self.keep_backups - 1, 0, -1):
            old_backup = self.path.with_suffix(f".bak.{i}")
            new_backup = self.path.with_suffix(f".bak.{i + 1}")
            if old_backup.exists():
                with contextlib.suppress(FileNotFoundError, OSError):
                    shutil.move(str(old_backup), str(new_backup))

        # Delete the oldest backup if we've reached the limit
        oldest_backup = self.path.with_suffix(f".bak.{self.keep_backups}")
        if oldest_backup.exists():
            with contextlib.suppress(FileNotFoundError, OSError):
                oldest_backup.unlink()

        # Move current .bak to .bak.1
        current_backup = self.path.with_suffix(".bak")
        rotated_backup = self.path.with_suffix(".bak.1")
        if current_backup.exists():
            with contextlib.suppress(FileNotFoundError, OSError):
                shutil.move(str(current_backup), str(rotated_backup))

        # Create new backup from current file
        with contextlib.suppress(FileNotFoundError, OSError):
            shutil.copy2(str(self.path), str(current_backup))

    def list_backups(self) -> list[Path]:
        """List all available backup files.

        Returns:
            List of Path objects for existing backup files, ordered by
            modification time (newest first).
        """
        backups = []
        # Check for .bak file
        bak_file = self.path.with_suffix(".bak")
        if bak_file.exists():
            backups.append(bak_file)

        # Check for .bak.1, .bak.2, etc.
        for i in range(1, self.keep_backups + 10):
            bak_file = self.path.with_suffix(f".bak.{i}")
            if bak_file.exists():
                backups.append(bak_file)

        # Sort by modification time (newest first)
        backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return backups

    def restore_from_backup(self, backup_path: Path) -> None:
        """Restore data from a backup file.

        Args:
            backup_path: Path to the backup file to restore from.

        Raises:
            FileNotFoundError: If the backup file doesn't exist.
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Copy backup to main file
        shutil.copy2(str(backup_path), str(self.path))
