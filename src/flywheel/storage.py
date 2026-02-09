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

# Current schema version for the todo storage format
# Increment this when making breaking changes to the JSON format
CURRENT_SCHEMA_VERSION = 1

# Migration registry for converting old schema versions to current
# Format: {version: migration_function(data_dict) -> data_dict}
_MIGRATION_REGISTRY: dict[int, callable] = {}


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

        # Handle new schema format with versioning
        if isinstance(raw, dict):
            # Validate schema version
            if "_version" not in raw:
                raise ValueError(
                    "Missing required '_version' field in todo storage. "
                    "This file may be corrupted or from an incompatible version."
                )

            version = raw["_version"]
            if not isinstance(version, int) or version < 1:
                raise ValueError(
                    f"Invalid schema version: {version!r}. "
                    f"Version must be a positive integer."
                )

            if version > CURRENT_SCHEMA_VERSION:
                raise ValueError(
                    f"Schema version mismatch: file has version {version}, "
                    f"but this version of flywheel only supports up to version {CURRENT_SCHEMA_VERSION}. "
                    f"Please upgrade flywheel to open this file."
                )

            # If version matches, extract todos
            if version == CURRENT_SCHEMA_VERSION:
                todos_data = raw.get("todos", [])
            else:
                # Version is older than current - would run migrations here
                # For now, we only support version 1
                raise ValueError(
                    f"Legacy schema version {version} detected. "
                    f"Automatic migration is not yet implemented."
                )

            return [Todo.from_dict(item) for item in todos_data]

        # Handle legacy format (plain list without versioning)
        if isinstance(raw, list):
            raise ValueError(
                "Legacy todo format detected (JSON list without schema version). "
                "This file format is no longer supported. "
                "Please use a version of flywheel that supports legacy format to migrate your data."
            )

        raise ValueError("Todo storage must be a JSON object with '_version' and 'todos' keys")

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

        # Wrap todos in schema object with version
        payload = {
            "_version": CURRENT_SCHEMA_VERSION,
            "todos": [todo.to_dict() for todo in todos],
        }
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
