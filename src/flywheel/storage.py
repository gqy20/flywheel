"""JSON-backed todo storage."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .todo import Todo

# Maximum JSON file size to prevent DoS attacks (10MB)
_MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024


def _validate_todo_item(item: object, index: int) -> dict:
    """Validate a single todo item from JSON.

    Args:
        item: The item to validate (should be a dict)
        index: The index of the item in the list (for error messages)

    Returns:
        The validated dict if valid

    Raises:
        ValueError: If the item is not a valid todo structure
    """
    if not isinstance(item, dict):
        raise ValueError(
            f"Todo item at index {index} must be a JSON object, got {type(item).__name__}"
        )

    # Check required fields
    required_fields = ["id", "text"]
    for field in required_fields:
        if field not in item:
            raise ValueError(
                f"Todo item at index {index} missing required field '{field}'"
            )

    # Validate field types
    if not isinstance(item["id"], int):
        raise ValueError(
            f"Todo item at index {index}: 'id' must be an integer, got {type(item['id']).__name__}"
        )

    if not isinstance(item["text"], str):
        raise ValueError(
            f"Todo item at index {index}: 'text' must be a string, got {type(item['text']).__name__}"
        )

    # Validate optional 'done' field
    if "done" in item and not isinstance(item["done"], bool):
        raise ValueError(
            f"Todo item at index {index}: 'done' must be a boolean, got {type(item['done']).__name__}"
        )

    # Note: Extra unknown fields are silently ignored by Todo.from_dict()
    # This is intentional for forward compatibility

    return item


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

        # Security: Validate each item's schema before deserialization
        validated_items = []
        for index, item in enumerate(raw):
            validated_items.append(_validate_todo_item(item, index))

        return [Todo.from_dict(item) for item in validated_items]

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
