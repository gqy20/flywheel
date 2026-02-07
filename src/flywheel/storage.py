"""JSON-backed todo storage."""

from __future__ import annotations

import json
from pathlib import Path

from .todo import Todo


def _atomic_write(path: Path, content: str) -> None:
    """Write content to file atomically using temp file + rename.

    This ensures data integrity: if the process crashes during write,
    the original file remains intact.

    Args:
        path: Target file path.
        content: Content to write.
    """
    # Create temp file in same directory to ensure rename is atomic
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(content, encoding="utf-8")
    # Atomic rename: on POSIX, this overwrites target atomically
    temp_path.replace(path)


class TodoStorage:
    """Persistent storage for todos."""

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or ".todo.json")

    def load(self) -> list[Todo]:
        if not self.path.exists():
            return []

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Todo storage must be a JSON list")
        return [Todo.from_dict(item) for item in raw]

    def save(self, todos: list[Todo]) -> None:
        payload = [todo.to_dict() for todo in todos]
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        _atomic_write(self.path, content)

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
