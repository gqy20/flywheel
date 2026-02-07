"""JSON-backed todo storage."""

from __future__ import annotations

import json
from pathlib import Path

from .todo import Todo


class TodoStorage:
    """Persistent storage for todos."""

    def __init__(self, path: str | None = None) -> None:
        self.path = self._validate_and_resolve_path(path or ".todo.json")

    def _validate_and_resolve_path(self, path: str) -> Path:
        """Validate that the path is safe and within the allowed boundary.

        Prevents path traversal attacks by blocking paths that contain '..'
        components which could escape outside the intended directory.

        Args:
            path: The user-provided path string

        Returns:
            The validated and resolved Path object

        Raises:
            ValueError: If the path contains '..' components
        """
        input_path = Path(path)

        # Check if the path string contains '..' which could be used for path traversal
        # We check the string representation before resolution to catch traversal attempts
        path_str = str(path)
        if ".." in path_str:
            raise ValueError(
                f"Path '{path}' contains '..' component which could allow "
                "directory traversal. For security, paths must not contain '..'."
            )

        return input_path.resolve()

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
