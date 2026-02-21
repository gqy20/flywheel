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
    """Persistent storage for todos.

    Args:
        path: Path to the JSON storage file. Defaults to ".todo.json".
        cache_enabled: If True, cache loaded todos in memory to reduce disk I/O.
            The cache is automatically invalidated on save() and when file mtime
            changes externally. Default is False for backward compatibility.
    """

    def __init__(
        self, path: str | None = None, cache_enabled: bool = False
    ) -> None:
        self.path = Path(path or ".todo.json")
        self.cache_enabled = cache_enabled
        self._cache: list[Todo] | None = None
        self._cache_mtime: float | None = None

    def _get_file_mtime(self) -> float | None:
        """Get file modification time, or None if file doesn't exist."""
        if not self.path.exists():
            return None
        return self.path.stat().st_mtime

    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid based on mtime."""
        if self._cache is None:
            return False
        # Special case: cache_mtime is None means file didn't exist when cached
        if self._cache_mtime is None:
            # Cache is valid only if file still doesn't exist
            return not self.path.exists()
        current_mtime = self._get_file_mtime()
        # Cache is valid if mtime matches
        return current_mtime == self._cache_mtime

    def invalidate_cache(self) -> None:
        """Clear the in-memory cache.

        Safe to call even if cache is empty or file doesn't exist.
        """
        self._cache = None
        self._cache_mtime = None

    def load(self) -> list[Todo]:
        # Return cached data if valid
        if self.cache_enabled and self._is_cache_valid():
            return self._cache if self._cache is not None else []

        if not self.path.exists():
            # Cache the empty result
            if self.cache_enabled:
                self._cache = []
                self._cache_mtime = None
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

        todos = [Todo.from_dict(item) for item in raw]

        # Update cache if enabled
        if self.cache_enabled:
            self._cache = todos
            self._cache_mtime = self._get_file_mtime()

        return todos

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.

        Note: Invalidates the cache if caching is enabled.
        """
        # Invalidate cache before saving
        self.invalidate_cache()

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
