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
    """Persistent storage for todos."""

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or ".todo.json")
        self._max_id: int | None = None  # Cached max_id for O(1) next_id()

    def load(self) -> list[Todo]:
        if not self.path.exists():
            self._max_id = 0
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

        # Handle new format: {"todos": [...], "max_id": N}
        if isinstance(raw, dict):
            if "todos" not in raw:
                raise ValueError("Todo storage dict must have 'todos' key")
            todo_list = raw["todos"]
            if not isinstance(todo_list, list):
                raise ValueError("'todos' must be a JSON list")
            # Use stored max_id if available, otherwise compute (for migration)
            self._max_id = raw.get("max_id")
            if self._max_id is None:
                # Migration: compute max_id from existing todos
                self._max_id = max((t.get("id", 0) for t in todo_list), default=0)
            return [Todo.from_dict(item) for item in todo_list]

        # Backward compatibility: old format was just a list [...]
        if isinstance(raw, list):
            todos = [Todo.from_dict(item) for item in raw]
            # Compute max_id from todos for backward compatibility
            self._max_id = max((todo.id for todo in todos), default=0)
            return todos

        raise ValueError("Todo storage must be a JSON list or object with 'todos' key")

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

        # Update max_id if any todo has higher id than current
        if self._max_id is None:
            self._max_id = max((todo.id for todo in todos), default=0)
        else:
            for todo in todos:
                if todo.id > self._max_id:
                    self._max_id = todo.id

        payload = {
            "todos": [todo.to_dict() for todo in todos],
            "max_id": self._max_id,
        }
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
        """Return the next available todo ID in O(1) time.

        Uses cached max_id instead of scanning all todos.
        """
        if self._max_id is None:
            # Fallback: compute from todos if max_id not cached
            self._max_id = max((todo.id for todo in todos), default=0)
        return self._max_id + 1
