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


def _validate_path_safety(file_path: Path) -> None:
    """Validate path doesn't escape intended directory via path traversal.

    Security: Prevents path traversal attacks by detecting when '..' components
    would resolve outside the intended directory context.

    For example:
    - '../../../etc/passwd' escapes the current working directory
    - '/home/user/project/../../../etc/passwd' escapes the project directory

    Raises:
        ValueError: If path contains '..' that escapes the intended directory
    """
    # Get the resolved (absolute, normalized) path
    resolved_path = file_path.resolve()

    # Check if the original path string contains '..' components
    path_str = str(file_path)
    if ".." not in path_str:
        return  # No path traversal characters, safe to proceed

    # For relative paths, check if resolved path is outside cwd
    if not file_path.is_absolute():
        cwd = Path.cwd().resolve()
        try:
            resolved_path.relative_to(cwd)
        except ValueError:
            # The resolved path is outside cwd - this is path traversal
            raise ValueError(
                f"Security: Path '{file_path}' escapes current working directory. "
                f"Path traversal is not allowed."
            ) from None
    else:
        # For absolute paths with '..', find the "intended" base directory
        # This is the longest prefix before any '..' appears
        parts = file_path.parts
        base_parts = []
        for part in parts:
            if part == "..":
                break  # Stop at first '..' - everything before is the intended base
            elif part != "/":  # Skip root marker on Unix
                base_parts.append(part)

        if base_parts:
            # Construct the intended base path
            base_path = Path("/") / Path(*base_parts)
            # Check if the resolved path is within this base
            try:
                resolved_path.relative_to(base_path)
            except ValueError:
                # The resolved path is outside the intended base - this is traversal
                raise ValueError(
                    f"Security: Path '{file_path}' escapes intended directory. "
                    f"Path traversal is not allowed."
                ) from None
        else:
            # Path starts with '..' from root - always traversal
            raise ValueError(
                f"Security: Path '{file_path}' escapes filesystem root. "
                f"Path traversal is not allowed."
            ) from None


def _ensure_parent_directory(file_path: Path) -> None:
    """Safely ensure parent directory exists for file_path.

    Validates that:
    1. Path doesn't escape current working directory (path traversal protection)
    2. All parent path components either don't exist or are directories (not files)
    3. Creates parent directories if needed
    4. Provides clear error messages for permission issues

    Raises:
        ValueError: If path escapes current working directory or if any parent
                    path component exists but is a file
        OSError: If directory creation fails due to permissions
    """
    # Security: Validate path doesn't escape current working directory
    _validate_path_safety(file_path)

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
        # Security: Validate path doesn't escape current working directory
        _validate_path_safety(self.path)

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
