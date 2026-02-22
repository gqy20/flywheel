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

# Default lock timeout in seconds
_DEFAULT_LOCK_TIMEOUT = 30.0


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
        self,
        path: str | None = None,
        use_lock: bool = False,
        lock_timeout: float = _DEFAULT_LOCK_TIMEOUT,
    ) -> None:
        """Initialize storage.

        Args:
            path: Path to the JSON file. Defaults to '.todo.json'.
            use_lock: If True, use file locking for concurrent access safety.
            lock_timeout: Timeout in seconds for acquiring lock. Default 30s.
        """
        self.path = Path(path or ".todo.json")
        self.use_lock = use_lock
        self.lock_timeout = lock_timeout
        self._lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    def _acquire_lock(self, exclusive: bool = True) -> int | None:
        """Acquire file lock for concurrent access.

        Args:
            exclusive: If True, acquire exclusive lock (for writes).
                      If False, acquire shared lock (for reads).

        Returns:
            File descriptor of lock file, or None if locking disabled.

        Raises:
            TimeoutError: If lock cannot be acquired within timeout.
        """
        if not self.use_lock:
            return None

        # Ensure parent directory exists for lock file
        _ensure_parent_directory(self._lock_path)

        # Open lock file (create if doesn't exist)
        fd = os.open(
            str(self._lock_path),
            os.O_RDWR | os.O_CREAT,
            stat.S_IRUSR | stat.S_IWUSR,  # 0o600
        )

        lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH

        # Try to acquire lock with timeout using LOCK_NB + polling
        # This is more portable than using signal-based timeout
        import time

        start_time = time.monotonic()
        while True:
            try:
                fcntl.flock(fd, lock_type | fcntl.LOCK_NB)
                return fd
            except (BlockingIOError, OSError):
                elapsed = time.monotonic() - start_time
                if elapsed >= self.lock_timeout:
                    os.close(fd)
                    raise TimeoutError(
                        f"Could not acquire lock on {self._lock_path} "
                        f"within {self.lock_timeout}s"
                    ) from None
                time.sleep(0.01)  # Brief sleep before retry

    def _release_lock(self, fd: int | None) -> None:
        """Release file lock.

        Args:
            fd: File descriptor returned by _acquire_lock, or None.
        """
        if fd is None:
            return

        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        except OSError:
            # Lock already released or file closed
            pass

    def load(self) -> list[Todo]:
        """Load todos from file.

        If use_lock=True, acquires a shared lock during read to ensure
        consistent reads when other processes may be writing.

        Returns:
            List of Todo objects, empty list if file doesn't exist.
        """
        # Acquire shared lock for reading (if enabled)
        lock_fd = self._acquire_lock(exclusive=False)
        try:
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
        finally:
            self._release_lock(lock_fd)

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        If use_lock=True, acquires an exclusive lock during write to prevent
        concurrent write conflicts (last-writer-wins data loss).

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        # Acquire exclusive lock for writing (if enabled)
        lock_fd = self._acquire_lock(exclusive=True)
        try:
            self._save_unlocked(todos)
        finally:
            self._release_lock(lock_fd)

    def _save_unlocked(self, todos: list[Todo]) -> None:
        """Internal save without locking - called by save() after lock acquired."""
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
