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

        # Validate each item before deserialization to provide clear error messages
        for idx, item in enumerate(raw):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Todo item at index {idx} must be a JSON object, got {type(item).__name__}"
                )
            # Check required fields
            if "id" not in item:
                raise ValueError(f"Todo item at index {idx} missing required field 'id'")
            if "text" not in item:
                raise ValueError(f"Todo item at index {idx} missing required field 'text'")

            # Validate field types
            if not isinstance(item["id"], int):
                # Check if it's a float that's actually an integer value (e.g., 1.0)
                if isinstance(item["id"], float):
                    if item["id"] != int(item["id"]):
                        raise ValueError(
                            f"Todo item at index {idx} has 'id' with non-integer value {item['id']}"
                        )
                else:
                    raise ValueError(
                        f"Todo item at index {idx} has 'id' with wrong type {type(item['id']).__name__}, expected integer"
                    )
            if not isinstance(item["text"], str):
                raise ValueError(
                    f"Todo item at index {idx} has 'text' with wrong type {type(item['text']).__name__}, expected string"
                )
            # Optional field: done must be boolean if present
            if "done" in item and not isinstance(item["done"], bool):
                raise ValueError(
                    f"Todo item at index {idx} has 'done' with wrong type {type(item['done']).__name__}, expected boolean"
                )
            # Optional fields: created_at and updated_at must be strings if present
            for field in ("created_at", "updated_at"):
                if field in item and not isinstance(item[field], str):
                    raise ValueError(
                        f"Todo item at index {idx} has '{field}' with wrong type {type(item[field]).__name__}, expected string"
                    )

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
