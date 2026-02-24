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
        self._next_id: int | None = None  # Cached next_id counter

    def load(self) -> list[Todo]:
        if not self.path.exists():
            self._next_id = 1
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

        # Support both new object format and legacy list format
        if isinstance(raw, list):
            # Legacy format: just a list of todos
            todos = [Todo.from_dict(item) for item in raw]
            # Initialize next_id from max id in list
            self._next_id = (max((t.id for t in todos), default=0) + 1) if todos else 1
            return todos

        if isinstance(raw, dict):
            # New format: {"todos": [...], "_next_id": N}
            if "todos" not in raw:
                raise ValueError("Todo storage object must have 'todos' key")
            todo_list = raw["todos"]
            if not isinstance(todo_list, list):
                raise ValueError("'todos' must be a JSON list")
            todos = [Todo.from_dict(item) for item in todo_list]

            # Load or initialize next_id counter
            stored_next_id = raw.get("_next_id")
            if isinstance(stored_next_id, int) and stored_next_id > 0:
                self._next_id = stored_next_id
            else:
                # Fallback: initialize from max id in list
                self._next_id = (
                    (max((t.id for t in todos), default=0) + 1) if todos else 1
                )
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

        # Ensure _next_id is initialized and at least greater than any existing ID
        if self._next_id is None:
            self._next_id = (
                (max((t.id for t in todos), default=0) + 1) if todos else 1
            )
        else:
            # Make sure _next_id is always >= max_id + 1
            max_id = max((t.id for t in todos), default=0) if todos else 0
            if self._next_id <= max_id:
                self._next_id = max_id + 1

        # Save in new format with next_id counter
        payload = {"todos": [todo.to_dict() for todo in todos], "_next_id": self._next_id}
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
        """Return the next unique ID for a new todo.

        Uses a persistent counter to ensure IDs are never reused,
        even after deletions. The counter is stored in the JSON file
        alongside the todos.

        Args:
            todos: Current list of todos (used for fallback if counter not initialized).

        Returns:
            The next unique ID that has not been used before.
        """
        if self._next_id is None:
            # Fallback: compute from current list (for when load() wasn't called)
            self._next_id = (
                (max((t.id for t in todos), default=0) + 1) if todos else 1
            )

        result = self._next_id
        # Increment the counter for next time
        self._next_id += 1
        return result
