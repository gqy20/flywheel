"""JSON-backed todo storage."""

from __future__ import annotations

import json
from pathlib import Path

from .todo import Todo


class TodoStorage:
    """Persistent storage for todos."""

    def __init__(self, path: str | None = None, validate: bool = False) -> None:
        self.path = self._validate_and_resolve_path(path or ".todo.json") if validate else Path(path or ".todo.json")

    def _validate_and_resolve_path(self, path: str) -> Path:
        """
        Validate and resolve the database path to prevent path traversal attacks.

        Normalizes the path and checks that it doesn't escape the current
        working directory through parent directory references (../).

        Args:
            path: User-provided path string

        Returns:
            Resolved absolute Path

        Raises:
            ValueError: If path attempts to traverse outside current working directory
        """
        input_path = Path(path)

        # Resolve to absolute path (this normalizes ../ and symlinks)
        try:
            resolved = input_path.resolve(strict=False)
        except OSError as e:
            raise ValueError(f"Invalid path: {e}") from e

        # Get current working directory as the security boundary
        cwd = Path.cwd().resolve()

        # Check if the resolved path is within CWD
        # This prevents path traversal attacks like "../../../etc/passwd"
        try:
            resolved.relative_to(cwd)
        except ValueError:
            raise ValueError(
                f"Path '{path}' is outside the current working directory. "
                "Path traversal is not permitted for security reasons."
            ) from None

        return resolved

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
