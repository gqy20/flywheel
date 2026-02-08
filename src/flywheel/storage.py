"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import errno
import json
import os
import stat
import tempfile
import time
from pathlib import Path

from .todo import Todo

# Maximum JSON file size to prevent DoS attacks (10MB)
_MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024

# Default lock timeout in seconds
_DEFAULT_LOCK_TIMEOUT = 5.0

# Lock polling interval in seconds
_LOCK_POLL_INTERVAL = 0.1


class _FileLock:
    """Cross-platform file lock context manager.

    Uses fcntl.flock on Unix and msvcrt.locking on Windows to provide
    exclusive file locking. The lock is automatically released when the
    context manager exits.

    Args:
        path: Path to the file to lock.
        timeout: Maximum time to wait for lock acquisition in seconds.
            Raises TimeoutError if lock cannot be acquired within this time.

    Raises:
        TimeoutError: If lock cannot be acquired within timeout period.
        OSError: If lock acquisition fails for other reasons.
    """

    def __init__(self, path: Path, timeout: float = _DEFAULT_LOCK_TIMEOUT) -> None:
        self._path = path
        self._timeout = timeout
        self._lock_file: Path | None = None
        self._lock_fd: int | None = None

    def __enter__(self) -> _FileLock:
        # Create a separate lock file in the same directory
        # This avoids issues with the main file being replaced
        lock_path = self._path.parent / f".{self._path.name}.lock"
        self._lock_file = lock_path

        # Open lock file (create if doesn't exist)
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        self._lock_fd = fd

        start_time = time.time()

        while True:
            try:
                self._acquire_lock(fd)
                return self
            except OSError as e:
                # Lock is held by another process
                if e.errno not in (errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK):
                    raise

                # Check timeout
                elapsed = time.time() - start_time
                if elapsed >= self._timeout:
                    os.close(fd)
                    raise TimeoutError(
                        f"Could not acquire lock on '{self._path}' "
                        f"after {self._timeout:.1f} seconds"
                    ) from None

                # Wait before retrying
                time.sleep(_LOCK_POLL_INTERVAL)

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        if self._lock_fd is not None:
            try:
                self._release_lock(self._lock_fd)
                os.close(self._lock_fd)
            except OSError:
                pass
            self._lock_fd = None

        # Note: We don't delete the lock file as it will be reused

    def _acquire_lock(self, fd: int) -> None:
        """Acquire exclusive lock on file descriptor."""
        if os.name == "nt":  # Windows
            import msvcrt

            # msvcrt.locking expects a file-like object
            # Seek to beginning and lock 1 byte
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)  # Non-blocking lock
        else:  # Unix/Linux/macOS
            import fcntl

            # fcntl.flock with LOCK_EX | LOCK_NB for non-blocking exclusive lock
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _release_lock(self, fd: int) -> None:
        """Release lock on file descriptor."""
        if os.name == "nt":  # Windows
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:  # Unix/Linux/macOS
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_UN)


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
        # Acquire file lock for concurrent access protection
        with _FileLock(self.path):
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

        File locking is used to prevent concurrent write corruption from
        multiple processes.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        # Acquire file lock for concurrent write protection
        with _FileLock(self.path):
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
