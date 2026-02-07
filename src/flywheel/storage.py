"""JSON-backed todo storage."""

from __future__ import annotations

import json
from pathlib import Path

from .todo import Todo


class TodoStorage:
    """Persistent storage for todos."""

    def __init__(self, path: str | None = None) -> None:
        input_path = Path(path or ".todo.json")
        self.path = self._validate_path_safety(input_path)

    def _validate_path_safety(self, path: Path) -> Path:
        """Validate the storage path to prevent path traversal attacks.

        This method checks if the path would escape to sensitive system locations
        when resolved. The main security concern is preventing access to files like
        /etc/passwd via '../' components.

        Args:
            path: The input path to validate

        Returns:
            The resolved path (if safe)

        Raises:
            ValueError: If the path resolves to a sensitive system location
        """
        # Resolve the path to its absolute form
        resolved = path.resolve()

        # Define sensitive system paths that should never be accessed
        # We use specific paths rather than broad directories to avoid false positives
        sensitive_paths = [
            Path("/etc"),
            Path("/root"),
            Path("/var"),
            Path("/usr/bin"),
            Path("/usr/sbin"),
            Path("/bin"),
            Path("/sbin"),
            Path("/boot"),
            Path("/lib"),
            Path("/lib64"),
            Path("/sys"),
            Path("/proc"),
        ]

        # Check if the resolved path is within or equals a sensitive path
        for sensitive in sensitive_paths:
            # Use is_relative_to() which returns True/False instead of raising
            if resolved.is_relative_to(sensitive):
                raise ValueError(
                    f"Path traversal detected: '{path}' resolves to sensitive system location '{resolved}'. "
                    f"For security reasons, TodoStorage cannot access system directories."
                )

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
