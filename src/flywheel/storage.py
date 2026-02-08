"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
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
            A tuple of (is_valid: bool, error_message: str | None).
            Returns (True, None) if the file is valid JSON.
            Returns (False, error_message) if the file is corrupted or missing.
        """
        if not self.path.exists():
            return False, f"File not found: {self.path}"

        try:
            content = self.path.read_text(encoding="utf-8")
        except OSError as e:
            return False, f"Failed to read file: {e}"

        try:
            json.loads(content)
            return True, None
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}"

    def repair(self) -> list[Todo]:
        """Attempt to recover valid todos from a corrupted JSON file.

        Creates a .recovered.json backup before attempting repairs.
        Uses partial parsing strategies to extract valid JSON objects.

        Returns:
            A list of recovered Todo objects. May be empty if no valid todos found.
        """
        recovered: list[Todo] = []

        # Create backup of original corrupted file if it exists
        if self.path.exists():
            backup_path = Path(str(self.path) + ".recovered")
            with contextlib.suppress(OSError):
                shutil.copy2(self.path, backup_path)

            content = self.path.read_text(encoding="utf-8")
        else:
            content = ""

        # Attempt to recover valid todos from corrupted JSON
        recovered = self._recover_todos_from_corrupted(content)

        # Save recovered todos (creates valid empty array if no recovery)
        self.save(recovered)
        return recovered

    def _recover_todos_from_corrupted(self, content: str) -> list[Todo]:
        """Recover valid todos from corrupted JSON content.

        Uses several strategies:
        1. Try to fix trailing commas
        2. Extract complete JSON objects using regex
        3. Try parsing with missing closing brackets

        Args:
            content: The corrupted JSON content

        Returns:
            A list of recovered Todo objects
        """
        recovered: list[Todo] = []

        # Strategy 1: Try to fix trailing commas (common manual edit error)
        fixed = self._try_fix_trailing_commas(content)
        if fixed:
            try:
                parsed = json.loads(fixed)
                if isinstance(parsed, list):
                    return [Todo.from_dict(item) for item in parsed]
            except (json.JSONDecodeError, ValueError):
                pass

        # Strategy 2: Extract complete JSON objects using regex
        # Look for patterns like {"id": 1, "text": "...", "done": false}
        objects = self._extract_json_objects(content)
        for obj in objects:
            try:
                recovered.append(Todo.from_dict(obj))
            except (ValueError, KeyError):
                continue

        return recovered

    def _try_fix_trailing_commas(self, content: str) -> str | None:
        """Try to fix trailing commas in JSON.

        Removes trailing commas before closing brackets/braces.

        Args:
            content: The potentially corrupted JSON content

        Returns:
            Fixed content if successful, None if fixing didn't help
        """
        # Remove trailing comma before closing bracket or brace
        # Pattern: ",]" or ",}" -> "]" or "}"
        fixed = re.sub(r",(\s*[\]}])", r"\1", content)

        # Only return if we actually made changes
        return fixed if fixed != content else None

    def _extract_json_objects(self, content: str) -> list[dict]:
        """Extract complete JSON objects from corrupted content.

        Uses regex to find patterns that look like todo objects.

        Args:
            content: The corrupted JSON content

        Returns:
            A list of valid JSON dict objects
        """
        objects: list[dict] = []

        # Pattern to match {"id": ..., "text": "...", ...}
        # This is a best-effort approach and won't catch all cases
        pattern = r'\{[^{}]*"id"\s*:\s*\d+[^{}]*"text"\s*:\s*"[^"]*"[^{}]*\}'

        for match in re.finditer(pattern, content):
            try:
                obj = json.loads(match.group(0))
                if isinstance(obj, dict) and "id" in obj and "text" in obj:
                    objects.append(obj)
            except json.JSONDecodeError:
                continue

        return objects
