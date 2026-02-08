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
        """Validate the integrity of the JSON file.

        Returns:
            A tuple of (is_valid, error_message) where:
            - is_valid: True if the file is valid or doesn't exist, False otherwise
            - error_message: None if valid, otherwise a descriptive error message
        """
        if not self.path.exists():
            return True, None

        # Security: Check file size before loading to prevent DoS
        try:
            file_size = self.path.stat().st_size
        except OSError as e:
            return False, f"Cannot access file: {e}"

        if file_size > _MAX_JSON_SIZE_BYTES:
            size_mb = file_size / (1024 * 1024)
            limit_mb = _MAX_JSON_SIZE_BYTES / (1024 * 1024)
            return False, f"JSON file too large ({size_mb:.1f}MB > {limit_mb:.0f}MB limit)"

        try:
            content = self.path.read_text(encoding="utf-8")
        except OSError as e:
            return False, f"Cannot read file: {e}"

        try:
            raw = json.loads(content)
        except json.JSONDecodeError as e:
            return (
                False,
                f"Invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}",
            )

        if not isinstance(raw, list):
            return False, "Todo storage must be a JSON list, not a dict or other type"

        # Validate each todo item has required structure
        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                return False, f"Todo at index {i} is not a JSON object"
            if "id" not in item:
                return False, f"Todo at index {i} missing required field 'id'"
            if "text" not in item:
                return False, f"Todo at index {i} missing required field 'text'"

        return True, None

    def repair(self) -> bool:
        """Attempt to repair a corrupted JSON file.

        Creates a .recovered.json backup of the original corrupted file,
        then attempts to extract valid todo objects using partial parsing.

        Returns:
            True if repair was successful (file is now valid),
            False if repair failed or file doesn't exist.
        """
        if not self.path.exists():
            return False

        # First, check if file is already valid
        is_valid, _ = self.validate()
        if is_valid:
            # No repair needed
            return True

        try:
            content = self.path.read_text(encoding="utf-8")
        except OSError:
            return False

        # Create backup before attempting repair
        backup_path = self.path.with_suffix(self.path.suffix + ".recovered.json")
        with contextlib.suppress(OSError):
            backup_path.write_text(content, encoding="utf-8")

        # Attempt repair strategies
        repaired_todos = self._attempt_repair(content)

        if repaired_todos is not None:
            # Successfully repaired - save the recovered data
            try:
                self.save(repaired_todos)
                return True
            except (ValueError, OSError):
                # Save failed, but we have a backup
                return False

        return False

    def _attempt_repair(self, content: str) -> list[Todo] | None:
        """Attempt to repair corrupted JSON content.

        Tries multiple strategies to extract valid todo objects from
        corrupted JSON. Returns None if all strategies fail.

        Args:
            content: The corrupted JSON content as a string

        Returns:
            A list of Todo objects if repair succeeds, None otherwise
        """
        import re

        # Strategy 1: Try to extract complete JSON objects using regex
        # This handles cases like trailing commas, partial truncation, etc.
        object_pattern = r'\{\s*"id"\s*:\s*\d+\s*,\s*"text"\s*:\s*"(?:[^"\\]|\\.)*"(?:\s*,\s*"done"\s*:\s*(?:true|false))?(?:\s*,\s*"created_at"\s*:\s*"[^"]*")?(?:\s*,\s*"updated_at"\s*:\s*"[^"]*")?\s*\}'

        matches = re.finditer(object_pattern, content)

        recovered_todos = []
        for match in matches:
            json_str = match.group(0)
            try:
                obj = json.loads(json_str)
                # Validate it's a proper todo object
                todo = Todo.from_dict(obj)
                recovered_todos.append(todo)
            except (json.JSONDecodeError, ValueError, KeyError):
                # Skip invalid matches
                continue

        if recovered_todos:
            return recovered_todos

        # Strategy 2: Try to fix trailing commas in array
        # Replace },] with }] and ] only if it's a trailing comma
        fixed_content = re.sub(r'},\s*\]', '}]', content)
        try:
            raw = json.loads(fixed_content)
            if isinstance(raw, list):
                return [Todo.from_dict(item) for item in raw]
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 3: Try to extract valid objects by finding braces
        # This is a fallback for more severe corruption
        brace_count = 0
        current_obj = ""
        obj_start = -1

        for i, char in enumerate(content):
            if char == "{":
                if brace_count == 0:
                    obj_start = i
                brace_count += 1
                current_obj += char
            elif char == "}":
                brace_count -= 1
                current_obj += char
                if brace_count == 0 and obj_start >= 0:
                    # Found a complete object
                    try:
                        obj = json.loads(current_obj)
                        if isinstance(obj, dict) and "id" in obj and "text" in obj:
                            todo = Todo.from_dict(obj)
                            recovered_todos.append(todo)
                    except (json.JSONDecodeError, ValueError):
                        pass
                    current_obj = ""
                    obj_start = -1
            elif brace_count > 0:
                current_obj += char

        if recovered_todos:
            return recovered_todos

        # All strategies failed
        return None
