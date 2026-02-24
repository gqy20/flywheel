"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from .todo import Todo


class ConcurrencyError(Exception):
    """Raised when concurrent modification is detected."""
    pass

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
    """Persistent storage for todos.

    Provides file locking to prevent concurrent modification data loss.
    Use the `locked()` context manager for safe load-modify-save sequences.
    """

    # Lock file suffix for exclusive access
    _LOCK_SUFFIX = ".lock"

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or ".todo.json")
        self._lock_fd: int | None = None
        self._lock_path = self.path.with_suffix(self.path.suffix + self._LOCK_SUFFIX)

    def _get_or_create_lock_file(self) -> int:
        """Get or create the lock file, returning its file descriptor.

        The lock file is created if it doesn't exist. We keep the fd open
        for use with fcntl.flock.
        """
        if self._lock_fd is not None:
            return self._lock_fd

        # Ensure parent directory exists for lock file
        _ensure_parent_directory(self._lock_path)

        # Create/open lock file (doesn't need content, just needs to exist)
        # Use O_CREAT | O_RDWR to create if not exists, open for read/write
        self._lock_fd = os.open(
            str(self._lock_path),
            os.O_CREAT | os.O_RDWR,
            stat.S_IRUSR | stat.S_IWUSR,  # 0o600
        )
        return self._lock_fd

    def try_lock(self) -> bool:
        """Try to acquire an exclusive lock without blocking.

        Returns:
            True if lock was acquired, False if lock is held by another process.
        """
        fd = self._get_or_create_lock_file()
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (BlockingIOError, OSError):
            return False

    def lock(self) -> None:
        """Acquire an exclusive lock, blocking until available."""
        fd = self._get_or_create_lock_file()
        fcntl.flock(fd, fcntl.LOCK_EX)

    def unlock(self) -> None:
        """Release the exclusive lock."""
        if self._lock_fd is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            except OSError:
                pass  # Lock may have been released or fd closed

    @contextmanager
    def locked(self) -> Generator[None, None, None]:
        """Context manager for acquiring and releasing the file lock.

        Usage:
            with storage.locked():
                todos = storage.load()
                todos.append(new_todo)
                storage.save(todos)

        The lock is automatically released even if an exception occurs.
        """
        self.lock()
        try:
            yield
        finally:
            self.unlock()

    def save_with_lock_check(self, todos: list[Todo]) -> None:
        """Save todos with concurrency detection.

        This method checks if the file has been modified since the last load
        and raises ConcurrencyError if so. This is for optimistic locking.

        For proper locking, use the `locked()` context manager instead.

        Raises:
            ConcurrencyError: If the file was modified after it was loaded.
        """
        if not self.path.exists():
            # No existing file, safe to save
            self.save(todos)
            return

        # Get current file modification time
        current_mtime = self.path.stat().st_mtime

        # Check if we have a recorded load time to compare
        if hasattr(self, '_last_load_mtime') and self._last_load_mtime is not None:
            if current_mtime != self._last_load_mtime:
                raise ConcurrencyError(
                    f"Concurrent modification detected: '{self.path}' was modified "
                    "after it was loaded. Use the locked() context manager for safe "
                    "load-modify-save sequences."
                )

        self.save(todos)

    def load(self) -> list[Todo]:
        if not self.path.exists():
            self._last_load_mtime = None
            return []

        # Record modification time for optimistic locking
        stat_info = self.path.stat()
        self._last_load_mtime = stat_info.st_mtime

        # Security: Check file size before loading to prevent DoS
        file_size = stat_info.st_size
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
