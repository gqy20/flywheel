"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import stat
import sys
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from .todo import Todo

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

    def __init__(self, path: str | None = None, *, use_locking: bool = True) -> None:
        """Initialize TodoStorage.

        Args:
            path: Path to the JSON storage file. Defaults to ".todo.json".
            use_locking: Whether to use file locking for concurrent access.
                         Defaults to True for safe multi-process writes.
        """
        self.path = Path(path or ".todo.json")
        self.use_locking = use_locking

    @contextmanager
    def _acquire_lock(self) -> Generator[None]:
        """Acquire an exclusive file lock for safe concurrent writes.

        Uses platform-specific locking:
        - Unix: fcntl.flock with LOCK_EX (exclusive lock)
        - Windows: msvcrt.locking with LK_NBLCK (non-blocking exclusive lock)

        The lock is automatically released when exiting the context.
        """
        if not self.use_locking:
            yield
            return

        # Ensure parent directory exists before creating lock file
        _ensure_parent_directory(self.path)

        lock_file_path = self.path.with_suffix(self.path.suffix + ".lock")
        lock_fd = None

        try:
            # Open/create lock file
            lock_fd = os.open(
                str(lock_file_path),
                os.O_CREAT | os.O_RDWR,
                stat.S_IRUSR | stat.S_IWUSR,  # 0o600
            )

            if sys.platform == "win32":
                # Windows: use msvcrt.locking
                import msvcrt

                # Try to acquire lock (blocking)
                # msvcrt.locking doesn't have a blocking mode, so we poll
                max_attempts = 100
                for _ in range(max_attempts):
                    try:
                        msvcrt.locking(lock_fd, msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        # Lock is held by another process, wait and retry
                        import time

                        time.sleep(0.01)
                else:
                    # Failed to acquire lock after max attempts
                    raise OSError(f"Could not acquire lock on {lock_file_path}")
            else:
                # Unix: use fcntl.flock
                import fcntl

                fcntl.flock(lock_fd, fcntl.LOCK_EX)

            yield

        finally:
            # Release lock and close file
            if lock_fd is not None:
                try:
                    if sys.platform == "win32":
                        import msvcrt

                        msvcrt.locking(lock_fd, msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(lock_fd, fcntl.LOCK_UN)
                finally:
                    os.close(lock_fd)

                    # Clean up lock file (best effort)
                    with contextlib.suppress(OSError):
                        os.unlink(lock_file_path)

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
        """Save todos to file atomically with optional file locking.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        When use_locking=True (default), uses file locking to serialize
        concurrent writes from multiple processes.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        with self._acquire_lock():
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
