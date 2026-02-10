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


def _validate_db_path(path: str | Path | None) -> Path:
    """Validate that the database path is within the allowed directory.

    This prevents path traversal attacks where users could specify paths like
    '../../../etc/passwd' to access files outside the intended directory.

    The primary security check is rejecting paths with '..' components,
    which prevents directory traversal attacks. Absolute paths are allowed
    for programmatic use (e.g., tests), but CLI usage has additional
    validation to reject absolute paths outside the working directory.

    Args:
        path: The user-provided database path.

    Returns:
        The validated and resolved Path object.

    Raises:
        ValueError: If the path contains traversal patterns.
    """
    path = Path(".todo.json") if path is None else Path(path)

    # Convert to string for pattern checking (handles both Path and str inputs)
    path_str = str(path)

    # The allowed base directory is the current working directory
    allowed_base = Path.cwd()

    # Check for backslashes (Windows-style path separators) - these could be
    # path traversal attempts on Windows or create weird filenames on Unix
    if '\\' in path_str:
        raise ValueError(
            f"Security error: Path '{path}' contains backslashes which are not allowed. "
            f"Use forward slashes (/) for path separators. "
            f"This protects against path traversal attacks."
        )

    # Check for path traversal patterns before resolving
    # This catches things like '../../../etc/passwd' before they resolve
    path_parts = Path(path).parts

    # Check for explicit '..' components - reject these regardless of whether
    # the path is relative or absolute. This is the key security check.
    if '..' in path_parts:
        raise ValueError(
            f"Security error: Path '{path}' contains '..' component which is not allowed. "
            f"This protects against path traversal attacks."
        )

    # Check for obfuscated dot patterns that could be used for evasion
    # (e.g., '....', '.....', etc.) - these are often used to bypass '..' checks
    for part in path_parts:
        if part and all(c == '.' for c in part):
            raise ValueError(
                f"Security error: Path '{path}' contains invalid component '{part}' which is not allowed. "
                f"This protects against path traversal attacks."
            )

    # Resolve to absolute path
    # For absolute paths, this just returns the resolved absolute path
    # For relative paths, this resolves relative to cwd
    resolved = path.resolve()

    # For relative paths, verify the resolved path is within the allowed base directory
    # This prevents relative path traversal (e.g., '../../../etc/passwd')
    if not path.is_absolute():
        try:
            resolved.relative_to(allowed_base)
        except ValueError:
            raise ValueError(
                f"Security error: Database path '{path}' resolves outside the allowed directory. "
                f"Path must be within the current working directory ('{allowed_base}'). "
                f"This protects against path traversal attacks."
            ) from None

    # For absolute paths, we've already verified no '..' components in the path,
    # which is the main security concern at the storage layer.
    # Additional validation for CLI-provided absolute paths happens in cli.py.

    return resolved


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
        self.path = _validate_db_path(path)

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
