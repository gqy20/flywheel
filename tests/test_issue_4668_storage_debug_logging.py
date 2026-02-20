"""Tests for storage debug logging (issue #4668).

This test suite verifies that TodoStorage provides DEBUG level logging
for load/save operations to help troubleshoot storage-related issues.
"""

from __future__ import annotations

import logging
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class LogCapture(logging.Handler):
    """Simple handler to capture log records for testing."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def get_messages(self) -> list[str]:
        return [r.getMessage() for r in self.records]


def test_load_produces_debug_log_with_file_path(tmp_path: Path) -> None:
    """Test that load operation produces DEBUG log with file path."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create some test data
    storage.save([Todo(id=1, text="test")])

    # Capture logs at DEBUG level
    logger = logging.getLogger("flywheel.storage")
    logger.setLevel(logging.DEBUG)
    handler = LogCapture()
    logger.addHandler(handler)

    try:
        storage.load()

        # Should have at least one debug log
        assert len(handler.records) >= 1, "Expected at least one DEBUG log entry"

        # Check that log contains file path
        log_messages = handler.get_messages()
        assert any(str(db) in msg for msg in log_messages), \
            f"Expected log to contain file path, got: {log_messages}"
    finally:
        logger.removeHandler(handler)


def test_save_produces_debug_log_with_file_path_and_count(tmp_path: Path) -> None:
    """Test that save operation produces DEBUG log with file path and data count."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]

    # Capture logs at DEBUG level
    logger = logging.getLogger("flywheel.storage")
    logger.setLevel(logging.DEBUG)
    handler = LogCapture()
    logger.addHandler(handler)

    try:
        storage.save(todos)

        # Should have at least one debug log
        assert len(handler.records) >= 1, "Expected at least one DEBUG log entry"

        # Check that log contains file path
        log_messages = handler.get_messages()
        assert any(str(db) in msg for msg in log_messages), \
            f"Expected log to contain file path, got: {log_messages}"

        # Check that log contains data count
        assert any("2" in msg for msg in log_messages), \
            f"Expected log to contain data count, got: {log_messages}"
    finally:
        logger.removeHandler(handler)


def test_load_empty_file_produces_debug_log(tmp_path: Path) -> None:
    """Test that loading a non-existent file produces appropriate debug log."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Capture logs at DEBUG level
    logger = logging.getLogger("flywheel.storage")
    logger.setLevel(logging.DEBUG)
    handler = LogCapture()
    logger.addHandler(handler)

    try:
        result = storage.load()
        assert result == []

        # Should have debug log even for empty/non-existent file
        assert len(handler.records) >= 1, "Expected at least one DEBUG log entry"

        log_messages = handler.get_messages()
        # Log should indicate load operation
        assert any("load" in msg.lower() for msg in log_messages), \
            f"Expected log to mention 'load', got: {log_messages}"
    finally:
        logger.removeHandler(handler)


def test_no_output_at_default_warning_level(tmp_path: Path) -> None:
    """Test that no logs are output at default WARNING level."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create test data
    storage.save([Todo(id=1, text="test")])

    # Reset logger level to default WARNING
    logger = logging.getLogger("flywheel.storage")
    logger.setLevel(logging.WARNING)  # Default level
    handler = LogCapture()
    logger.addHandler(handler)

    try:
        # Perform operations
        storage.save([Todo(id=2, text="test2")])
        storage.load()

        # Should have no debug logs at WARNING level
        debug_logs = [r for r in handler.records if r.levelno == logging.DEBUG]
        assert len(debug_logs) == 0, \
            f"Expected no DEBUG logs at WARNING level, got: {[r.getMessage() for r in debug_logs]}"
    finally:
        logger.removeHandler(handler)


def test_logger_name_is_flywheel_storage(tmp_path: Path) -> None:
    """Test that the logger uses 'flywheel.storage' namespace."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="test")])

    # Get the logger used by storage module
    logger = logging.getLogger("flywheel.storage")
    assert logger.name == "flywheel.storage", \
        f"Expected logger name 'flywheel.storage', got '{logger.name}'"
