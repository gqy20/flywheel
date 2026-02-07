"""JSON-backed todo storage."""

from __future__ import annotations

import json
import warnings
from pathlib import Path

from .todo import Todo


class TodoStorage:
    """Persistent storage for todos."""

    def __init__(self, path: str | None = None) -> None:
        path = path or ".todo.json"
        self._validate_path(path)
        self.path = Path(path)

    def _validate_path(self, path: str) -> None:
        """Reject paths with '..' components to prevent directory traversal.

        Args:
            path: User-provided path string

        Raises:
            ValueError: If path contains '..' parent directory components
        """
        # Check for both Unix (../) and Windows (..\) style parent references
        if "../" in path or "..\\" in path or path.endswith("..") or path.startswith(".."):
            raise ValueError(f"path traversal not allowed: {path!r}")

        # Also resolve absolute paths and warn if they escape CWD
        resolved = Path(path).resolve()
        try:
            cwd = Path.cwd()
            if cwd not in resolved.parents and cwd != resolved:
                warnings.warn(
                    f"Path {path!r} is outside current working directory",
                    UserWarning,
                    stacklevel=3,
                )
        except RuntimeError:
            # Path.resolve() may raise RuntimeError on invalid paths
            pass

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
