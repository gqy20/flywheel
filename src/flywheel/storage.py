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
        """Validate that the path is safe and resolve it.

        Prevents directory traversal attacks via relative paths with '..'.
        Absolute paths are allowed since they are an explicit user choice.

        Args:
            path: The user-provided path string

        Returns:
            The resolved Path object

        Raises:
            ValueError: If the relative path attempts to traverse outside the working directory
        """
        input_path = Path(path)

        # Check for '..' in path components to prevent directory traversal
        # Only check relative paths - absolute paths are an explicit user choice
        if not input_path.is_absolute():
            # For relative paths, check if any component contains '..'
            if ".." in input_path.parts:
                raise ValueError(
                    f"Path '{path}' contains '..' which is not allowed for security reasons. "
                    "Use a path within the current directory or an absolute path."
                )
            # Verify that resolving the path stays within or under current directory
            resolved = input_path.resolve()
            cwd = Path.cwd()
            try:
                resolved.relative_to(cwd)
            except ValueError as exc:
                raise ValueError(
                    f"Path '{path}' resolves outside the working directory. "
                    "Paths with '..' components are not allowed for security reasons."
                ) from exc
            return resolved

        # Absolute paths are allowed as-is (explicit user choice)
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
