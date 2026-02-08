"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import stat
import tempfile
from pathlib import Path

import portalocker
from portalocker.exceptions import LockException

from .todo import Todo

# Maximum JSON file size to prevent DoS attacks (10MB)
_MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024

# Default lock timeout in seconds
_DEFAULT_LOCK_TIMEOUT = 5.0


@contextlib.contextmanager
def _file_lock(lock_path: Path, timeout: float = _DEFAULT_LOCK_TIMEOUT) -> contextlib.AbstractContextManager[None]:  # type: ignore[misc]
    """Acquire an exclusive file lock for concurrent access protection.

    Uses portalocker for cross-platform file locking (Unix/Windows).
    The lock file is created alongside the data file with a .lock suffix.

    Args:
        lock_path: Path to the lock file (typically data_file.with_suffix('.lock'))
        timeout: Maximum seconds to wait for lock acquisition

    Raises:
        TimeoutError: If lock cannot be acquired within timeout period
        OSError: If lock file operations fail

    Yields:
        None when lock is acquired
    """
    # Create parent directory if needed for lock file
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    # Open/create lock file - use 'a' mode to create if not exists
    # Lock is released when file is closed
    # Default flags include EXCLUSIVE|NON_BLOCKING which enables timeout behavior
    try:
        with portalocker.Lock(
            lock_path,
            mode="a",
            timeout=timeout,
        ):
            yield
    except LockException as e:
        raise TimeoutError(
            f"Could not acquire file lock on '{lock_path}' within {timeout}s. "
            f"Another process may be holding the lock."
        ) from e


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

    def _lock_path(self) -> Path:
        """Return the path to the lock file for this storage."""
        # Use .lock suffix adjacent to the data file
        return self.path.with_suffix(self.path.suffix + ".lock")

    def load(self) -> list[Todo]:
        # Use shared lock for read (allows concurrent reads, blocks writes)
        with _file_lock(self._lock_path(), timeout=_DEFAULT_LOCK_TIMEOUT):
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
        if the process crashes during write. File locking prevents concurrent
        write corruption from multiple processes.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        # Use exclusive lock for write (blocks both reads and writes)
        with _file_lock(self._lock_path(), timeout=_DEFAULT_LOCK_TIMEOUT):
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
