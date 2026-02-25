"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import stat
import sys
import tempfile
import threading
import typing
from pathlib import Path

from .todo import Todo

# Cross-platform file locking support
if sys.platform == "win32":
    import msvcrt

    def _lock_file(fd: int, exclusive: bool = True) -> None:
        """Lock file on Windows using msvcrt.locking."""
        mode = msvcrt.LK_NBLCK if exclusive else msvcrt.LK_NBRLCK
        try:
            msvcrt.locking(fd, mode, 1)
        except OSError:
            # If lock fails, retry with blocking (LK_LOCK)
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)

    def _unlock_file(fd: int) -> None:
        """Unlock file on Windows."""
        # Move to beginning of file for unlock
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _lock_file(fd: int, exclusive: bool = True) -> None:
        """Lock file on Unix using fcntl.flock."""
        lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        fcntl.flock(fd, lock_type)

    def _unlock_file(fd: int) -> None:
        """Unlock file on Unix."""
        fcntl.flock(fd, fcntl.LOCK_UN)


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
        # Thread-local storage to track lock state for reentrant locking
        self._lock_state = threading.local()

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
                f"Invalid JSON in '{self.path}': {e.msg}. Check line {e.lineno}, column {e.colno}."
            ) from e

        if not isinstance(raw, list):
            raise ValueError("Todo storage must be a JSON list")
        return [Todo.from_dict(item) for item in raw]

    @contextlib.contextmanager
    def exclusive_access(self) -> typing.Iterator[None]:
        """Context manager for exclusive access to the storage file.

        Acquires an exclusive lock that is held for the duration of the context.
        Use this when performing read-modify-write operations to prevent race
        conditions where concurrent processes could overwrite each other's changes.

        Example:
            with storage.exclusive_access():
                todos = storage.load()
                todos.append(new_todo)
                storage.save(todos)
        """
        # Check if we already hold the lock (reentrant locking)
        already_locked = getattr(self._lock_state, "held", False)

        if not already_locked:
            lock_fd = self._acquire_lock()
            self._lock_state.held = True
            try:
                yield
            finally:
                self._lock_state.held = False
                self._release_lock(lock_fd)
        else:
            # Lock already held, just execute the block
            yield

    def _acquire_lock(self) -> int:
        """Acquire an exclusive lock on the storage file.

        Creates a lock file and acquires an exclusive lock on it.
        The lock is held until _release_lock is called.

        Returns:
            File descriptor of the lock file (must be passed to _release_lock).
        """
        # Ensure parent directory exists before creating lock file
        _ensure_parent_directory(self.path)

        # Use a separate lock file to avoid issues with the main data file
        # being replaced during atomic rename
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")

        # Open/create the lock file
        lock_fd = os.open(
            str(lock_path),
            os.O_CREAT | os.O_RDWR,
            stat.S_IRUSR | stat.S_IWUSR,  # 0o600
        )

        try:
            _lock_file(lock_fd, exclusive=True)
        except OSError:
            # If we can't acquire the lock, close the fd and re-raise
            os.close(lock_fd)
            raise

        return lock_fd

    def _release_lock(self, lock_fd: int) -> None:
        """Release the lock acquired by _acquire_lock."""
        try:
            _unlock_file(lock_fd)
        finally:
            os.close(lock_fd)

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically with file locking.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write. Also uses file locking to prevent
        data loss from concurrent writes (last-writer-wins problem).

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        # Check if we already hold the lock (from exclusive_access context)
        already_locked = getattr(self._lock_state, "held", False)

        if not already_locked:
            lock_fd = self._acquire_lock()
            self._lock_state.held = True
            try:
                self._save_with_lock(todos)
            finally:
                self._lock_state.held = False
                self._release_lock(lock_fd)
        else:
            # Lock already held by exclusive_access, just do the save
            self._save_with_lock(todos)

    def _save_with_lock(self, todos: list[Todo]) -> None:
        """Internal save implementation that assumes lock is already held."""
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
