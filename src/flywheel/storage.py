"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import stat
import tempfile
from pathlib import Path

from .todo import Todo

# Maximum JSON file size to prevent DoS attacks (10MB)
_MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024


def _atomic_increment_counter(counter_path: Path, min_value: int = 0) -> int:
    """Atomically read and increment a counter file, returning the new value.

    Uses file locking to ensure atomicity across multiple processes.
    Creates the counter file if it doesn't exist.

    Args:
        counter_path: Path to the counter file
        min_value: Minimum value for the counter. If current counter is below this,
                   it will be set to min_value before incrementing.

    Returns:
        The new counter value after incrementing
    """
    # Ensure parent directory exists
    _ensure_parent_directory(counter_path)

    # Open/create the counter file
    fd = os.open(
        str(counter_path),
        os.O_RDWR | os.O_CREAT,
        stat.S_IRUSR | stat.S_IWUSR,  # 0o600
    )

    try:
        # Acquire exclusive lock (blocks until available)
        fcntl.flock(fd, fcntl.LOCK_EX)

        # Read current value (default to 0 if empty/missing)
        try:
            content = os.read(fd, 1024).decode("utf-8").strip()
            current = int(content) if content else 0
        except (ValueError, UnicodeDecodeError):
            current = 0

        # Ensure counter is at least min_value to sync with existing data
        if current < min_value:
            current = min_value

        # Increment and write back
        new_value = current + 1

        # Truncate and write new value
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        os.write(fd, str(new_value).encode("utf-8"))

        return new_value
    finally:
        # Release lock and close file
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


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

            # Atomic rename (os.replace is atomic on both Unix and Windows)
            os.replace(temp_path, self.path)
        except OSError:
            # Clean up temp file on error
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
            raise

    @property
    def _counter_path(self) -> Path:
        """Path to the ID counter file (alongside the main database)."""
        return self.path.with_suffix(self.path.suffix + ".counter")

    def next_id(self, todos: list[Todo]) -> int:
        """Generate a unique ID for a new todo.

        Uses file-based locking to ensure uniqueness across concurrent processes.
        The counter is stored in a separate file and atomically incremented.
        The counter is synced with existing todo IDs to ensure consistency.

        Args:
            todos: Current list of todos (used to sync counter with existing data)

        Returns:
            A unique integer ID for the new todo
        """
        try:
            # Calculate max ID from existing todos to sync counter if needed
            max_existing_id = max((todo.id for todo in todos), default=0)
            return _atomic_increment_counter(self._counter_path, min_value=max_existing_id)
        except OSError:
            # Fallback to in-memory calculation if file locking fails
            # This maintains backwards compatibility but may have race conditions
            return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
