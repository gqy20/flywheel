"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path

from .todo import Todo

# Maximum JSON file size to prevent DoS attacks (10MB)
_MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024


def _ensure_parent_directory(file_path: Path) -> None:
    """Safely ensure parent directory exists for file_path.

    Validates that:
    1. All parent path components either don't exist or are directories (not files)
    2. Creates parent directories if needed
    3. Provides clear error messages for permission issues

    Raises:
        ValueError: If any parent path component exists but is a file
        OSError: If directory creation fails due to permissions
    """
    parent = file_path.parent

    # Check all parent components (excluding the file itself) for file-as-directory confusion
    # This handles cases like: /path/to/file.json/subdir/db.json
    # where 'file.json' exists as a file but we need it to be a directory
    for part in list(file_path.parents):  # Only check parents, not file_path itself
        if part.exists() and not part.is_dir():
            raise ValueError(
                f"Path error: '{part}' exists as a file, not a directory. "
                f"Cannot use '{file_path}' as database path."
            )

    # Create parent directory if it doesn't exist
    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=False)  # exist_ok=False since we validated above
        except OSError as e:
            raise OSError(
                f"Failed to create directory '{parent}': {e}. "
                f"Check permissions or specify a different location with --db=path/to/db.json"
            ) from e


class TodoStorage:
    """Persistent storage for todos."""

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or ".todo.json")

    def load(self) -> list[Todo]:
        if not self.path.exists():
            return []

        # Security: Check file size before loading to prevent DoS
        file_size = self.path.stat().st_size
        if file_size > _MAX_JSON_SIZE_BYTES:
            size_mb = file_size / (1024 * 1024)
            limit_mb = _MAX_JSON_SIZE_BYTES / (1024 * 1024)
            raise ValueError(
                f"JSON file too large ({size_mb:.1f}MB > {limit_mb:.0f}MB limit). "
                f"This protects against denial-of-service attacks."
            )

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in '{self.path}': {e.msg}. "
                f"Check line {e.lineno}, column {e.colno}."
            ) from e

        if not isinstance(raw, list):
            raise ValueError("Todo storage must be a JSON list")
        return [Todo.from_dict(item) for item in raw]

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

        payload = [todo.to_dict() for todo in todos]
        content = json.dumps(payload, ensure_ascii=False, indent=2)

        # Create temp file in same directory as target for atomic rename
        # Use tempfile.mkstemp for unpredictable name and O_EXCL semantics
        fd, temp_path = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            text=False,  # We'll write binary data to control encoding
        )

        try:
            # Set restrictive permissions (owner read/write only)
            # This protects against other users reading temp file before rename
            os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)  # 0o600 (rw-------)

            # Write content with proper encoding
            # Use os.write instead of Path.write_text for more control
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)

            # Atomic rename (os.replace is atomic on both Unix and Windows)
            os.replace(temp_path, self.path)
        except OSError:
            # Clean up temp file on error
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
            raise

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1

    def validate(self) -> tuple[bool, str | None]:
        """Validate the JSON file integrity.

        Returns:
            A tuple of (is_valid, error_message) where:
            - is_valid: True if file is valid or doesn't exist, False otherwise
            - error_message: None if valid, otherwise a description of the error
        """
        if not self.path.exists():
            # Nonexistent file is valid (empty state)
            return True, None

        try:
            content = self.path.read_text(encoding="utf-8")
        except OSError as e:
            return False, f"Cannot read file: {e}"

        # Check file size before parsing
        file_size = len(content.encode("utf-8"))
        if file_size > _MAX_JSON_SIZE_BYTES:
            size_mb = file_size / (1024 * 1024)
            limit_mb = _MAX_JSON_SIZE_BYTES / (1024 * 1024)
            return False, f"File too large ({size_mb:.1f}MB > {limit_mb:.0f}MB limit)"

        try:
            raw = json.loads(content)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}"

        if not isinstance(raw, list):
            return False, "Todo storage must be a JSON list"

        # Validate each todo item
        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                return False, f"Todo item {i} is not a JSON object"
            if "id" not in item:
                return False, f"Todo item {i} missing required field 'id'"
            if "text" not in item:
                return False, f"Todo item {i} missing required field 'text'"

        return True, None

    def repair(self) -> list[Todo]:
        """Attempt to repair a corrupted JSON file.

        Creates a backup of the original file before attempting repair.
        Uses partial parsing strategies to extract valid todo objects.

        Returns:
            A list of recovered Todo objects (may be empty).
        """
        if not self.path.exists():
            return []

        # Create backup before attempting repair
        backup_path = self.path.with_suffix(self.path.suffix + ".recovered.json")
        try:
            import shutil

            shutil.copy2(self.path, backup_path)
        except OSError:
            # Continue without backup if copy fails
            pass

        content = self.path.read_text(encoding="utf-8")
        recovered_todos = self._extract_valid_todos(content)

        # Save recovered todos to file
        self.save(recovered_todos)

        return recovered_todos

    def _extract_valid_todos(self, content: str) -> list[Todo]:
        """Extract valid todo objects from potentially corrupted JSON content.

        Args:
            content: The potentially corrupted JSON content

        Returns:
            A list of successfully parsed Todo objects
        """
        recovered: list[Todo] = []

        # Strategy 1: Try parsing as-is (might be valid with trailing comma)
        try:
            # Fix trailing comma issue
            normalized = re.sub(r",\s*([}\]])", r"\1", content)
            raw = json.loads(normalized)
            if isinstance(raw, list):
                return self._parse_todo_list(raw)
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 2: Extract individual objects using regex
        # Find JSON objects with "id" and "text" fields
        pattern = r'\{\s*"id"\s*:\s*\d+\s*,\s*"text"\s*:\s*"(?:[^"\\]|\\.)*"\s*(?:,\s*(?:"done"|"created_at"|"updated_at")\s*:\s*[^,}]*\s*)*\}'
        matches = re.finditer(pattern, content)

        for match in matches:
            obj_str = match.group(0)
            try:
                obj = json.loads(obj_str)
                if isinstance(obj, dict) and "id" in obj and "text" in obj:
                    todo = Todo.from_dict(obj)
                    recovered.append(todo)
            except (json.JSONDecodeError, ValueError):
                continue

        return recovered

    def _parse_todo_list(self, raw: list) -> list[Todo]:
        """Parse a list of todo dicts into Todo objects.

        Args:
            raw: List of dictionaries

        Returns:
            List of Todo objects (skips invalid entries)
        """
        todos = []
        for item in raw:
            try:
                todo = Todo.from_dict(item)
                todos.append(todo)
            except ValueError:
                # Skip invalid entries
                continue
        return todos
