"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from .todo import Todo

if TYPE_CHECKING:
    from collections.abc import Iterator

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
        self._lock_path = Path(str(self.path) + ".lock")

    def _acquire_lock(self, exclusive: bool = True) -> int:
        """Acquire a file-based lock for the storage file.

        Uses fcntl.flock for advisory locking on Unix systems.
        Returns the file descriptor of the lock file.
        """
        # Ensure parent directory exists
        _ensure_parent_directory(self._lock_path)

        # Open lock file (create if doesn't exist)
        fd = os.open(
            str(self._lock_path),
            os.O_CREAT | os.O_RDWR,
            stat.S_IRUSR | stat.S_IWUSR,
        )
        try:
            # LOCK_EX for exclusive (write) access, LOCK_SH for shared (read) access
            lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            fcntl.flock(fd, lock_type)
            return fd
        except OSError:
            os.close(fd)
            raise

    def _release_lock(self, fd: int) -> None:
        """Release the file-based lock."""
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    @contextlib.contextmanager
    def _exclusive_lock(self) -> Iterator[int]:
        """Context manager for exclusive locking."""
        fd = self._acquire_lock(exclusive=True)
        try:
            yield fd
        finally:
            self._release_lock(fd)

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

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1

    def atomic_modify(self, modify_func) -> None:
        """Atomically load, modify, and save todos with file-based locking.

        Args:
            modify_func: A callable that takes a list[Todo] and modifies it in place.
                         The function should not return anything; changes are made
                         directly to the todo list.

        This method acquires an exclusive lock before loading the todos,
        calls the modify function, then saves the todos while still holding
        the lock. This prevents race conditions where concurrent processes
        could lose updates.

        Example:
            def mark_done(todos, todo_id):
                for todo in todos:
                    if todo.id == todo_id:
                        todo.mark_done()
                        return
                raise ValueError(f"Todo #{todo_id} not found")

            storage.atomic_modify(lambda todos: mark_done(todos, 1))
        """
        with self._exclusive_lock():
            todos = self.load()
            modify_func(todos)
            self.save(todos)
