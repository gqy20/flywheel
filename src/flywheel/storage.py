"""JSON-backed todo storage."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import stat
import tempfile
import time
from pathlib import Path

from .todo import Todo

# Configure logger for storage operations
_logger = logging.getLogger(__name__)


def _ensure_logging_configured() -> None:
    """Configure logging level based on FW_LOG_LEVEL environment variable.

    If FW_LOG_LEVEL is not set, logging remains disabled (default behavior).
    This ensures backward compatibility - no logs by default.

    This function is called on each storage operation to check the current
    environment variable state, allowing runtime configuration changes.
    """
    log_level_str = os.environ.get("FW_LOG_LEVEL", "").upper()

    # Check if we need to (re)configure
    has_handler = bool(_logger.handlers)

    if log_level_str:
        level = getattr(logging, log_level_str, logging.DEBUG)
        _logger.setLevel(level)

        # Only add handler if not already configured
        if not has_handler:
            handler = logging.StreamHandler()
            handler.setLevel(level)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            _logger.addHandler(handler)
    else:
        # Explicitly disable logging by default for backward compatibility
        _logger.setLevel(logging.CRITICAL + 1)  # Disable all logging

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
        _ensure_logging_configured()
        start_time = time.perf_counter()
        if not self.path.exists():
            _logger.info(f"File not found: {self.path}, returning empty list")
            return []

        # Security: Check file size before loading to prevent DoS
        file_size = self.path.stat().st_size
        if file_size > _MAX_JSON_SIZE_BYTES:
            size_mb = file_size / (1024 * 1024)
            limit_mb = _MAX_JSON_SIZE_BYTES / (1024 * 1024)
            _logger.error(f"JSON file too large: {self.path} ({size_mb:.1f}MB > {limit_mb:.0f}MB limit)")
            raise ValueError(
                f"JSON file too large ({size_mb:.1f}MB > {limit_mb:.0f}MB limit). "
                f"This protects against denial-of-service attacks."
            )

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            _logger.error(f"Invalid JSON in '{self.path}': {e.msg} at line {e.lineno}, column {e.colno}")
            raise ValueError(
                f"Invalid JSON in '{self.path}': {e.msg}. "
                f"Check line {e.lineno}, column {e.colno}."
            ) from e

        if not isinstance(raw, list):
            _logger.error(f"Invalid format in '{self.path}': expected JSON list")
            raise ValueError("Todo storage must be a JSON list")

        todos = [Todo.from_dict(item) for item in raw]
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        _logger.info(f"Loaded {len(todos)} todo(s) from {self.path} in {elapsed_ms:.2f}ms")
        return todos

    def save(self, todos: list[Todo]) -> None:
        """Save todos to file atomically.

        Uses write-to-temp-file + atomic rename pattern to prevent data loss
        if the process crashes during write.

        Security: Uses tempfile.mkstemp to create unpredictable temp file names
        and sets restrictive permissions (0o600) to protect against symlink attacks.
        """
        _ensure_logging_configured()
        start_time = time.perf_counter()
        # Ensure parent directory exists (lazy creation, validated)
        try:
            _ensure_parent_directory(self.path)
        except (ValueError, OSError) as e:
            _logger.error(f"Failed to create parent directory for {self.path}: {e}")
            raise

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

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            _logger.info(f"Saved {len(todos)} todo(s) to {self.path} in {elapsed_ms:.2f}ms")
        except OSError:
            # Clean up temp file on error
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            _logger.error(f"Failed to save {len(todos)} todo(s) to {self.path} after {elapsed_ms:.2f}ms")
            raise

    def next_id(self, todos: list[Todo]) -> int:
        return (max((todo.id for todo in todos), default=0) + 1) if todos else 1
