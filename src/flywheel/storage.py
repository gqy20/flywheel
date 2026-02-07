"""JSON-backed todo storage."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .todo import Todo


def _get_temp_path(target_path: Path) -> Path:
    """Generate a unique temp file path for atomic writes.

    Includes process ID to avoid cross-process collisions that could
    cause data loss when multiple processes write to the same file.
    """
    pid = os.getpid()
    return target_path.with_name(f".{target_path.name}.{pid}.tmp")


def _cleanup_stale_temp_files(target_path: Path) -> None:
    """Clean up stale temp files from previous crashed processes.

    Removes any temp files matching the pattern .{target_path.name}.*.tmp
    that may have been left by crashed processes.

    Security: This prevents accumulation of orphaned temp files and ensures
    we don't collide with temp files from previous runs.
    """
    from contextlib import suppress

    parent = target_path.parent
    pattern = f".{target_path.name}.*.tmp"

    # Find and remove any stale temp files matching the pattern
    for stale_temp in parent.glob(pattern):
        with suppress(OSError):
            stale_temp.unlink()

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

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Todo storage must be a JSON list")
        return [Todo.from_dict(item) for item in raw]

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses process-unique temp filename and cleans up stale
        temp files to prevent cross-process collisions.
        """
        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

        payload = [todo.to_dict() for todo in todos]
        content = json.dumps(payload, ensure_ascii=False, indent=2)

        # Clean up stale temp files from previous crashed processes
        _cleanup_stale_temp_files(self.path)

        # Create process-unique temp file to avoid cross-process collision
        temp_path = _get_temp_path(self.path)

        try:
            # Write to temp file first
            temp_path.write_text(content, encoding="utf-8")

            # Atomic rename (os.replace is atomic on both Unix and Windows)
            os.replace(temp_path, self.path)
        finally:
            # Clean up temp file if os.replace fails
            temp_path.unlink(missing_ok=True)

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
