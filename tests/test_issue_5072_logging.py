"""Tests for operation logging feature (issue #5072).

This test suite verifies that TodoStorage logs operations at DEBUG level
with appropriate context including file paths, operation status, and errors.
"""

from __future__ import annotations

import logging

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class LogCapture(logging.Handler):
    """Custom log handler to capture log records for testing."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def get_messages(self, level: int | None = None) -> list[str]:
        """Get all log messages, optionally filtered by level."""
        if level is None:
            return [r.getMessage() for r in self.records]
        return [r.getMessage() for r in self.records if r.levelno == level]

    def get_debug_messages(self) -> list[str]:
        return self.get_messages(logging.DEBUG)

    def get_error_messages(self) -> list[str]:
        return self.get_messages(logging.ERROR)


@pytest.fixture
def log_capture() -> LogCapture:
    """Fixture to capture logs from flywheel.storage logger."""
    handler = LogCapture()
    logger = logging.getLogger("flywheel.storage")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield handler
    logger.removeHandler(handler)


def test_load_logs_debug_start_and_completion(tmp_path, log_capture) -> None:
    """Test that load() logs DEBUG messages for start and completion."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save some data first
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Clear any existing log records from save
    log_capture.records.clear()

    # Load the data
    loaded = storage.load()

    # Should have loaded successfully
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"

    # Should have logged debug messages
    debug_msgs = log_capture.get_debug_messages()
    assert len(debug_msgs) >= 2, f"Expected at least 2 debug messages, got: {debug_msgs}"

    # Should log the file path in the messages
    all_msgs = " ".join(debug_msgs)
    assert str(db) in all_msgs or "todo.json" in all_msgs, \
        f"Expected file path in log messages, got: {debug_msgs}"


def test_load_empty_file_logs_debug(tmp_path, log_capture) -> None:
    """Test that loading non-existent file logs appropriate debug message."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Clear any existing log records
    log_capture.records.clear()

    # Load from non-existent file (should return empty list)
    loaded = storage.load()

    assert loaded == []

    # Should have logged debug message about non-existent file
    debug_msgs = log_capture.get_debug_messages()
    assert len(debug_msgs) >= 1, f"Expected debug messages, got: {debug_msgs}"
    all_msgs = " ".join(debug_msgs)
    assert "nonexistent" in all_msgs or str(db) in all_msgs, \
        f"Expected file path in log messages, got: {debug_msgs}"


def test_save_logs_debug_start_and_completion(tmp_path, log_capture) -> None:
    """Test that save() logs DEBUG messages for start and completion."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="save test")]

    # Clear any existing log records
    log_capture.records.clear()

    # Save the data
    storage.save(todos)

    # Should have logged debug messages
    debug_msgs = log_capture.get_debug_messages()
    assert len(debug_msgs) >= 1, f"Expected at least 1 debug message, got: {debug_msgs}"

    # Should log the file path in the messages
    all_msgs = " ".join(debug_msgs)
    assert str(db) in all_msgs or "todo.json" in all_msgs, \
        f"Expected file path in log messages, got: {debug_msgs}"


def test_load_json_error_logs_detailed_error(tmp_path, log_capture) -> None:
    """Test that JSON parse errors log detailed error information."""
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    # Write invalid JSON
    db.write_text("{ invalid json }", encoding="utf-8")

    # Clear any existing log records
    log_capture.records.clear()

    # Load should raise ValueError
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()

    # Should have logged error message with details
    error_msgs = log_capture.get_error_messages()
    debug_msgs = log_capture.get_debug_messages()

    # Either error or debug should contain the JSON error details
    all_msgs = " ".join(error_msgs + debug_msgs)
    # The error details should be logged somewhere
    assert "JSON" in all_msgs.upper() or "json" in all_msgs.lower() or "invalid" in all_msgs.lower(), \
        f"Expected JSON error details in log messages, got: {error_msgs + debug_msgs}"


def test_load_logs_item_count(tmp_path, log_capture) -> None:
    """Test that load logs the number of items loaded."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save multiple items
    todos = [Todo(id=i, text=f"todo {i}") for i in range(1, 4)]
    storage.save(todos)

    # Clear logs from save
    log_capture.records.clear()

    # Load the data
    loaded = storage.load()
    assert len(loaded) == 3

    # Should have logged with item count
    debug_msgs = log_capture.get_debug_messages()
    all_msgs = " ".join(debug_msgs)
    # Should mention count or items somewhere
    assert "3" in all_msgs or "item" in all_msgs.lower() or "todo" in all_msgs.lower(), \
        f"Expected item count in log messages, got: {debug_msgs}"


def test_save_logs_item_count(tmp_path, log_capture) -> None:
    """Test that save logs the number of items being saved."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save multiple items
    todos = [Todo(id=i, text=f"todo {i}") for i in range(1, 5)]

    # Clear logs
    log_capture.records.clear()

    storage.save(todos)

    # Should have logged with item count
    debug_msgs = log_capture.get_debug_messages()
    all_msgs = " ".join(debug_msgs)
    # Should mention count or items
    assert "4" in all_msgs or "item" in all_msgs.lower() or "todo" in all_msgs.lower(), \
        f"Expected item count in log messages, got: {debug_msgs}"


def test_load_includes_file_path_context(tmp_path, log_capture) -> None:
    """Test that log messages include file path for context."""
    db = tmp_path / "my_todos.json"
    storage = TodoStorage(str(db))

    # Save and load
    storage.save([Todo(id=1, text="test")])
    log_capture.records.clear()

    storage.load()

    # All debug messages should reference the file path
    debug_msgs = log_capture.get_debug_messages()
    all_msgs = " ".join(debug_msgs)
    assert "my_todos.json" in all_msgs, \
        f"Expected file path 'my_todos.json' in log messages, got: {debug_msgs}"
