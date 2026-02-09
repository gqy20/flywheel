"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import stat
import tempfile
from pathlib import Path

from .todo import Todo

# Module-level logger with NullHandler (no output by default)
_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())
_logger.setLevel(logging.DEBUG)  # Capture all levels, handler filters output


def _configure_debug_logging() -> None:
    """Configure debug logging output if FLYWHEEL_DEBUG is enabled.

    This function is safe to call multiple times - it will only add
    the debug handler once. Call this after importing the module
    to enable debug output via FLYWHEEL_DEBUG environment variable.

    The debug handler uses stderr to avoid polluting stdout.
    """
    if os.environ.get("FLYWHEEL_DEBUG", "").lower() not in ("1", "true", "yes"):
        return

    # Only add handler if not already present
    for handler in _logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.NullHandler
        ):
            return  # Already configured

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(name)s - %(levelname)s - %(message)s"))
    _logger.addHandler(handler)


# Auto-configure debug logging on module import
_configure_debug_logging()

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
            _logger.debug("Storage file '%s' does not exist, returning empty list", self.path)
            return []

        # Security: Check file size before loading to prevent DoS
        file_size = self.path.stat().st_size
        if file_size > _MAX_JSON_SIZE_BYTES:
            size_mb = file_size / (1024 * 1024)
            limit_mb = _MAX_JSON_SIZE_BYTES / (1024 * 1024)
            _logger.warning(
                "File '%s' too large: %.1fMB > %.0fMB limit",
                self.path,
                size_mb,
                limit_mb,
            )
            raise ValueError(
                f"JSON file too large ({size_mb:.1f}MB > {limit_mb:.0f}MB limit). "
                f"This protects against denial-of-service attacks."
            )

        _logger.debug("Loading from '%s' (%d bytes)", self.path, file_size)

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            _logger.warning(
                "Failed to parse JSON in '%s': %s at line %s, column %s",
                self.path,
                e.msg,
                e.lineno,
                e.colno,
            )
            raise ValueError(
                f"Invalid JSON in '{self.path}': {e.msg}. "
                f"Check line {e.lineno}, column {e.colno}."
            ) from e

        if not isinstance(raw, list):
            raise ValueError("Todo storage must be a JSON list")

        result = [Todo.from_dict(item) for item in raw]
        _logger.debug("Loaded %d todos from '%s'", len(result), self.path)
        return result

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        _logger.debug("Saving %d todos to '%s'", len(todos), self.path)

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
            _logger.debug("Atomic rename: '%s' -> '%s'", temp_path, self.path)
            os.replace(temp_path, self.path)
        except OSError:
            # Clean up temp file on error
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
            raise

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
