"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import errno
import json
import os
import stat

# Cross-platform file locking imports
import sys
import tempfile
from pathlib import Path

from .todo import Todo

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


class FileLock:
    """Cross-platform file lock context manager.

    Provides exclusive file locking for concurrent write safety.
    Uses fcntl.flock() on Unix and msvcrt.locking() on Windows.
    """

    def __init__(self, file_path: Path, timeout: float = 10.0) -> None:
        """Initialize file lock.

        Args:
            file_path: Path to the file to lock.
            timeout: Maximum seconds to wait for lock acquisition.
        """
        self.file_path = file_path
        self.timeout = timeout
        self._lock_fd = None

    def _acquire_lock(self) -> None:
        """Acquire exclusive lock on the lock file.

        Uses a separate .lock file alongside the target file.
        This works even if the target file doesn't exist yet.
        """
        lock_path = self._get_lock_path()

        # Ensure parent directory exists for lock file
        lock_parent = os.path.dirname(lock_path)
        if lock_parent and not os.path.exists(lock_parent):
            os.makedirs(lock_parent, exist_ok=True)

        # Open or create lock file
        self._lock_fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY)

        start_time = __import__("time").time()

        while True:
            try:
                if sys.platform == "win32":
                    # Windows: use msvcrt.locking()
                    msvcrt.locking(self._lock_fd, msvcrt.LK_NBLCK, 1)
                else:
                    # Unix: use fcntl.flock() with LOCK_EX | LOCK_NB
                    fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return  # Lock acquired
            except OSError as e:
                # Lock is held by another process
                if e.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise

                # Check timeout
                if __import__("time").time() - start_time >= self.timeout:
                    raise TimeoutError(
                        f"Could not acquire lock on {self.file_path} "
                        f"after {self.timeout} seconds"
                    ) from None

                # Small sleep before retry
                __import__("time").sleep(0.01)

    def _release_lock(self) -> None:
        """Release the file lock."""
        if self._lock_fd is not None:
            try:
                if sys.platform == "win32":
                    # Windows: unlock
                    msvcrt.locking(self._lock_fd, msvcrt.LK_UNLCK, 1)
                else:
                    # Unix: unlock
                    fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            except OSError:
                pass  # Ignore errors during release
            finally:
                os.close(self._lock_fd)
                self._lock_fd = None

    def _get_lock_path(self) -> str:
        """Get the path to the lock file.

        Uses a .lock file alongside the target file.
        """
        return str(self.file_path) + ".lock"

    def __enter__(self) -> FileLock:
        """Acquire lock when entering context."""
        self._acquire_lock()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Release lock when exiting context, even on error."""
        self._release_lock()


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

    def load(self) -> list[Todo]:
        if not self.path.exists():
            return []

        # Acquire lock for safe concurrent access
        with FileLock(self.path):
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

        Uses file locking to serialize concurrent writes and prevent data loss.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        # Acquire lock for safe concurrent access
        with FileLock(self.path):
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
