"""JSON-backed todo storage."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .todo import Todo

# Maximum JSON file size to prevent DoS attacks (10MB)
_MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024


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

        # Security: Validate schema of each item before deserialization
        for idx, item in enumerate(raw):
            self._validate_item_schema(item, idx)

        return [Todo.from_dict(item) for item in raw]

    def _validate_item_schema(self, item: object, idx: int) -> None:
        """Validate that an item has the required schema structure.

        Raises ValueError with clear message if validation fails.
        """
        if not isinstance(item, dict):
            raise ValueError(
                f"Invalid todo data: item at index {idx} must be a JSON object, got {type(item).__name__}"
            )

        # Check required fields
        missing_fields = []
        if "id" not in item:
            missing_fields.append("'id'")
        if "text" not in item:
            missing_fields.append("'text'")

        if missing_fields:
            raise ValueError(
                f"Invalid todo data: item at index {idx} missing required field(s): {', '.join(missing_fields)}"
            )

        # Validate field types
        if not isinstance(item["id"], int):
            raise ValueError(
                f"Invalid todo data: item at index {idx} field 'id' must be an int, got {type(item['id']).__name__}"
            )

        if not isinstance(item["text"], str):
            raise ValueError(
                f"Invalid todo data: item at index {idx} field 'text' must be a string, got {type(item['text']).__name__}"
            )

        # Validate optional field types
        if "done" in item and not isinstance(item["done"], bool):
            raise ValueError(
                f"Invalid todo data: item at index {idx} field 'done' must be a bool, got {type(item['done']).__name__}"
            )

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.
        """
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
