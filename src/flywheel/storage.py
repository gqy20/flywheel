"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import stat
import tempfile
import time
from pathlib import Path

from .todo import Todo

# Maximum JSON file size to prevent DoS attacks (10MB)
_MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024

# Default timeout for file lock acquisition (seconds)
_DEFAULT_LOCK_TIMEOUT = 5.0

# Lock polling interval (seconds)
_LOCK_POLL_INTERVAL = 0.05


def _get_lock_file_path(file_path: Path) -> Path:
    """Get the lock file path for a given file.

    Uses a separate lock file alongside the data file to coordinate
    concurrent access across processes.
    """
    return file_path.parent / f".{file_path.name}.lock"


@contextlib.contextmanager
def _acquire_file_lock(
    file_path: Path,
    exclusive: bool = True,
    timeout: float = _DEFAULT_LOCK_TIMEOUT,
):
    """Acquire a file lock with timeout.

    Args:
        file_path: Path to the file being locked
        exclusive: If True, acquire exclusive lock (for writes).
                   If False, acquire shared lock (for reads).
        timeout: Maximum seconds to wait for lock acquisition

    Raises:
        TimeoutError: If lock cannot be acquired within timeout period
        OSError: If lock file operations fail

    Yields:
        None when lock is acquired
    """
    lock_path = _get_lock_file_path(file_path)

    # Create lock file if it doesn't exist
    if not lock_path.exists():
        try:
            lock_path.touch(mode=stat.S_IRUSR | stat.S_IWUSR)
        except OSError as e:
            raise OSError(f"Failed to create lock file '{lock_path}': {e}") from e

    # Try to acquire lock using filelock library (cross-platform)
    try:
        from filelock import FileLock
    except ImportError:
        # Fallback: implement basic lock using fcntl (Unix) or msvcrt (Windows)
        yield from _acquire_lock_fallback(lock_path, exclusive, timeout)
        return

    # Use filelock for cross-platform locking with timeout
    lock = FileLock(str(lock_path), timeout=timeout)

    try:
        lock.acquire()
        yield
    except Exception:  # filelock.Timeout
        # Check if it's a timeout exception
        if "timeout" in str(type(lock).__name__).lower():
            raise TimeoutError(
                f"Could not acquire {'exclusive' if exclusive else 'shared'} "
                f"lock on '{file_path}' within {timeout:.1f} seconds. "
                f"Another process may be holding the lock."
            ) from None
        raise
    finally:
        with contextlib.suppress(Exception):
            lock.release(force=True)


def _acquire_lock_fallback(
    lock_path: Path,
    exclusive: bool,
    timeout: float,
):
    """Fallback lock implementation using platform-specific primitives.

    This is used when filelock is not available. Uses fcntl on Unix
    and msvcrt on Windows.
    """
    import sys

    if sys.platform == "win32":
        import msvcrt

        def lock_file(fd):
            try:
                # Windows: lock entire file
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError:
                return False
            return True

        def unlock_file(fd):
            with contextlib.suppress(OSError):
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

    else:
        import fcntl

        def lock_file(fd):
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except (OSError, BlockingIOError):
                return False

        def unlock_file(fd):
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)

    fd = -1
    try:
        fd = os.open(lock_path, os.O_RDWR)
        start_time = time.time()

        while True:
            if lock_file(fd):
                try:
                    yield
                    return
                finally:
                    unlock_file(fd)

            # Check timeout
            if time.time() - start_time >= timeout:
                raise TimeoutError(
                    f"Could not acquire {'exclusive' if exclusive else 'shared'} "
                    f"lock on '{lock_path.parent / lock_path.stem[:-5]}' within {timeout:.1f} seconds. "
                    f"Another process may be holding the lock."
                )

            # Wait before retrying
            time.sleep(_LOCK_POLL_INTERVAL)

    finally:
        if fd >= 0:
            with contextlib.suppress(OSError):
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

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or ".todo.json")

    def load(self, lock_timeout: float = _DEFAULT_LOCK_TIMEOUT) -> list[Todo]:
        """Load todos from file with shared lock for concurrent read safety.

        Args:
            lock_timeout: Maximum seconds to wait for file lock

        Returns:
            List of Todo objects

        Raises:
            TimeoutError: If lock cannot be acquired within timeout period
            ValueError: If JSON is invalid or too large
        """
        if not self.path.exists():
            return []

        # Acquire shared lock during read to prevent concurrent modification
        with _acquire_file_lock(self.path, exclusive=False, timeout=lock_timeout):
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

    def save(self, todos: list[Todo], lock_timeout: float = _DEFAULT_LOCK_TIMEOUT) -> None:
        """Save todos to file atomically with exclusive lock for concurrent write safety.

        Args:
            todos: List of Todo objects to save
            lock_timeout: Maximum seconds to wait for file lock

        Raises:
            TimeoutError: If lock cannot be acquired within timeout period
            OSError: If file operations fail

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        # Acquire exclusive lock during write to prevent concurrent modification
        with _acquire_file_lock(self.path, exclusive=True, timeout=lock_timeout):
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
