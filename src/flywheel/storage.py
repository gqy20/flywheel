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
# Default number of backups to keep
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
        self._backup_base = self.path.parent / f".{self.path.name}.bak"

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
        """Rotate existing backup files to make room for a new backup.

        Backup naming scheme:
        - .todo.json.bak      (most recent)
        - .todo.json.bak.1    (second most recent)
        - .todo.json.bak.2    (third most recent)
        - etc.

        Keeps only max_backups most recent backups.
        """
        # If no backups exist yet, nothing to rotate
        if not self._backup_base.exists():
            return

        # Rotate existing backups: .bak -> .bak.1, .bak.1 -> .bak.2, etc.
        # Start from the oldest (highest number) and work backwards
        for i in range(self.max_backups - 1, 0, -1):
            old_backup = self._backup_base.parent / f"{self._backup_base.name}.{i}"
            new_backup = self._backup_base.parent / f"{self._backup_base.name}.{i + 1}"

            if old_backup.exists():
                if new_backup.exists():
                    new_backup.unlink()
                old_backup.rename(new_backup)

        # Rotate the base backup (.bak -> .bak.1)
        if self._backup_base.exists():
            next_backup = self._backup_base.parent / f"{self._backup_base.name}.1"
            if next_backup.exists():
                next_backup.unlink()
            self._backup_base.rename(next_backup)

    def _cleanup_old_backups(self) -> None:
        """Remove backups beyond max_backups limit."""
        # Remove .bak.N files where N >= max_backups
        for i in range(self.max_backups, self.max_backups + 10):
            old_backup = self._backup_base.parent / f"{self._backup_base.name}.{i}"
            if old_backup.exists():
                old_backup.unlink()
            else:
                break

    def _create_backup(self) -> None:
        """Create a backup of the existing file before overwriting.

        Uses a numeric rotation scheme:
        - First backup: .todo.json.bak
        - Second backup: .todo.json.bak.1 (old .bak becomes .bak.1)
        - Third backup: .todo.json.bak.2 (old .bak.1 becomes .bak.2)
        - etc.

        Only keeps max_backups most recent backups.
        """
        if not self.path.exists():
            return

        # Rotate existing backups
        self._rotate_backups()

        # Create new backup by renaming the existing file to .bak
        # Use a temp copy approach since we need to keep the original file
        import shutil

        shutil.copy2(self.path, self._backup_base)

        # Clean up any backups beyond the limit
        self._cleanup_old_backups()

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.

        Backups: Creates backup of existing file before overwriting, keeping
        max_backups most recent versions using numeric rotation (.bak, .bak.1, .bak.2, ...).
        """
        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

        # Create backup of existing file before overwriting
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

    def list_backups(self) -> list[Path]:
        """List all backup files for this storage.

        Returns sorted list of backup file paths (oldest to newest).
        Returns empty list if no backups exist.

        Backup order is: .bak.N (oldest) -> ... -> .bak.1 -> .bak (newest)
        """
        backups = []

        # Collect all .bak.N files first
        numbered_backups = []
        i = 1
        while True:
            backup = self._backup_base.parent / f"{self._backup_base.name}.{i}"
            if backup.exists():
                numbered_backups.append(backup)
                i += 1
            else:
                break

        # Numbered backups are ordered oldest to newest (.bak.1 is oldest, .bak.2 is newer)
        # Wait, that's not right. The rotation scheme is:
        # .bak (newest) <- .bak.1 <- .bak.2 <- .bak.3 (oldest)
        # So .bak.N with higher N is older
        backups = reversed(numbered_backups)

        # Add base .bak file if it exists (most recent)
        if self._backup_base.exists():
            backups = list(backups) + [self._backup_base]

        return list(backups)

    def restore_from_backup(self, backup_path: Path) -> None:
        """Restore data from a backup file.

        Args:
            backup_path: Path to the backup file to restore from

        Raises:
            FileNotFoundError: If backup file doesn't exist
            ValueError: If backup file contains invalid data
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Verify backup contains valid JSON before restoring
        try:
            backup_content = backup_path.read_text(encoding="utf-8")
            json.loads(backup_content)  # Validate JSON structure
        except json.JSONDecodeError as e:
            raise ValueError(f"Backup file contains invalid JSON: {e}") from e

        # Ensure parent directory exists
        _ensure_parent_directory(self.path)

        # Copy backup to main file
        import shutil

        shutil.copy2(backup_path, self.path)
