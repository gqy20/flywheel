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

# Default number of backups to keep
_DEFAULT_BACKUP_COUNT = 3


def _get_backup_count() -> int:
    """Get the number of backups to keep from environment variable.

    Returns:
        int: Number of backups to keep (0 means disabled).
    """
    try:
        value = os.environ.get("TODO_BACKUP_COUNT", str(_DEFAULT_BACKUP_COUNT))
        count = int(value)
        return max(0, count)  # Ensure non-negative
    except ValueError:
        return _DEFAULT_BACKUP_COUNT


def _rotate_backups(file_path: Path, max_backups: int) -> None:
    """Rotate backup files, keeping only the most recent max_backups.

    Args:
        file_path: The original file path.
        max_backups: Maximum number of backups to keep.

    Rotation scheme:
        - Newest backup: .bak (no number)
        - Older backups: .bak.1, .bak.2, ..., .bak.(max_backups-1)
    """
    if max_backups <= 0:
        return

    # Rotate existing numbered backups: .bak.N -> .bak.N+1
    # We start from the highest number to avoid overwriting
    existing_backups = []
    for f in file_path.parent.glob(f"{file_path.name}.bak.*"):
        suffix = f.name.split(".bak.")[-1]
        if suffix.isdigit():
            existing_backups.append((int(suffix), f))

    # Sort by number descending (oldest numbered backup first in rotation)
    existing_backups.sort(key=lambda x: x[0], reverse=True)

    for num, backup in existing_backups:
        if num >= max_backups - 1:
            # Delete old backups beyond the limit
            with contextlib.suppress(OSError):
                backup.unlink()
        else:
            # Rotate to higher number
            new_name = backup.parent / f"{file_path.name}.bak.{num + 1}"
            with contextlib.suppress(OSError):
                os.replace(backup, new_name)

    # Rotate .bak (without number) to .bak.1
    bak_path = file_path.parent / f"{file_path.name}.bak"
    if bak_path.exists():
        new_bak = bak_path.parent / f"{file_path.name}.bak.1"
        with contextlib.suppress(OSError):
            os.replace(bak_path, new_bak)


def _create_backup(file_path: Path) -> None:
    """Create a backup of the existing file before overwriting.

    Args:
        file_path: The file to backup.

    Note:
        Backup failures are silently suppressed to prevent main save operation
        from failing. This is intentional - the save operation is more critical
        than the backup creation.
    """
    max_backups = _get_backup_count()
    if max_backups <= 0:
        return

    if not file_path.exists():
        return

    try:
        # First rotate existing backups
        _rotate_backups(file_path, max_backups)

        # Create new backup as .bak (most recent)
        bak_path = file_path.parent / f"{file_path.name}.bak"
        shutil.copy2(file_path, bak_path)
    except OSError:
        # Silently suppress backup failures - don't prevent main save
        pass


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

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or ".todo.json")

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
            _create_backup(self.path)

            # Atomic rename (os.replace is atomic on both Unix and Windows)
            os.replace(temp_path, self.path)
        except OSError:
            # Clean up temp file on error
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
            raise

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
