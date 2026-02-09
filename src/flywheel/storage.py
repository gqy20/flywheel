"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import stat

# Platform-specific locking imports
import sys
import tempfile
from pathlib import Path

from .todo import Todo

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

# Default lock timeout in seconds
_DEFAULT_LOCK_TIMEOUT = 5.0

# Maximum JSON file size to prevent DoS attacks (10MB)
_MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024


def _acquire_lock(file_handle: int, exclusive: bool, timeout: float) -> None:
    """Acquire a file lock with timeout.

    Args:
        file_handle: Open file handle to lock
        exclusive: True for exclusive lock (write), False for shared lock (read)
        timeout: Maximum seconds to wait for lock

    Raises:
        TimeoutError: If lock cannot be acquired within timeout
        OSError: If lock acquisition fails for other reasons
    """
    import time

    start_time = time.time()
    poll_interval = 0.01  # 10ms polling interval

    while True:
        try:
            if sys.platform == "win32":
                # Windows: use msvcrt.locking
                current_pos = os.lseek(file_handle, 0, os.SEEK_CUR)
                os.lseek(file_handle, 0, os.SEEK_SET)

                lock_mode = msvcrt.LK_NBLCK
                try:
                    msvcrt.locking(file_handle, lock_mode, 1)
                except OSError as e:
                    os.lseek(file_handle, current_pos, os.SEEK_SET)
                    if e.errno == 36:  # File is locked
                        raise BlockingIOError("File is locked") from None
                    raise

                os.lseek(file_handle, current_pos, os.SEEK_SET)
            else:
                # Unix: use fcntl.flock
                lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
                try:
                    fcntl.flock(file_handle, lock_type | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise BlockingIOError("File is locked") from None

            return

        except BlockingIOError:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                lock_type = "exclusive" if exclusive else "shared"
                raise TimeoutError(
                    f"Could not acquire {lock_type} lock on file after {timeout:.1f} seconds. "
                    f"Another process may be holding the lock."
                ) from None

            time.sleep(poll_interval)


def _release_lock(file_handle: int) -> None:
    """Release a file lock.

    Args:
        file_handle: Open file handle to unlock
    """
    if sys.platform == "win32":
        current_pos = os.lseek(file_handle, 0, os.SEEK_CUR)
        os.lseek(file_handle, 0, os.SEEK_SET)
        with contextlib.suppress(OSError):
            msvcrt.locking(file_handle, msvcrt.LK_UNLCK, 1)
        os.lseek(file_handle, current_pos, os.SEEK_SET)
    else:
        fcntl.flock(file_handle, fcntl.LOCK_UN)


@contextlib.contextmanager
def _file_lock(path: Path, exclusive: bool, timeout: float):
    """Context manager for file locking.

    Args:
        path: File path to lock
        exclusive: True for exclusive lock (write), False for shared lock (read)
        timeout: Maximum seconds to wait for lock

    Yields:
        None

    Raises:
        TimeoutError: If lock cannot be acquired within timeout
        OSError: If lock acquisition fails for other reasons
    """
    mode = os.O_RDWR | os.O_CREAT
    fd = None
    try:
        fd = os.open(path, mode, stat.S_IRUSR | stat.S_IWUSR)
        _acquire_lock(fd, exclusive, timeout)
        yield
    finally:
        if fd is not None:
            with contextlib.suppress(Exception):
                _release_lock(fd)
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

    def __init__(
        self, path: str | None = None, lock_timeout: float = _DEFAULT_LOCK_TIMEOUT
    ) -> None:
        self.path = Path(path or ".todo.json")
        self._lock_timeout = lock_timeout

    def load(self) -> list[Todo]:
        # For reading, we need the parent directory to exist for the lock
        # If the file or its parent directory doesn't exist, return empty list without locking
        if not self.path.exists():
            return []

        # Acquire shared lock for reading (allows concurrent reads)
        # Parent directory exists because the file exists
        with _file_lock(self.path, exclusive=False, timeout=self._lock_timeout):
            # File may have been deleted between exists check and lock acquisition
            if not self.path.exists():
                return []

            # Return empty list for empty files
            if self.path.stat().st_size == 0:
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

        Uses exclusive file locking to prevent concurrent writes and read-during-write
        race conditions.
        """
        # Ensure parent directory exists (lazy creation, validated)
        # Must do this before acquiring lock since lock requires file path to be valid
        _ensure_parent_directory(self.path)

        # Acquire exclusive lock for writing (prevents concurrent writes and reads)
        with _file_lock(self.path, exclusive=True, timeout=self._lock_timeout):
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
