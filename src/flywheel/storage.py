"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import stat
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import filelock

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
    """Persistent storage for todos.

    Args:
        path: Path to the JSON file for storage.
        use_lock: If True, use file locking to prevent concurrent write conflicts.
            When enabled, use the transaction() context manager to safely perform
            load-modify-save cycles. Default is False for backward compatibility.
        lock_timeout: Maximum time in seconds to wait for lock acquisition.
            Default is 30 seconds. Only used when use_lock=True.

    Note:
        For concurrent access safety, always use the transaction() context manager
        to wrap the entire load-modify-save cycle:

            with storage.transaction():
                todos = storage.load()
                todos.append(new_todo)
                storage.save(todos)

        Individual load() and save() calls inside a transaction() block will not
        re-acquire the lock.
    """

    # Default lock timeout in seconds
    DEFAULT_LOCK_TIMEOUT = 30

    def __init__(
        self,
        path: str | None = None,
        use_lock: bool = False,
        lock_timeout: float | None = None,
    ) -> None:
        self.path = Path(path or ".todo.json")
        self.use_lock = use_lock
        self.lock_timeout = lock_timeout if lock_timeout is not None else self.DEFAULT_LOCK_TIMEOUT

        # Create lock file path (same directory, same name with .lock suffix)
        self._lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self._file_lock = filelock.FileLock(self._lock_path, timeout=self.lock_timeout)
        # Track if we're inside a transaction (lock already held)
        self._in_transaction = False

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Context manager for transactional access to the storage.

        When use_lock is True, acquires an exclusive lock for the entire block,
        ensuring that load-modify-save cycles are atomic across processes.

        Usage:
            with storage.transaction():
                todos = storage.load()
                todos.append(new_todo)
                storage.save(todos)

        If use_lock is False, this context manager does nothing (no-op).

        Yields:
            None
        """
        if not self.use_lock:
            # No locking, just execute the block
            yield
            return

        if self._in_transaction:
            # Already in a transaction (reentrant), just execute the block
            yield
            return

        # Acquire lock and set transaction flag
        with self._file_lock:
            self._in_transaction = True
            try:
                yield
            finally:
                self._in_transaction = False

    def load(self) -> list[Todo]:
        """Load todos from file.

        If use_lock is True and not inside a transaction(), acquires an
        exclusive lock before reading. The lock is released after reading
        completes (unless inside a transaction()).

        For safe concurrent access, wrap the entire load-modify-save cycle
        in a transaction() block.
        """
        if not self.use_lock or self._in_transaction:
            return self._load_without_lock()

        with self._file_lock:
            return self._load_without_lock()

    def _load_without_lock(self) -> list[Todo]:
        """Internal load method without lock acquisition."""
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

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        If use_lock is True and not inside a transaction(), acquires an
        exclusive lock before writing. This prevents last-writer-wins data loss
        when multiple processes modify the same file concurrently.

        For safe concurrent access, wrap the entire load-modify-save cycle
        in a transaction() block.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        if not self.use_lock or self._in_transaction:
            self._save_without_lock(todos)
            return

        with self._file_lock:
            self._save_without_lock(todos)

    def _save_without_lock(self, todos: list[Todo]) -> None:
        """Internal save method without lock acquisition."""
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
