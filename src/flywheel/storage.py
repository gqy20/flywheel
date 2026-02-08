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
            A tuple of (is_valid, error_message). If valid, error_message is None.
            If file doesn't exist, it's considered valid (empty state).
        """
        if not self.path.exists():
            return True, None

        try:
            content = self.path.read_text(encoding="utf-8")
            # Check file size limit
            file_size = len(content.encode("utf-8"))
            if file_size > _MAX_JSON_SIZE_BYTES:
                size_mb = file_size / (1024 * 1024)
                limit_mb = _MAX_JSON_SIZE_BYTES / (1024 * 1024)
                return False, f"File too large ({size_mb:.1f}MB > {limit_mb:.0f}MB limit)"

            raw = json.loads(content)
            if not isinstance(raw, list):
                return False, "Todo storage must be a JSON list"

            # Try to parse each todo to ensure they're all valid
            for item in raw:
                Todo.from_dict(item)

            return True, None
        except json.JSONDecodeError as e:
            return False, f"Invalid json: {e.msg} at line {e.lineno}, column {e.colno}"
        except (ValueError, KeyError, TypeError) as e:
            return False, f"Invalid todo object: {e}"
        except OSError as e:
            return False, f"File read error: {e}"

    def repair(self) -> int:
        """Attempt to repair a corrupted JSON file.

        Creates a .recovered.json backup before attempting repair.
        Uses partial parsing strategies to extract valid todo objects.

        Returns:
            The number of valid todos recovered.
        """
        # If file doesn't exist, nothing to repair
        if not self.path.exists():
            return 0

        # Try to validate first - if valid, try to load and count todos
        is_valid, _ = self.validate()
        if is_valid:
            try:
                todos = self.load()
                return len(todos)
            except (ValueError, KeyError, TypeError):
                # JSON is valid but contains invalid todo objects
                # Fall through to recovery logic
                pass

        # Create backup of corrupted file
        backup_path = self.path.with_suffix(self.path.suffix + ".recovered.json")
        try:
            content = self.path.read_text(encoding="utf-8")
            backup_path.write_text(content, encoding="utf-8")
        except OSError:
            pass  # Continue even if backup fails
            # If we haven't read content yet, try now
            try:
                content = self.path.read_text(encoding="utf-8")
            except OSError:
                return 0

        # Attempt to recover valid todos using multiple strategies
        recovered_todos = self._recover_todos(content)

        # Save recovered data (empty list if recovery failed)
        self.save(recovered_todos)
        return len(recovered_todos)

    def _recover_todos(self, content: str) -> list[Todo]:
        """Attempt to recover valid todos from corrupted JSON content.

        Args:
            content: The potentially corrupted JSON content.

        Returns:
            A list of valid Todo objects (may be empty).
        """
        recovered: list[Todo] = []

        # Strategy 1: Try to parse as-is and filter out invalid objects
        recovered.extend(self._try_parse_and_filter(content))

        # Strategy 2: If that failed, try to extract individual JSON objects
        if not recovered:
            recovered.extend(self._extract_json_objects(content))

        # Strategy 3: Last resort - try to fix trailing commas
        if not recovered:
            recovered.extend(self._try_fix_trailing_commas(content))

        # Deduplicate by ID while preserving order
        seen_ids = set()
        unique_todos = []
        for todo in recovered:
            if todo.id not in seen_ids:
                seen_ids.add(todo.id)
                unique_todos.append(todo)

        return unique_todos

    def _try_parse_and_filter(self, content: str) -> list[Todo]:
        """Try to parse JSON and filter out objects that fail validation.

        Args:
            content: The JSON content to parse.

        Returns:
            A list of valid Todo objects.
        """
        todos: list[Todo] = []

        # Try standard JSON parsing
        try:
            raw = json.loads(content)
            if isinstance(raw, list):
                for item in raw:
                    try:
                        todos.append(Todo.from_dict(item))
                    except (ValueError, KeyError, TypeError):
                        # Skip invalid todo objects
                        continue
        except (json.JSONDecodeError, ValueError):
            pass

        return todos

    def _extract_json_objects(self, content: str) -> list[Todo]:
        """Try to extract individual JSON objects from corrupted content.

        This regex-based approach looks for JSON object patterns
        ({...}) even when the overall structure is invalid.

        Args:
            content: The corrupted content to scan.

        Returns:
            A list of valid Todo objects.
        """
        todos: list[Todo] = []

        # Pattern to match JSON objects: {...}
        # This handles nested braces by counting balanced pairs
        objects = self._extract_braced_content(content, "{", "}")

        for obj_str in objects:
            try:
                # Try to parse as JSON
                obj_data = json.loads(obj_str)
                # Try to create a Todo from it
                try:
                    todos.append(Todo.from_dict(obj_data))
                except (ValueError, KeyError, TypeError):
                    # Not a valid todo, skip
                    continue
            except json.JSONDecodeError:
                # Not valid JSON, skip
                continue

        return todos

    def _extract_braced_content(self, content: str, open_brace: str, close_brace: str) -> list[str]:
        """Extract content within matching braces from a string.

        Args:
            content: The content to scan.
            open_brace: The opening brace character.
            close_brace: The closing brace character.

        Returns:
            A list of strings containing braced content.
        """
        results: list[str] = []
        i = 0

        while i < len(content):
            # Find opening brace
            if content[i] != open_brace:
                i += 1
                continue

            # Track brace depth to find matching close
            depth = 0
            start = i

            while i < len(content):
                if content[i] == open_brace:
                    depth += 1
                elif content[i] == close_brace:
                    depth -= 1
                    if depth == 0:
                        # Found matching close
                        results.append(content[start:i + 1])
                        break
                i += 1

            i += 1

        return results

    def _try_fix_trailing_commas(self, content: str) -> list[Todo]:
        """Try to fix common trailing comma issues in JSON.

        Args:
            content: The JSON content with potential trailing commas.

        Returns:
            A list of valid Todo objects.
        """
        todos: list[Todo] = []

        # Fix trailing commas in arrays and objects
        # Pattern: ,\s*([}\]])
        # This replaces ", }" or ", ]" with just "}" or "]"
        try:
            fixed = re.sub(r",\s*([}\]])", r"\1", content)
            raw = json.loads(fixed)
            if isinstance(raw, list):
                for item in raw:
                    try:
                        todos.append(Todo.from_dict(item))
                    except (ValueError, KeyError, TypeError):
                        continue
        except (json.JSONDecodeError, ValueError):
            pass

        return todos
