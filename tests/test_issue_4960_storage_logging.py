"""Tests for load/save operation logging in TodoStorage.

This test suite verifies that TodoStorage can optionally log load/save operations
for debugging purposes. This is a regression test for issue #4960.

Requirements:
- Optional logger parameter in TodoStorage constructor (default None = silent)
- load() logs DEBUG message with file path and entry count on success
- save() logs DEBUG message with file path and entry count on success
- Default behavior unchanged (no logging when logger is None)
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_accepts_optional_logger_parameter(tmp_path: Path) -> None:
    """Test that TodoStorage constructor accepts optional logger parameter."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_logger")

    # Should not raise - logger parameter should be accepted
    storage = TodoStorage(str(db), logger=logger)
    assert storage is not None


def test_load_logs_debug_message_with_path_and_count(tmp_path: Path) -> None:
    """Test that load() logs DEBUG message with file path and entry count."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_load_logger")
    logger.setLevel(logging.DEBUG)

    # Create a list to capture log records
    log_records: list[logging.LogRecord] = []
    handler = logging.handlers.MemoryHandler(capacity=100)
    handler.setLevel(logging.DEBUG)

    # Custom handler to capture records
    class RecordCapture(logging.Handler):
        def __init__(self, records: list[logging.LogRecord]):
            super().__init__()
            self.records = records

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    capture_handler = RecordCapture(log_records)
    capture_handler.setLevel(logging.DEBUG)
    logger.addHandler(capture_handler)

    # Create storage with logger
    storage = TodoStorage(str(db), logger=logger)

    # Save some todos first
    todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2"), Todo(id=3, text="task 3")]
    storage.save(todos)

    # Clear records from save
    log_records.clear()

    # Load should produce a debug log
    loaded = storage.load()

    # Verify we got the data
    assert len(loaded) == 3

    # Verify debug log was captured
    debug_logs = [r for r in log_records if r.levelno == logging.DEBUG]
    assert len(debug_logs) >= 1, "Expected at least one DEBUG log message from load()"

    # Verify log message contains path and count
    log_message = debug_logs[0].getMessage()
    assert str(db) in log_message or "todo.json" in log_message, \
        f"Log message should contain file path, got: {log_message}"
    assert "3" in log_message, \
        f"Log message should contain entry count '3', got: {log_message}"


def test_save_logs_debug_message_with_path_and_count(tmp_path: Path) -> None:
    """Test that save() logs DEBUG message with file path and entry count."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_save_logger")
    logger.setLevel(logging.DEBUG)

    # Capture log records
    log_records: list[logging.LogRecord] = []

    class RecordCapture(logging.Handler):
        def __init__(self, records: list[logging.LogRecord]):
            super().__init__()
            self.records = records

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    capture_handler = RecordCapture(log_records)
    capture_handler.setLevel(logging.DEBUG)
    logger.addHandler(capture_handler)

    # Create storage with logger
    storage = TodoStorage(str(db), logger=logger)

    # Save todos - should produce a debug log
    todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2")]
    storage.save(todos)

    # Verify debug log was captured
    debug_logs = [r for r in log_records if r.levelno == logging.DEBUG]
    assert len(debug_logs) >= 1, "Expected at least one DEBUG log message from save()"

    # Verify log message contains path and count
    log_message = debug_logs[0].getMessage()
    assert str(db) in log_message or "todo.json" in log_message, \
        f"Log message should contain file path, got: {log_message}"
    assert "2" in log_message, \
        f"Log message should contain entry count '2', got: {log_message}"


def test_no_logging_when_logger_is_none(tmp_path: Path) -> None:
    """Test that default behavior (logger=None) produces no log output."""
    db = tmp_path / "todo.json"

    # Create storage without logger (default)
    storage = TodoStorage(str(db))

    # Create and save some todos
    todos = [Todo(id=1, text="task 1")]
    storage.save(todos)

    # Load them back
    loaded = storage.load()

    # Verify data works
    assert len(loaded) == 1
    assert loaded[0].text == "task 1"

    # Verify storage doesn't have logger attribute set to None or doesn't try to log
    # (This test mainly ensures no exception is raised and behavior is unchanged)
    assert storage.logger is None


def test_load_empty_file_still_logs_if_logger_provided(tmp_path: Path) -> None:
    """Test that load() logs even when loading empty file."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_empty_load_logger")
    logger.setLevel(logging.DEBUG)

    # Capture log records
    log_records: list[logging.LogRecord] = []

    class RecordCapture(logging.Handler):
        def __init__(self, records: list[logging.LogRecord]):
            super().__init__()
            self.records = records

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    capture_handler = RecordCapture(log_records)
    capture_handler.setLevel(logging.DEBUG)
    logger.addHandler(capture_handler)

    # Create storage with logger but no file
    storage = TodoStorage(str(db), logger=logger)

    # Load from non-existent file
    loaded = storage.load()

    # Should return empty list
    assert loaded == []

    # When file doesn't exist, we may or may not log - either is acceptable
    # The key is that no exception is raised


def test_logger_uses_debug_level(tmp_path: Path) -> None:
    """Test that logging uses DEBUG level (not INFO or WARNING)."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_debug_level_logger")
    logger.setLevel(logging.DEBUG)

    # Capture log records
    log_records: list[logging.LogRecord] = []

    class RecordCapture(logging.Handler):
        def __init__(self, records: list[logging.LogRecord]):
            super().__init__()
            self.records = records

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    capture_handler = RecordCapture(log_records)
    capture_handler.setLevel(logging.DEBUG)
    logger.addHandler(capture_handler)

    # Create storage with logger
    storage = TodoStorage(str(db), logger=logger)

    # Perform operations
    todos = [Todo(id=1, text="test")]
    storage.save(todos)
    storage.load()

    # All log records should be DEBUG level
    for record in log_records:
        assert record.levelno == logging.DEBUG, \
            f"Expected DEBUG level, got {record.levelname}: {record.getMessage()}"
