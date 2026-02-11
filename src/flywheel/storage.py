"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

from .todo import Todo

# Platform-specific file locking imports
if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

# Maximum JSON file size to prevent DoS attacks (10MB)
_MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024

# File lock timeout (seconds)
_LOCK_TIMEOUT = 30

# Lock modes for Unix
_LOCK_EX = 2  # Exclusive lock
_LOCK_SH = 1  # Shared lock
_LOCK_UN = 8  # Unlock


@contextlib.contextmanager
def _file_lock(file_obj, exclusive: bool = True):
    """Context manager for file locking with cross-platform support.

    Args:
        file_obj: The file object to lock (must be opened in appropriate mode)
        exclusive: If True, acquire exclusive lock (for writes).
                   If False, acquire shared lock (for reads).

    Raises:
        OSError: If lock cannot be acquired within timeout period.
    """
    import time

    if not file_obj.closed:
        file_obj.flush()
    else:
        raise ValueError("Cannot lock closed file")

    start_time = time.time()
    lock_acquired = False

    try:
        # Try to acquire lock with timeout
        while True:
            try:
                if sys.platform == "win32":
                    # Windows: use msvcrt.locking
                    # For Windows, we need to seek to start for locking
                    file_obj.seek(0)
                    # Lock mode: 0 = unlock, 1 = shared, 2 = exclusive
                    lock_mode = 2 if exclusive else 1  # LK_NBLCK | LK_LOCK
                    msvcrt.locking(file_obj.fileno(), lock_mode, 1)
                else:
                    # Unix: use fcntl.flock
                    lock_operation = _LOCK_EX if exclusive else _LOCK_SH
                    # Non-blocking attempt first
                    fcntl.flock(file_obj.fileno(), lock_operation | fcntl.LOCK_NB)

                lock_acquired = True
                break
            except OSError as e:
                # Check for timeout
                if time.time() - start_time >= _LOCK_TIMEOUT:
                    timeout_msg = (
                        f"Could not acquire {'exclusive' if exclusive else 'shared'} "
                        f"file lock after {_LOCK_TIMEOUT} seconds. "
                        f"Another process may be holding the lock."
                    )
                    raise OSError(timeout_msg) from e

                # Wait a bit before retrying
                time.sleep(0.01)

        yield

    finally:
        # Release the lock
        if lock_acquired:
            try:
                if sys.platform == "win32":
                    file_obj.seek(0)
                    msvcrt.locking(file_obj.fileno(), 0, 1)  # 0 = LK_UNLCK
                else:
                    fcntl.flock(file_obj.fileno(), _LOCK_UN)
            except OSError:
                # Ignore errors during unlock
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

        # Use shared lock for reading - allows multiple readers, blocks writers
        with open(self.path, encoding="utf-8") as f, _file_lock(f, exclusive=False):
            content = f.read()

        try:
            raw = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in '{self.path}': {e.msg}. "
                f"Check line {e.lineno}, column {e.colno}."
            ) from e

        if not isinstance(raw, list):
            raise ValueError("Todo storage must be a JSON list")
        return [Todo.from_dict(item) for item in raw]

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically with file locking.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        File locking ensures serialized access when multiple processes write
        simultaneously, preventing last-writer-wins data loss.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

        payload = [todo.to_dict() for todo in todos]
        content = json.dumps(payload, ensure_ascii=False, indent=2)

        # Acquire exclusive lock on TARGET file for cross-process synchronization
        # We lock the target file (not the temp file) so concurrent processes
        # block each other. We use 'a' mode which creates the file if needed.
        with (
            open(self.path, "a", encoding="utf-8") as lock_file,
            _file_lock(lock_file, exclusive=True),
        ):
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
                    # No lock needed here since we're holding the target file lock
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        f.write(content)
                        f.flush()
                        os.fsync(f.fileno())

                    # Atomic rename (os.replace is atomic on both Unix and Windows)
                    # We still hold the target file lock here, ensuring exclusive access
                    os.replace(temp_path, self.path)
                except OSError:
                    # Clean up temp file on error
                    with contextlib.suppress(OSError):
                        os.unlink(temp_path)
                    raise

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
