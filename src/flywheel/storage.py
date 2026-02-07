"""JSON-backed todo storage."""

from __future__ import annotations

import json
from pathlib import Path

from .todo import Todo


class TodoStorage:
    """Persistent storage for todos."""

    def __init__(self, path: str | None = None) -> None:
        raw_path = path or ".todo.json"

        # Security: reject paths containing '..' to prevent directory traversal
        if ".." in raw_path:
            raise ValueError(
                "Storage path cannot contain '..' for security reasons. "
                "Path traversal is not allowed."
            )

        self.path = Path(raw_path)

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
