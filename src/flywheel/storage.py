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

    def _ensure_parent_dir(self) -> None:
        """Ensure the parent directory exists, handling edge cases safely.

        Raises:
            ValueError: If parent path exists but is a file, not a directory.
            PermissionError: If lacking permissions to create the directory.
        """
        parent = self.path.parent

        # Fast path: parent already exists as a directory
        if parent.is_dir():
            return

        # Edge case: parent exists but is a file (not a directory)
        if parent.exists():
            raise ValueError(
                f"Cannot create database: parent path '{parent}' exists but is a file, "
                f"not a directory. Please specify a different database path."
            )

        # Create parent directory with proper error handling
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except NotADirectoryError as e:
            # This occurs when a parent component in the path is a file, not a directory
            # E.g., trying to create "file.txt/nested/path" where "file.txt" is a file
            raise ValueError(
                f"Cannot create database: a parent component in the path '{parent}' "
                f"is a file, not a directory. Please check the path and specify a valid location."
            ) from e
        except PermissionError as e:
            raise PermissionError(
                f"Cannot create database directory '{parent}': permission denied. "
                f"Please check directory permissions or use a different path."
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
        return [Todo.from_dict(item) for item in raw]

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.
        """
        payload = [todo.to_dict() for todo in todos]
        content = json.dumps(payload, ensure_ascii=False, indent=2)

        # Ensure parent directory exists safely
        self._ensure_parent_dir()

        # Create temp file in same directory as target for atomic rename
        temp_path = self.path.with_name(f".{self.path.name}.tmp")

        # Write to temp file first
        temp_path.write_text(content, encoding="utf-8")

        # Atomic rename (os.replace is atomic on both Unix and Windows)
        os.replace(temp_path, self.path)

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
