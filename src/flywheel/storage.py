"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path

from .todo import Todo


@contextlib.contextmanager
def _file_lock(lock_file: Path):
    """Context manager for cross-platform file locking.

    Uses fcntl on Unix and msvcrt on Windows to provide exclusive file locking.
    The lock is released when exiting the context manager.

    Args:
        lock_file: Path to the file to lock

    Raises:
        OSError: If locking fails
    """
    fd = -1
    try:
        # Create lock file parent directory if it doesn't exist
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(lock_file, os.O_RDWR | os.O_CREAT)
        if sys.platform == "win32":
            import msvcrt

            # Windows: use msvcrt.locking
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        else:
            # Unix: use fcntl.flock
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        if fd >= 0:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

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

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or ".todo.json")
        # Lock file is stored in the same directory as the data file
        self._lock_path = self._get_lock_path()

    def _get_lock_path(self) -> Path:
        """Get the lock file path, ensuring parent directory is valid."""
        # Validate parent directory before creating lock file path
        import contextlib

        with contextlib.suppress(ValueError, OSError):
            _ensure_parent_directory(self.path)
        return self.path.with_name(f".{self.path.name}.lock")

    def load(self) -> list[Todo]:
        # For load, we need to validate the path before locking
        # If file doesn't exist, we can return early without locking
        if not self.path.exists():
            # Validate parent directory even for non-existent file
            # This catches path confusion issues early
            _ensure_parent_directory(self.path)
            return []

        with _file_lock(self._lock_path):
            # Double-check existence after acquiring lock
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

            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                raise ValueError("Todo storage must be a JSON list")
            return [Todo.from_dict(item) for item in raw]

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write. File locking prevents concurrent
        modifications from multiple processes.
        """
        # Ensure parent directory exists BEFORE acquiring lock
        # This ensures lock file path is valid
        _ensure_parent_directory(self.path)

        with _file_lock(self._lock_path):
            payload = [todo.to_dict() for todo in todos]
            content = json.dumps(payload, ensure_ascii=False, indent=2)

            # Create temp file in same directory as target for atomic rename
            temp_path = self.path.with_name(f".{self.path.name}.tmp")

            # Write to temp file first
            temp_path.write_text(content, encoding="utf-8")

            # Atomic rename (os.replace is atomic on both Unix and Windows)
            os.replace(temp_path, self.path)

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1

    def add_todo(self, todo: Todo) -> None:
        """Atomically add a todo to storage.

        This method holds the file lock during the entire read-modify-write cycle,
        preventing race conditions when multiple processes add todos concurrently.

        Args:
            todo: The todo to add
        """
        with _file_lock(self._lock_path):
            # Ensure parent directory exists
            _ensure_parent_directory(self.path)

            # Read current state
            if self.path.exists():
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(raw, list):
                    raise ValueError("Todo storage must be a JSON list")
                todos = [Todo.from_dict(item) for item in raw]
            else:
                todos = []

            # Modify
            todos.append(todo)

            # Write
            payload = [t.to_dict() for t in todos]
            content = json.dumps(payload, ensure_ascii=False, indent=2)
            temp_path = self.path.with_name(f".{self.path.name}.tmp")
            temp_path.write_text(content, encoding="utf-8")
            os.replace(temp_path, self.path)
