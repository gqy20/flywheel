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


def _validate_path_is_safe(path: Path) -> None:
    """Validate that path is safe from path traversal attacks.

    This prevents path traversal attacks where users could specify paths like
    '../../../etc/passwd' to access files outside the intended workspace.

    Security model:
    - Relative paths (e.g., '../test.json', 'data/db.json') must resolve to CWD or subdirectories
    - Absolute paths are allowed but checked against known-safe directories

    Args:
        path: The path to validate.

    Raises:
        ValueError: If path contains null bytes or escapes the working directory.
    """
    path_str = str(path)

    # Check for null byte injection attacks
    if "\0" in path_str:
        raise ValueError(
            "Path contains null byte, which is not allowed. "
            "This protects against path injection attacks."
        )

    # Check if path is relative (doesn't start with / on Unix or drive letter on Windows)
    is_relative = not path.is_absolute()

    # Resolve to absolute path to normalize '../' and symlinks
    try:
        resolved_path = path.resolve()
    except OSError as e:
        raise ValueError(
            f"Cannot resolve path '{path}': {e}. "
            f"The path may be invalid or contain unsafe components."
        ) from e

    # For relative paths, verify they don't escape CWD
    if is_relative:
        # Get current working directory as absolute path
        cwd = Path.cwd().resolve()

        # Check if resolved path is within CWD
        try:
            resolved_path.relative_to(cwd)
        except ValueError:
            # Path escapes CWD - provide helpful error
            raise ValueError(
                f"Relative path '{path}' (resolves to '{resolved_path}') is outside the working directory '{cwd}'. "
                f"For security reasons, relative paths must be within the current working directory tree. "
                f"Use a relative path from the current directory (e.g., 'data/db.json') or an absolute path."
            ) from None

    # For absolute paths, do basic sanity checks but allow them
    # This allows tests to use tmp_path while still protecting against obvious attacks
    else:
        # Check for obviously malicious absolute paths (system directories)
        # We block paths that are under well-known system directories
        # But we allow subdirectories of /tmp for testing purposes
        path_parts = resolved_path.parts
        # Unix system paths
        if len(path_parts) > 0 and path_parts[0] == "/":
                if len(path_parts) < 2:
                    return  # Just root "/" - shouldn't happen but is safe

                second_level = path_parts[1]

                # Block well-known system directories (not tmp which has legitimate subdirs)
                # Note: /root is excluded as it's a user home directory (for root user)
                if second_level in (
                    "etc", "usr", "bin", "sbin", "var", "sys", "proc", "dev",
                    "boot", "opt", "srv", "run", "snap"
                ):
                    raise ValueError(
                        f"Absolute path '{path}' points to a system directory. "
                        f"For security reasons, database files cannot be stored in system directories."
                    )

                # For /tmp, block direct /tmp access but allow subdirectories
                # /tmp/test.json has 3 parts (/, tmp, test.json) - block it
                # /tmp/pytest-of-runner/test has 4+ parts - allow it
                if second_level == "tmp" and len(path_parts) <= 3:
                        raise ValueError(
                            f"Absolute path '{path}' points to the system temp directory. "
                            f"For security reasons, database files cannot be stored directly in /tmp. "
                            f"Use a subdirectory like /tmp/myapp/db.json or a relative path."
                        )
            # TODO: Add Windows system path checks if needed


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
        # Convert to Path and validate for security
        db_path = Path(path or ".todo.json")
        _validate_path_is_safe(db_path)
        self.path = db_path

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
