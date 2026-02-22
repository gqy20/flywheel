"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import csv
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

    def export_to(self, path: Path | str, format: str = "json") -> None:
        """Export todos to an external file in the specified format.

        Args:
            path: Destination file path for the export.
            format: Export format - 'json' (default) or 'csv'.

        Raises:
            ValueError: If format is not supported.
        """
        path = Path(path)
        todos = self.load()

        if format == "json":
            payload = [todo.to_dict() for todo in todos]
            content = json.dumps(payload, ensure_ascii=False, indent=2)
            path.write_text(content, encoding="utf-8")
        elif format == "csv":
            _ensure_parent_directory(path)
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "text", "done", "created_at", "updated_at"])
                for todo in todos:
                    writer.writerow([
                        todo.id,
                        todo.text,
                        todo.done,
                        todo.created_at,
                        todo.updated_at,
                    ])
        else:
            raise ValueError(
                f"Unsupported export format: '{format}'. "
                f"Supported formats: json, csv"
            )

    def import_from(
        self, path: Path | str, format: str = "json", *, merge: bool = True
    ) -> list[Todo]:
        """Import todos from an external file and merge or replace existing data.

        Args:
            path: Source file path to import from.
            format: Import format - 'json' (default) or 'csv'.
            merge: If True, merge imported todos with existing. If False, replace all.

        Returns:
            List of imported Todo objects.

        Raises:
            ValueError: If format is not supported or file contains invalid data.
        """
        path = Path(path)

        if format == "json":
            imported_todos = self._import_json(path)
        elif format == "csv":
            imported_todos = self._import_csv(path)
        else:
            raise ValueError(
                f"Unsupported import format: '{format}'. "
                f"Supported formats: json, csv"
            )

        if merge:
            existing = self.load()
            existing_ids = {todo.id for todo in existing}
            max_id = max((todo.id for todo in existing), default=0)

            # Add imported todos, assigning new IDs for conflicts
            for todo in imported_todos:
                if todo.id in existing_ids:
                    max_id += 1
                    todo.id = max_id
                existing.append(todo)

            self.save(existing)
            return existing
        else:
            self.save(imported_todos)
            return imported_todos

    def _import_json(self, path: Path) -> list[Todo]:
        """Import todos from a JSON file."""
        try:
            content = path.read_text(encoding="utf-8")
            raw = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in '{path}': {e.msg}. "
                f"Check line {e.lineno}, column {e.colno}."
            ) from e

        if not isinstance(raw, list):
            raise ValueError(f"Import file must contain a JSON list, got {type(raw).__name__}")

        return [Todo.from_dict(item) for item in raw]

    def _import_csv(self, path: Path) -> list[Todo]:
        """Import todos from a CSV file."""
        todos = []

        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                # Validate required columns exist
                if reader.fieldnames is None:
                    raise ValueError(
                        f"CSV file '{path}' is empty or has no headers"
                    )

                required = {"id", "text"}
                missing = required - set(reader.fieldnames)
                if missing:
                    raise ValueError(
                        f"CSV file '{path}' missing required columns: {', '.join(sorted(missing))}"
                    )

                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Parse done field - accept various boolean representations
                        done_str = row.get("done", "False").strip().lower()
                        done = done_str in ("true", "1", "yes")

                        todo = Todo(
                            id=int(row["id"]),
                            text=row["text"],
                            done=done,
                            created_at=row.get("created_at", ""),
                            updated_at=row.get("updated_at", ""),
                        )
                        todos.append(todo)
                    except (ValueError, KeyError) as e:
                        raise ValueError(
                            f"Invalid data in CSV file '{path}' at row {row_num}: {e}"
                        ) from e
        except FileNotFoundError:
            raise ValueError(f"Import file not found: '{path}'") from None

        return todos
