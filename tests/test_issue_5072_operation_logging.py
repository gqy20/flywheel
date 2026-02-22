"""Tests for operation logging in TodoStorage.

This test suite verifies that TodoStorage operations (load/save) log
appropriate debug information to help diagnose issues.

Issue: #5072 - Add operation logging functionality
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class LogCapture(logging.Handler):
    """Custom logging handler to capture log records for testing."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def get_messages(self, level: int | None = None) -> list[str]:
        """Get all log messages, optionally filtered by level."""
        if level is None:
            return [r.getMessage() for r in self.records]
        return [r.getMessage() for r in self.records if r.levelno >= level]

    def get_debug_messages(self) -> list[str]:
        """Get all DEBUG level messages."""
        return self.get_messages(logging.DEBUG)


@pytest.fixture
def log_capture() -> LogCapture:
    """Fixture to capture log records from flywheel.storage logger."""
    handler = LogCapture()
    logger = logging.getLogger("flywheel.storage")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield handler
    logger.removeHandler(handler)


def test_load_logs_debug_on_start_and_completion(
    tmp_path: Path, log_capture: LogCapture
) -> None:
    """Test that load() logs DEBUG messages for start and completion."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Clear any logs from save
    log_capture.records.clear()

    # Load the todos
    loaded = storage.load()

    # Verify load was successful
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"

    # Verify DEBUG logs were generated
    debug_messages = log_capture.get_debug_messages()

    # Should have at least start and completion logs
    assert len(debug_messages) >= 2, f"Expected at least 2 debug logs, got {debug_messages}"

    # Check that logs contain relevant information
    all_logs = " ".join(debug_messages).lower()
    assert "load" in all_logs, f"Expected 'load' in logs: {debug_messages}"
    assert str(db) in " ".join(debug_messages), f"Expected path '{db}' in logs: {debug_messages}"


def test_save_logs_debug_on_start_and_completion(
    tmp_path: Path, log_capture: LogCapture
) -> None:
    """Test that save() logs DEBUG messages for start and completion."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="save test")]
    storage.save(todos)

    # Verify DEBUG logs were generated
    debug_messages = log_capture.get_debug_messages()

    # Should have at least start and completion logs
    assert len(debug_messages) >= 2, f"Expected at least 2 debug logs, got {debug_messages}"

    # Check that logs contain relevant information
    all_logs = " ".join(debug_messages).lower()
    assert "save" in all_logs, f"Expected 'save' in logs: {debug_messages}"
    assert str(db) in " ".join(debug_messages), f"Expected path '{db}' in logs: {debug_messages}"


def test_load_logs_error_on_invalid_json(
    tmp_path: Path, log_capture: LogCapture
) -> None:
    """Test that load() logs ERROR with details when JSON parsing fails."""
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    # Create an invalid JSON file
    db.write_text("{ invalid json }", encoding="utf-8")

    # Attempt to load - should raise ValueError
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()

    # Verify error was logged
    error_messages = [
        r.getMessage()
        for r in log_capture.records
        if r.levelno >= logging.ERROR
    ]

    assert len(error_messages) >= 1, f"Expected error logs, got: {log_capture.get_messages()}"

    # Error message should contain useful diagnostic info
    error_text = " ".join(error_messages).lower()
    assert "json" in error_text or "parse" in error_text or "error" in error_text, \
        f"Expected JSON error context in logs: {error_messages}"


def test_load_logs_debug_when_file_not_exists(
    tmp_path: Path, log_capture: LogCapture
) -> None:
    """Test that load() logs DEBUG when file doesn't exist (returns empty list)."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Load from non-existent file
    loaded = storage.load()

    # Should return empty list
    assert loaded == []

    # Verify DEBUG logs were generated
    debug_messages = log_capture.get_debug_messages()

    # Should have log indicating file not found or no load needed
    all_logs = " ".join(debug_messages).lower()
    assert "load" in all_logs or "not found" in all_logs or "empty" in all_logs, \
        f"Expected load/no-file context in logs: {debug_messages}"


def test_save_logs_item_count(
    tmp_path: Path, log_capture: LogCapture
) -> None:
    """Test that save() logs include the count of items being saved."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save multiple items
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]
    storage.save(todos)

    # Check logs for count information
    debug_messages = log_capture.get_debug_messages()
    all_logs = " ".join(debug_messages)

    # Should include the count (3)
    assert "3" in all_logs, f"Expected item count '3' in logs: {debug_messages}"
