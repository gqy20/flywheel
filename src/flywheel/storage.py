"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import os
import stat
import tempfile
from collections.abc import Callable
from pathlib import Path

from .todo import Todo

# Maximum JSON file size to prevent DoS attacks (10MB)
_MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024

# Current schema version
_CURRENT_SCHEMA_VERSION = 1


# Migration registry: maps from version -> (version, migration_function)
# migration_function takes raw JSON dict and returns migrated dict
_MIGRATION_REGISTRY: dict[int, tuple[int, Callable[[dict], dict]]] = {}


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

    def _validate_and_migrate_schema(self, raw: dict) -> dict:
        """Validate schema version and apply migrations if needed.

        Args:
            raw: The parsed JSON data as a dict

        Returns:
            The migrated data dict

        Raises:
            ValueError: If version is missing, invalid, or unsupported
        """
        if "_version" not in raw:
            raise ValueError(
                "Schema version is missing. The data file may be outdated or corrupted. "
                f"Expected version {_CURRENT_SCHEMA_VERSION}. "
                "Please check your data file or reinitialize."
            )

        try:
            version = int(raw["_version"])
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Invalid schema version: {raw['_version']!r}. "
                f"Version must be an integer."
            ) from e

        if version > _CURRENT_SCHEMA_VERSION:
            raise ValueError(
                f"Schema version {version} is newer than supported version {_CURRENT_SCHEMA_VERSION}. "
                "This data was created with a newer version of the application. "
                "Please update to the latest version."
            )

        if version < _CURRENT_SCHEMA_VERSION:
            # Apply migrations
            current = raw
            for v in range(version, _CURRENT_SCHEMA_VERSION):
                if v in _MIGRATION_REGISTRY:
                    target_version, migrate_fn = _MIGRATION_REGISTRY[v]
                    current = migrate_fn(current)
                else:
                    raise ValueError(
                        f"No migration found from version {v} to {target_version}. "
                        "Cannot load this data file."
                    )
            return current

        return raw

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

        # Validate and migrate schema (handles both old list format and new dict format)
        if isinstance(raw, list):
            # Old format without version - this is outdated
            raise ValueError(
                "Schema version is missing. The data file appears to be in an outdated format "
                f"(plain list). Current version is {_CURRENT_SCHEMA_VERSION}. "
                "Please reinitialize or migrate your data."
            )

        if not isinstance(raw, dict):
            raise ValueError("Todo storage must be a JSON object or list")

        # Validate schema version and apply migrations
        raw = self._validate_and_migrate_schema(raw)

        # Extract todos list
        if "todos" not in raw:
            raise ValueError("Todo storage missing 'todos' field")

        if not isinstance(raw["todos"], list):
            raise ValueError("Todo storage 'todos' field must be a list")

        return [Todo.from_dict(item) for item in raw["todos"]]

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

        # Structure data with schema version
        payload = {
            "_version": _CURRENT_SCHEMA_VERSION,
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
