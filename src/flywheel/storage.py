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

# Maximum JSON file size to prevent DoS attacks (10MB)
_MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024

# Platform-specific locking imports
if sys.platform == "win32":
    import msvcrt
else:
    pass


class FileLock:
    """Cross-platform file lock with context manager support.

    Uses fcntl.lockf on Unix and msvcrt.locking on Windows.
    Supports both exclusive (write) and shared (read) locks.

    Args:
        path: Path to the file to lock.
        exclusive: If True, acquire an exclusive lock (for writes).
                   If False, acquire a shared lock (for reads). Windows only
                   supports exclusive locks.
        timeout: Maximum seconds to wait for lock. Raises TimeoutError if exceeded.

    Raises:
        TimeoutError: If lock cannot be acquired within timeout.
        OSError: If lock acquisition fails for other reasons.
    """

    def __init__(
        self, path: Path | str, exclusive: bool = True, timeout: float = 10.0
    ) -> None:
        self._path = Path(path)
        self._exclusive = exclusive
        self._timeout = timeout
        self._fd: int | None = None

    def _acquire_lock(self) -> None:
        """Acquire the lock using platform-specific mechanism."""
        # Open the file for locking
        # We need to open the file ourselves to get a file descriptor
        mode = os.O_RDWR | os.O_CREAT
        self._fd = os.open(self._path, mode, stat.S_IRUSR | stat.S_IWUSR)

        if sys.platform == "win32":
            self._acquire_lock_windows()
        else:
            self._acquire_lock_unix()

    def _acquire_lock_windows(self) -> None:
        """Acquire lock on Windows using msvcrt.locking."""
        if self._fd is None:
            raise RuntimeError("File descriptor not available")

        start_time = _time_now()

        # Windows msvcrt.locking doesn't support non-blocking or timeout natively
        # We need to poll with a short sleep
        while True:
            try:
                # Lock the entire file (0 = from current position, may need LK_LOCK)
                # LK_NBLCK = non-blocking, LK_LOCK = blocking
                # msvcrt.locking(fd, mode, size)
                # We'll use a non-blocking approach and retry
                msvcrt.locking(self._fd, msvcrt.LK_NBLCK, 1)  # Lock 1 byte
                return
            except OSError:
                # Lock is held by another process
                if _time_now() - start_time >= self._timeout:
                    raise TimeoutError(
                        f"Could not acquire {'exclusive' if self._exclusive else 'shared'} "
                        f"lock on {self._path} within {self._timeout}s timeout. "
                        f"Another process may be holding the lock."
                    ) from None
                # Wait a bit before retrying
                _sleep(0.01)

    def _acquire_lock_unix(self) -> None:
        """Acquire lock on Unix using fcntl.lockf."""
        if self._fd is None:
            raise RuntimeError("File descriptor not available")

        import fcntl

        # fcntl.LOCK_EX = exclusive lock
        # fcntl.LOCK_SH = shared lock
        lock_type = fcntl.LOCK_EX if self._exclusive else fcntl.LOCK_SH

        # Try non-blocking first to support timeout
        try:
            fcntl.lockf(self._fd, lock_type | fcntl.LOCK_NB, 0)
            return
        except BlockingIOError:
            # Lock is held, wait with timeout
            pass

        # Use polling approach for timeout (fcntl with timeout is tricky)
        start_time = _time_now()
        while True:
            try:
                fcntl.lockf(self._fd, lock_type | fcntl.LOCK_NB, 0)
                return
            except BlockingIOError:
                if _time_now() - start_time >= self._timeout:
                    raise TimeoutError(
                        f"Could not acquire {'exclusive' if self._exclusive else 'shared'} "
                        f"lock on {self._path} within {self._timeout}s timeout. "
                        f"Another process may be holding the lock."
                    ) from None
                _sleep(0.01)

    def _release_lock(self) -> None:
        """Release the lock using platform-specific mechanism."""
        if self._fd is None:
            return

        try:
            if sys.platform == "win32":
                # On Windows, unlock by locking with LK_UNLCK
                with contextlib.suppress(OSError):
                    msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                # On Unix, unlock with LOCK_UN
                fcntl.lockf(self._fd, fcntl.LOCK_UN, 0)
        finally:
            # Always close the file descriptor
            os.close(self._fd)
            self._fd = None

    def __enter__(self) -> FileLock:
        self._acquire_lock()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._release_lock()


def _time_now() -> float:
    """Get current time. Helper for testing."""
    import time

    return time.time()


def _sleep(seconds: float) -> None:
    """Sleep for specified seconds. Helper for testing."""
    import time

    time.sleep(seconds)


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
        # Check if file exists before locking to avoid creating empty lock files
        if not self.path.exists():
            return []

        # Use shared lock for reading (allows multiple concurrent readers)
        with FileLock(self.path, exclusive=False, timeout=10.0):
            # Re-check existence after acquiring lock (another process may have deleted it)
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

            # Handle empty file (lock may have created it)
            if file_size == 0:
                return []

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

        Uses file locking to prevent concurrent writes from multiple processes.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        # Ensure parent directory exists BEFORE acquiring lock
        # (FileLock needs to open the file, which requires parent dir to exist)
        _ensure_parent_directory(self.path)

        # Use exclusive lock for writing (only one writer at a time)
        with FileLock(self.path, exclusive=True, timeout=10.0):
            self._save_without_lock(todos)

    def _save_without_lock(self, todos: list[Todo]) -> None:
        """Internal save method without locking (caller must hold lock)."""
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
