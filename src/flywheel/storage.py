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

# Default number of backups to retain
_DEFAULT_MAX_BACKUPS = 5


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

        Creates a backup before overwriting existing data for recovery.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        # Create backup before overwriting existing file
        if self.path.exists():
            self.backup()

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

    def _get_backup_path(self) -> Path:
        """Generate a backup file path with timestamp suffix.

        Returns:
            Path with pattern: <original_path>.bak.YYYYMMDDHHMMSS
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return self.path.parent / f"{self.path.name}.bak.{timestamp}"

    def _cleanup_old_backups(self) -> None:
        """Remove old backups, keeping only the most recent max_backups.

        Backup files are identified by the pattern: <path>.bak.*
        """
        backup_files = sorted(self.path.parent.glob(f"{self.path.name}.bak.*"))
        # Remove oldest backups if we have too many
        while len(backup_files) > self.max_backups:
            oldest = backup_files.pop(0)
            with contextlib.suppress(OSError):
                oldest.unlink()

    def backup(self) -> None:
        """Create a timestamped backup of the current todo file.

        Uses atomic write pattern (same as save()) to ensure backup integrity.
        Does nothing if the main file doesn't exist yet.
        """
        if not self.path.exists():
            return

        # Ensure parent directory exists
        _ensure_parent_directory(self.path)

        # Read current content
        content = self.path.read_text(encoding="utf-8")

        # Generate backup path with timestamp
        backup_path = self._get_backup_path()

        # Create temp file for atomic backup
        fd, temp_path = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=f".{self.path.name}.bak.",
            suffix=".tmp",
            text=False,
        )

        try:
            # Set restrictive permissions
            os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)

            # Write content to temp file
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)

            # Atomic rename to backup path
            os.replace(temp_path, backup_path)
        except OSError:
            # Clean up temp file on error
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
            raise

        # Clean up old backups
        self._cleanup_old_backups()

    def list_backups(self) -> list[dict[str, Path | str]]:
        """List all available backup files with timestamps.

        Returns:
            List of dicts with 'path' and 'timestamp' keys, sorted chronologically
            (oldest first). Returns empty list if no backups exist.
        """
        backup_files = sorted(self.path.parent.glob(f"{self.path.name}.bak.*"))
        backups = []

        for backup_path in backup_files:
            # Extract timestamp from filename: <name>.bak.YYYYMMDDHHMMSS
            name_parts = backup_path.name.split(".bak.")
            if len(name_parts) == 2 and name_parts[1].isdigit() and len(name_parts[1]) == 14:
                timestamp_str = name_parts[1]
                try:
                    # Parse timestamp for validation
                    dt = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                    backups.append({
                        "path": backup_path,
                        "timestamp": timestamp_str,
                        "datetime": dt,
                    })
                except ValueError:
                    # Invalid timestamp format, skip this backup
                    continue

        # Sort chronologically (oldest first)
        backups.sort(key=lambda b: b["datetime"])
        # Remove datetime key from output (used only for sorting)
        for b in backups:
            del b["datetime"]

        return backups

    def restore(self, backup_path: Path) -> None:
        """Restore todos from a specific backup file.

        Args:
            backup_path: Path to the backup file to restore from

        Raises:
            FileNotFoundError: If backup file doesn't exist
            ValueError: If backup file contains invalid data
        """
        if not isinstance(backup_path, Path):
            backup_path = Path(backup_path)

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Validate backup file contains valid JSON
        try:
            content = backup_path.read_text(encoding="utf-8")
            json.loads(content)  # Validate JSON structure
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in backup file: {e}") from e

        # Use atomic write to restore
        _ensure_parent_directory(self.path)

        fd, temp_path = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            text=False,
        )

        try:
            os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)

            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)

            os.replace(temp_path, self.path)
        except OSError:
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
            raise

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
