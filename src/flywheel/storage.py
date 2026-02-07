"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
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
        """Validate JSON file integrity.

        Returns:
            tuple[bool, str | None]: (is_valid, error_message)
                - is_valid: True if file is valid or doesn't exist, False otherwise
                - error_message: None if valid, otherwise a descriptive error message
        """
        if not self.path.exists():
            return True, None

        try:
            _ = self.path.stat().st_size
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                return False, "Todo storage must be a JSON list"
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}"
        except OSError as e:
            return False, f"File read error: {e}"

        return True, None

    def repair(self, backup_path: str | None = None) -> list[Todo]:
        """Attempt to repair corrupted JSON file and recover valid todos.

        Creates a backup of the original file before attempting repairs.
        Uses partial parsing strategies to extract valid JSON objects.

        Args:
            backup_path: Optional path for backup file. Defaults to path + ".recovered.json"

        Returns:
            list[Todo]: List of recovered todos. Empty list if no valid todos found.
        """
        if not self.path.exists():
            return []

        # Default backup path
        if backup_path is None:
            backup_path = str(self.path) + ".recovered.json"

        # Read original content for backup
        original_content = self.path.read_text(encoding="utf-8")

        # Create backup
        backup = Path(backup_path)
        backup.write_text(original_content, encoding="utf-8")

        # Try to recover todos using partial parsing
        recovered = self._extract_valid_todos(original_content)

        # Save recovered data
        self.save(recovered)

        return recovered

    def _extract_valid_todos(self, content: str) -> list[Todo]:
        """Extract valid todos from potentially corrupted JSON content.

        Uses multiple strategies:
        1. Try parsing as-is (for valid JSON)
        2. Try fixing trailing commas
        3. Extract individual JSON objects from content

        Args:
            content: Potentially corrupted JSON content

        Returns:
            list[Todo]: List of recovered todos
        """
        todos = []

        # Strategy 1: Try parsing as-is
        try:
            raw = json.loads(content)
            if isinstance(raw, list):
                for item in raw:
                    with contextlib.suppress(ValueError, TypeError, KeyError):
                        todos.append(Todo.from_dict(item))
                return todos
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 2: Try fixing trailing commas
        try:
            # Remove trailing commas before ] and }
            fixed = content.rstrip()
            # Remove trailing comma before closing bracket/brace
            import re
            fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
            raw = json.loads(fixed)
            if isinstance(raw, list):
                for item in raw:
                    with contextlib.suppress(ValueError, TypeError, KeyError):
                        todos.append(Todo.from_dict(item))
                return todos
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 3: Extract individual JSON objects using regex
        # This finds {...} patterns and tries to parse them as todos
        import re

        # Find all {...} objects
        object_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        for match in re.finditer(object_pattern, content):
            obj_str = match.group(0)
            try:
                obj = json.loads(obj_str)
                if isinstance(obj, dict):
                    todo = Todo.from_dict(obj)
                    todos.append(todo)
            except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                continue

        return todos
