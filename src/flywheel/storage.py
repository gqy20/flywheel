"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import stat
import tempfile
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
    """Persistent storage for todos with load caching.

    The cache is invalidated based on file modification time (mtime).
    When load() is called:
    - If file hasn't been modified since last load, return cached data
    - If file has been modified (or cache is empty), read from file

    Cache can be disabled via use_cache=False for debug/testing scenarios.
    """

    def __init__(self, path: str | None = None, *, use_cache: bool = True) -> None:
        """Initialize TodoStorage.

        Args:
            path: Path to the JSON database file. Defaults to '.todo.json'.
            use_cache: If True (default), cache load() results in memory.
                       If False, always read from file (for debug mode).
        """
        self.path = Path(path or ".todo.json")
        self._use_cache = use_cache
        self._cache: list[Todo] | None = None
        self._cache_mtime: float | None = None

    def load(self) -> list[Todo]:
        """Load todos from storage, using cache if available and valid.

        Returns cached data if:
        - Cache is enabled (use_cache=True)
        - File exists and hasn't been modified since last load (mtime unchanged)

        Otherwise reads from file and updates cache.
        """
        if not self.path.exists():
            # Cache empty result for non-existent file
            if self._use_cache:
                self._cache = []
                self._cache_mtime = None
            return []

        # Get file stats for size check and mtime
        file_stat = self.path.stat()

        # Security: Check file size before loading to prevent DoS
        if file_stat.st_size > _MAX_JSON_SIZE_BYTES:
            size_mb = file_stat.st_size / (1024 * 1024)
            limit_mb = _MAX_JSON_SIZE_BYTES / (1024 * 1024)
            raise ValueError(
                f"JSON file too large ({size_mb:.1f}MB > {limit_mb:.0f}MB limit). "
                f"This protects against denial-of-service attacks."
            )

        # Check if we can use cached data
        current_mtime = file_stat.st_mtime
        if self._use_cache and self._cache is not None and self._cache_mtime == current_mtime:
            # Cache is valid - return cached data
            return self._cache

        # Cache miss or disabled - read from file
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in '{self.path}': {e.msg}. "
                f"Check line {e.lineno}, column {e.colno}."
            ) from e

        if not isinstance(raw, list):
            raise ValueError("Todo storage must be a JSON list")

        result = [Todo.from_dict(item) for item in raw]

        # Update cache if enabled
        if self._use_cache:
            self._cache = result
            self._cache_mtime = current_mtime

        return result

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.

        After successful save, the cache is automatically updated with the saved data.
        """
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

        # Update cache after successful save
        if self._use_cache:
            self._cache = todos
            self._cache_mtime = self.path.stat().st_mtime

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
