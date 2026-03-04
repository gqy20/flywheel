"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import fcntl
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

    def save(self, todos: list[Todo], ensure_unique_ids: bool = True) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.

        Args:
            todos: List of todos to save.
            ensure_unique_ids: If True, reassign IDs to ensure uniqueness
                (prevents ID collision in concurrent environments).
        """
        # Ensure parent directory exists (lazy creation, validated)
        _ensure_parent_directory(self.path)

        # Fix ID collisions for concurrent safety
        if ensure_unique_ids:
            todos = self._ensure_unique_ids(todos)

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

    def atomic_add(self, todo: Todo, max_retries: int = 10) -> Todo:
        """Atomically add a todo with guaranteed unique ID.

        This method is safe for concurrent use across multiple processes.
        It uses file locking (fcntl) to ensure atomicity.

        Args:
            todo: The todo to add (id will be reassigned if necessary).
            max_retries: Maximum number of retry attempts on collision.

        Returns:
            The todo with its final assigned ID.

        Raises:
            RuntimeError: If unable to add after max_retries attempts.
        """
        # Ensure parent directory exists
        _ensure_parent_directory(self.path)

        # Use a separate lock file to avoid issues with the data file
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")

        # Create lock file if it doesn't exist
        lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)

        try:
            # Acquire exclusive lock (blocks until available)
            fcntl.flock(lock_fd, fcntl.LOCK_EX)

            # Load current state
            existing_todos = self.load()

            # Calculate unique ID based on current state
            new_id = self.next_id(existing_todos)

            # Create todo with unique ID
            new_todo = Todo(
                id=new_id,
                text=todo.text,
                done=todo.done,
                created_at=todo.created_at,
                updated_at=todo.updated_at,
            )

            # Prepare new list and save
            new_todos = existing_todos + [new_todo]
            self.save(new_todos, ensure_unique_ids=True)

            return new_todo
        finally:
            # Release lock and close file descriptor
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1

    def _ensure_unique_ids(self, todos: list[Todo]) -> list[Todo]:
        """Ensure all todos have unique IDs, reassigning if necessary.

        This is critical for concurrent safety: when multiple processes
        add todos simultaneously, they may calculate the same next_id.
        This method detects and fixes any ID collisions before saving.

        Returns:
            A new list of todos with guaranteed unique IDs.
        """
        if not todos:
            return todos

        # Check if IDs are already unique
        ids = [todo.id for todo in todos]
        if len(ids) == len(set(ids)):
            return todos

        # Reassign IDs to ensure uniqueness
        # Sort by created_at to maintain relative ordering
        sorted_todos = sorted(todos, key=lambda t: t.created_at or "")
        result = []
        next_id = 1
        seen_ids = set()

        # First pass: keep unique IDs as-is (preserving existing IDs where possible)
        for todo in sorted_todos:
            if todo.id not in seen_ids:
                seen_ids.add(todo.id)
                result.append(todo)
                next_id = max(next_id, todo.id + 1)
            else:
                # ID collision detected, assign a new unique ID
                while next_id in seen_ids:
                    next_id += 1
                seen_ids.add(next_id)
                result.append(Todo(
                    id=next_id,
                    text=todo.text,
                    done=todo.done,
                    created_at=todo.created_at,
                    updated_at=todo.updated_at,
                ))
                next_id += 1

        return result
