"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import stat
import tempfile
from datetime import UTC, datetime
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

    # Default number of backups to retain
    DEFAULT_BACKUP_LIMIT = 5

    def __init__(self, path: str | None = None, backup_limit: int = DEFAULT_BACKUP_LIMIT) -> None:
        self.path = Path(path or ".todo.json")
        self.backup_limit = backup_limit

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
        # Create backup before overwriting existing file
        if self.path.exists():
            self._cleanup_old_backups()

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

    def backup(self) -> None:
        """Create a timestamped backup of the current todo file.

        Uses the same atomic write pattern as save() to ensure backup safety.
        The backup filename includes a timestamp: .todo.json.bak.YYYYMMDDHHMMSS
        """
        if not self.path.exists():
            return

        # Read current content
        content = self.path.read_text(encoding="utf-8")

        # Generate backup filename with timestamp including microseconds for uniqueness
        # Microseconds ensure unique filenames even for rapid successive saves
        now = datetime.now(UTC)
        timestamp = now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond:06d}"
        backup_path = self.path.parent / f"{self.path.name}.bak.{timestamp}"

        # Use atomic write pattern for backup
        fd, temp_backup_path = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=f".{self.path.name}.bak.",
            suffix=".tmp",
            text=False,
        )

        try:
            os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)

            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)

            os.replace(temp_backup_path, backup_path)
        except OSError:
            with contextlib.suppress(OSError):
                os.unlink(temp_backup_path)
            raise

    def list_backups(self) -> list[dict]:
        """Return a list of available backup files with timestamps.

        Returns:
            A list of dicts with keys:
            - 'path': str - Path to the backup file
            - 'timestamp': datetime - When the backup was created
        """
        backups = []
        backup_pattern = f"{self.path.name}.bak."

        for backup_path in sorted(self.path.parent.glob(f"{self.path.name}.bak.*")):
            # Extract timestamp from filename
            if backup_path.name.startswith(backup_pattern):
                timestamp_str = backup_path.name.replace(backup_pattern, "")
                try:
                    # Try new format with microseconds (20 digits: YYYYMMDDHHMMSS + 6 digit microseconds)
                    if len(timestamp_str) == 20:
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S%f")
                    else:
                        # Try old format without microseconds (14 digits)
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                    timestamp = timestamp.replace(tzinfo=UTC)
                    backups.append({"path": str(backup_path), "timestamp": timestamp})
                except ValueError:
                    # Skip invalid backup filenames
                    continue

        return backups

    def restore(self, backup_path: Path) -> list[Todo]:
        """Restore todos from a specific backup file.

        Args:
            backup_path: Path to the backup file to restore from

        Returns:
            The list of todos restored from the backup

        Raises:
            FileNotFoundError: If the backup file doesn't exist
            ValueError: If the backup file contains invalid data
        """
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Create a temporary storage object pointing to the backup file
        backup_storage = TodoStorage(str(backup_path), backup_limit=0)
        return backup_storage.load()

    def _cleanup_old_backups(self) -> None:
        """Remove old backups, keeping only the most recent ones up to backup_limit."""
        if self.backup_limit <= 0:
            return

        # Backup the current file before cleanup
        self.backup()

        # Get list of all backups after creating new backup
        backups = sorted(
            self.list_backups(),
            key=lambda b: b["timestamp"],
            reverse=True
        )

        # Remove excess backups (keep only backup_limit most recent)
        for backup in backups[self.backup_limit:]:
            backup_path = Path(backup["path"])
            with contextlib.suppress(OSError):
                backup_path.unlink()

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
