"""JSON-backed todo storage."""

from __future__ import annotations

import json
import os
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

    @staticmethod
    def _validate_item(item: dict, index: int) -> None:
        """Validate a single todo item from JSON.

        Args:
            item: The parsed JSON dict to validate
            index: The index of the item in the list (for error messages)

        Raises:
            ValueError: If the item is invalid, with a clear error message
        """
        # Check that item is a dict
        if not isinstance(item, dict):
            raise ValueError(
                f"Invalid todo at index {index}: expected object, got {type(item).__name__}"
            )

        # Check required fields
        required_fields = {"id", "text"}
        missing_fields = required_fields - item.keys()
        if missing_fields:
            missing_str = ", ".join(repr(f) for f in sorted(missing_fields))
            raise ValueError(
                f"Invalid todo at index {index}: missing required field(s): {missing_str}"
            )

        # Validate id field type (must be convertible to int)
        try:
            int(item["id"])
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Invalid todo at index {index}: 'id' must be a number, got {type(item['id']).__name__}"
            ) from e

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

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Todo storage must be a JSON list")

        # Validate each item before creating Todo objects
        for i, item in enumerate(raw):
            self._validate_item(item, i)

        return [Todo.from_dict(item) for item in raw]

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.
        """
        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

        payload = [todo.to_dict() for todo in todos]
        content = json.dumps(payload, ensure_ascii=False, indent=2)

        # Create temp file in same directory as target for atomic rename
        temp_path = self.path.with_name(f".{self.path.name}.tmp")

        # Write to temp file first
        temp_path.write_text(content, encoding="utf-8")

        # Atomic rename (os.replace is atomic on both Unix and Windows)
        os.replace(temp_path, self.path)

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
