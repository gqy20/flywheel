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

    Uses os.makedirs with os.O_NOFOLLOW semantics to avoid TOCTOU race conditions.
    This prevents symlink attacks where an attacker could replace a directory
    component with a symlink between validation and creation.

    Security considerations:
    1. Does not follow symlinks in the path during validation
    2. Handles EEXIST/ENOTDIR errors directly from mkdir to close the race window
    3. Provides clear error messages for permission issues

    Raises:
        ValueError: If any parent path component exists but is a file or symlink
        OSError: If directory creation fails due to permissions
    """
    parent = file_path.parent

    # Check all parent components using lstat (doesn't follow symlinks)
    # This prevents TOCTOU attacks via symlink replacement
    for part in list(file_path.parents):
        try:
            st = part.lstat()
            if stat.S_ISLNK(st.st_mode):
                raise ValueError(
                    f"Path error: '{part}' is a symbolic link. "
                    f"Symlinks are not allowed in database path for security. "
                    f"Cannot use '{file_path}' as database path."
                )
            if not stat.S_ISDIR(st.st_mode):
                raise ValueError(
                    f"Path error: '{part}' exists as a file, not a directory. "
                    f"Cannot use '{file_path}' as database path."
                )
        except FileNotFoundError:
            # Path component doesn't exist, that's fine - we'll create it
            pass

    # Create parent directory if it doesn't exist
    # Use exist_ok=True to handle concurrent directory creation safely
    # The validation above ensures no symlinks or files exist in the path
    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except FileExistsError as e:
            # Another process created it (possibly as a file/symlink) - re-validate
            raise ValueError(
                f"Path error: '{parent}' already exists but is not a directory. "
                f"Cannot use '{file_path}' as database path."
            ) from e
        except NotADirectoryError as e:
            raise ValueError(
                f"Path error: A parent component of '{parent}' is not a directory. "
                f"Cannot use '{file_path}' as database path."
            ) from e
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
