"""JSON-backed todo storage."""

from __future__ import annotations

import json
from pathlib import Path

from .todo import Todo


class TodoStorage:
    """Persistent storage for todos."""

    def __init__(self, path: str | None = None) -> None:
        input_path = Path(path or ".todo.json")
        self.path = self._validate_path(input_path)

    @staticmethod
    def _validate_path(path: Path) -> Path:
        """Validate path is safe from directory traversal attacks.

        Prevents directory traversal attacks by detecting and rejecting
        paths containing parent directory reference sequences ('../' or '..\\').

        Args:
            path: User-provided path to validate

        Returns:
            The validated path (may be relative or absolute)

        Raises:
            ValueError: If path contains parent directory traversal sequences
        """
        path_str = str(path)

        # Check for path traversal patterns in the input string
        # This catches both '../' and '..\\' sequences before any path normalization
        if "../" in path_str or "..\\" in path_str:
            raise ValueError(
                "Invalid path: parent directory references ('../' or '..\\') are not allowed for security reasons"
            )

        # Additional check: reject paths that start with '..' (would be normalized to parent)
        parts = Path(path_str).parts
        if any(p == ".." for p in parts):
            raise ValueError(
                "Invalid path: parent directory references are not allowed for security reasons"
            )

        # Return path as-is (could be relative or absolute)
        # Absolute paths are allowed for legitimate use cases (e.g., tests, explicit config)
        return path

    def load(self) -> list[Todo]:
        if not self.path.exists():
            return []

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Todo storage must be a JSON list")
        return [Todo.from_dict(item) for item in raw]

    def save(self, todos: list[Todo]) -> None:
        payload = [todo.to_dict() for todo in todos]
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
