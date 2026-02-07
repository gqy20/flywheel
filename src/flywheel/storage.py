"""JSON-backed todo storage."""

from __future__ import annotations

import json
from pathlib import Path

from .todo import Todo


def _validate_path_safety(path: Path, base_dir: Path | None = None) -> None:
    """Validate that path is within the allowed directory.

    Args:
        path: The path to validate
        base_dir: The base directory (defaults to current working directory)

    Raises:
        ValueError: If path escapes the allowed directory via ../, absolute path, or symlink
    """
    if base_dir is None:
        base_dir = Path.cwd()

    # Resolve to absolute path and check for path traversal
    resolved = path.resolve()
    base_resolved = base_dir.resolve()

    # Check if resolved path is within base directory
    try:
        resolved.relative_to(base_resolved)
    except ValueError as err:
        raise ValueError(
            f"Path '{path}' resolves outside allowed directory '{base_resolved}'. "
            f"Path traversal detected."
        ) from err


class TodoStorage:
    """Persistent storage for todos."""

    def __init__(self, path: str | None = None) -> None:
        input_path = Path(path or ".todo.json")
        _validate_path_safety(input_path)
        self.path = input_path

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
