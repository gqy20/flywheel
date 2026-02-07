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
        """Validate path is safe and resolve it.

        Args:
            path: User-provided path string

        Returns:
            Resolved Path object

        Raises:
            ValueError: If path contains directory traversal patterns
        """
        path_obj = Path(path)

        # Check for obvious traversal patterns before resolving
        # This prevents both '../' and '..\' (Windows style) attacks
        parts = path_obj.parts
        for part in parts:
            if part == "..":
                raise ValueError(f"Path traversal detected: '{path}' contains parent directory reference")

        # Resolve the path to normalize it (follows symlinks, eliminates redundant components)
        resolved = path_obj.resolve()

        # Double-check: after resolution, ensure no parent directory references remain
        # This catches edge cases like 'foo/../..' that resolve to parent
        try:
            resolved.relative_to(Path.cwd().resolve())
        except ValueError:
            # If path is outside CWD, verify it doesn't use parent traversal
            # to get there (absolute paths are OK, relative ones with '..' are not)
            if not path_obj.is_absolute():
                # Relative path that escapes CWD is suspicious
                resolved_str = str(resolved)
                cwd_str = str(Path.cwd().resolve())
                if not resolved_str.startswith(cwd_str):
                    raise ValueError(
                        f"Path '{path}' resolves outside current working directory"
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
