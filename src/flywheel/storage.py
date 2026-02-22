"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from .todo import Todo

if TYPE_CHECKING:
    pass

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
        lock_timeout: Timeout in seconds for acquiring lock. None means wait forever.
    """

    def __init__(
        self,
        path: str | None = None,
        *,
        use_lock: bool = False,
        lock_timeout: float | None = None,
    ) -> None:
        self.path = Path(path or ".todo.json")
        self.use_lock = use_lock
        self.lock_timeout = lock_timeout

    def _get_lock_path(self) -> Path:
        """Get the path for the lock file (same directory, .<name>.lock)."""
        return self.path.parent / f".{self.path.name}.lock"

    @contextlib.contextmanager
    def _acquire_lock(self, exclusive: bool = True) -> None:
        """Acquire file lock for thread/process synchronization.

        Uses fcntl.flock for advisory locking on Unix systems.

        Args:
            exclusive: If True, acquire exclusive (write) lock. If False, shared (read) lock.

        Raises:
            TimeoutError: If lock cannot be acquired within lock_timeout seconds.
        """
        if not self.use_lock:
            yield
            return

        lock_path = self._get_lock_path()
        _ensure_parent_directory(lock_path)

        # Create or open lock file
        lock_fd = os.open(
            str(lock_path),
            os.O_CREAT | os.O_RDWR,
            stat.S_IRUSR | stat.S_IWUSR,  # 0o600
        )

        try:
            # Set lock type
            lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH

            if self.lock_timeout is not None:
                # Use LOCK_NB for non-blocking, retry with timeout
                import time

                start_time = time.monotonic()
                while True:
                    try:
                        fcntl.flock(lock_fd, lock_type | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        elapsed = time.monotonic() - start_time
                        if elapsed >= self.lock_timeout:
                            raise TimeoutError(
                                f"Could not acquire lock on {lock_path} within "
                                f"{self.lock_timeout} seconds"
                            ) from None
                        time.sleep(0.01)  # Short sleep before retry
            else:
                # Blocking wait forever
                fcntl.flock(lock_fd, lock_type)

            yield
        finally:
            # Release lock and close file descriptor
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

    def load(self) -> list[Todo]:
        """Load todos from file.

        With locking enabled, acquires a shared (read) lock during the operation.
        """
        with self._acquire_lock(exclusive=False):
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

        With locking enabled, acquires an exclusive (write) lock during the operation
        to prevent concurrent write conflicts.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        with self._acquire_lock(exclusive=True):
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
