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

    def __init__(self, path: str | None = None, backup_count: int = 0) -> None:
        self.path = Path(path or ".todo.json")
        self.backup_count = backup_count

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

    def _rotate_backups(self) -> None:
        """Rotate backup files (1->2, 2->3, etc.) before creating new backup.

        This ensures we only keep backup_count most recent backups.
        """
        # Rotate existing backups from highest to lowest
        # e.g., .3.bak -> .4.bak, .2.bak -> .3.bak, .1.bak -> .2.bak
        for i in range(self.backup_count - 1, 0, -1):
            old_backup = self.path.parent / f".{self.path.name}.{i}.bak"
            new_backup = self.path.parent / f".{self.path.name}.{i + 1}.bak"

            if old_backup.exists():
                # Use atomic rename to move the backup
                # If new_backup exists, it will be replaced (which is correct behavior)
                if i + 1 > self.backup_count:
                    # This backup would exceed backup_count, so delete it
                    with contextlib.suppress(OSError):
                        old_backup.unlink()
                else:
                    os.replace(old_backup, new_backup)

        # Delete any backup that exceeds backup_count
        # (handles case where backup_count was reduced)
        for i in range(self.backup_count + 1, self.backup_count + 10):
            excess_backup = self.path.parent / f".{self.path.name}.{i}.bak"
            if not excess_backup.exists():
                break
            with contextlib.suppress(OSError):
                excess_backup.unlink()

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.

        If backup_count > 0, creates rolling backups before overwriting the main file.
        """
        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

        payload = [todo.to_dict() for todo in todos]
        content = json.dumps(payload, ensure_ascii=False, indent=2)

        # Create backup if enabled and main file exists
        if self.backup_count > 0 and self.path.exists():
            # Rotate existing backups first
            self._rotate_backups()

            # Create backup by copying current file to .1.bak
            backup_path = self.path.parent / f".{self.path.name}.1.bak"
            # Use atomic rename to create backup
            # We copy to a temp file first, then rename to ensure atomicity
            fd, backup_temp = tempfile.mkstemp(
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".bak.tmp",
                text=False,
            )
            try:
                # Set restrictive permissions on backup temp file
                os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
                # Copy current file content to backup temp
                with os.fdopen(fd, "wb") as f:
                    f.write(self.path.read_bytes())
                # Atomic rename to backup location
                os.replace(backup_temp, backup_path)
            except OSError:
                # Clean up temp file on error
                with contextlib.suppress(OSError):
                    os.unlink(backup_temp)
                raise

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
