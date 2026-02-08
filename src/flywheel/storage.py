"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
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

    def __init__(
        self,
        path: str | None = None,
        enable_backups: bool = True,
        max_backups: int = 3,
    ) -> None:
        self.path = Path(path or ".todo.json")
        self.enable_backups = enable_backups
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

        Backups: If enabled, creates backup files before overwriting existing data.
        """
        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

        # Create backup if enabled and file exists
        if self.enable_backups and self.max_backups > 0 and self.path.exists():
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
        """Create a backup of the current file before overwriting.

        Implements rotation based on max_backups:
        - .backup (most recent)
        - .backup.1, .backup.2, etc. (older backups)

        Backup failures are silently ignored to prevent blocking the main save operation.
        """
        backup_path = self._get_backup_path(0)

        try:
            # Rotate existing backups
            self._rotate_backups()

            # Copy current file to backup
            import shutil

            shutil.copy2(self.path, backup_path)
        except OSError:
            # Silently ignore backup failures to avoid blocking main save
            pass

    def _get_backup_path(self, index: int) -> Path:
        """Get backup path for given index.

        index=0 returns .backup (most recent)
        index=1 returns .backup.1, index=2 returns .backup.2, etc.
        """
        if index == 0:
            return self.path.with_suffix(self.path.suffix + ".backup")
        return self.path.with_suffix(self.path.suffix + f".backup.{index}")

    def _rotate_backups(self) -> None:
        """Rotate backup files to respect max_backups limit.

        Removes the oldest backup if needed, then shifts each backup
        to the next index (e.g., .backup.1 -> .backup.2).
        """
        if self.max_backups == 0:
            return

        # Remove oldest backup if we're at the limit
        oldest_backup = self._get_backup_path(self.max_backups - 1)
        with contextlib.suppress(OSError):
            oldest_backup.unlink()

        # Rotate backups in reverse order (highest index first)
        for i in range(self.max_backups - 1, 0, -1):
            src = self._get_backup_path(i - 1)
            dst = self._get_backup_path(i)
            with contextlib.suppress(OSError):
                src.replace(dst)
