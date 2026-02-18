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

# Lock file suffix for concurrent access protection
_LOCK_SUFFIX = ".lock"


@contextlib.contextmanager
def _file_lock(lock_path: Path, exclusive: bool = True):
    """Acquire an exclusive file lock for the given path.

    Uses fcntl.flock (BSD/POSIX flock semantics) for advisory locking.
    The lock is released automatically when the context manager exits.

    Args:
        lock_path: Path to the lock file
        exclusive: If True, acquire exclusive lock; otherwise shared lock

    Note:
        On systems without fcntl (Windows), this is a no-op and provides
        no synchronization. Windows users should avoid concurrent access.
    """
    lock_file = None
    try:
        # Ensure parent directory exists
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        # Open/create lock file
        lock_file = open(lock_path, "w")  # noqa: SIM115

        # Try to acquire the lock (non-blocking first, then blocking)
        lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        fcntl.flock(lock_file.fileno(), lock_type)

        yield lock_file
    finally:
        if lock_file is not None:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
            except OSError:
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
    """Persistent storage for todos.

    Thread/Process Safety:
        This class uses file locking (fcntl.flock) to prevent race conditions
        in the read-modify-write pattern. Use atomic_read_modify_write() for
        operations that need to load, modify, and save atomically.

    Note:
        File locking is only fully supported on Unix-like systems (Linux, macOS).
        Windows users should avoid concurrent multi-process access.
    """

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or ".todo.json")

    @property
    def _lock_path(self) -> Path:
        """Return the path to the lock file for this storage."""
        return self.path.with_suffix(self.path.suffix + _LOCK_SUFFIX)

    def _acquire_lock(self, exclusive: bool = True):
        """Acquire a file lock for this storage.

        Args:
            exclusive: If True, acquire exclusive lock; otherwise shared lock

        Returns:
            Context manager that holds the lock
        """
        return _file_lock(self._lock_path, exclusive=exclusive)

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

    def atomic_read_modify_write(self, modifier) -> None:
        """Atomically perform a load-modify-save operation with file locking.

        This prevents race conditions when multiple processes need to modify
        the same data concurrently.

        Args:
            modifier: A callable that takes a list[Todo] and returns the
                     modified list[Todo] to be saved.

        Example:
            def add_todo(todos):
                new_id = max((t.id for t in todos), default=0) + 1
                todos.append(Todo(id=new_id, text="New task"))
                return todos

            storage.atomic_read_modify_write(add_todo)
        """
        with self._acquire_lock(exclusive=True):
            todos = self.load()
            modified_todos = modifier(todos)
            self.save(modified_todos)

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
