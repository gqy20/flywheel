"""JSON-backed todo storage."""

from __future__ import annotations

import json
from pathlib import Path

from .todo import Todo


class TodoStorage:
    """Persistent storage for todos."""

    def __init__(self, path: str | None = None, validate: bool = False) -> None:
        self.path = Path(path or ".todo.json")
        self._validate = validate

    def _validate_path(self) -> None:
        """Validate that the path is safe and doesn't escape the working directory."""
        # Resolve to absolute path and follow symlinks
        resolved = self.path.resolve()

        # Get the current working directory
        cwd = Path.cwd().resolve()

        # Check if the resolved path is within the current working directory
        try:
            resolved.relative_to(cwd)
        except ValueError as err:
            raise ValueError(
                f"Path '{self.path}' resolves outside the current working directory. "
                "For security reasons, the database path must be within the working directory."
            ) from err

    def load(self) -> list[Todo]:
        if self._validate:
            self._validate_path()
        if not self.path.exists():
            return []

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Todo storage must be a JSON list")
        return [Todo.from_dict(item) for item in raw]

    def save(self, todos: list[Todo]) -> None:
        if self._validate:
            self._validate_path()
        payload = [todo.to_dict() for todo in todos]
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
