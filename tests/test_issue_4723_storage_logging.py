"""Tests for operation logging in TodoStorage.

This test suite verifies that TodoStorage properly logs operations
for debugging and auditing purposes (Issue #4723).

Acceptance criteria:
- load() success: DEBUG log with file path and loaded todo count
- save() success: DEBUG log with file path and saved todo count
- Error conditions: WARNING/ERROR log
"""

from __future__ import annotations

import json
import logging

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class LogCapture(logging.Handler):
    """Custom log handler to capture log records for testing."""

    def __init__(self):
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def get_messages(self, level: int | None = None) -> list[str]:
        """Get all log messages, optionally filtered by level."""
        if level is None:
            return [r.getMessage() for r in self.records]
        return [r.getMessage() for r in self.records if r.levelno == level]


@pytest.fixture
def log_capture():
    """Fixture to capture logs from flywheel.storage module."""
    handler = LogCapture()
    logger = logging.getLogger("flywheel.storage")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)  # Ensure DEBUG logs are captured
    original_level = logger.level

    yield handler

    logger.removeHandler(handler)
    logger.setLevel(original_level)


def test_load_logs_debug_on_success(tmp_path, log_capture) -> None:
    """Test that load() logs DEBUG on successful load with file path and count."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file with 3 todos
    todos_data = [
        {"id": 1, "text": "task 1"},
        {"id": 2, "text": "task 2"},
        {"id": 3, "text": "task 3"},
    ]
    db.write_text(json.dumps(todos_data), encoding="utf-8")

    # Load the todos
    loaded = storage.load()

    # Verify load worked
    assert len(loaded) == 3

    # Check for DEBUG log message
    debug_messages = log_capture.get_messages(logging.DEBUG)
    assert len(debug_messages) >= 1, "Expected at least one DEBUG log message"

    # Log should contain file path and count
    combined_message = " ".join(debug_messages)
    assert str(db) in combined_message or db.name in combined_message, (
        f"Log should contain file path, got: {debug_messages}"
    )
    assert "3" in combined_message, f"Log should contain todo count, got: {debug_messages}"


def test_save_logs_debug_on_success(tmp_path, log_capture) -> None:
    """Test that save() logs DEBUG on successful save with file path and count."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save 2 todos
    todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2")]
    storage.save(todos)

    # Check for DEBUG log message
    debug_messages = log_capture.get_messages(logging.DEBUG)
    assert len(debug_messages) >= 1, "Expected at least one DEBUG log message"

    # Log should contain file path and count
    combined_message = " ".join(debug_messages)
    assert str(db) in combined_message or db.name in combined_message, (
        f"Log should contain file path, got: {debug_messages}"
    )
    assert "2" in combined_message, f"Log should contain todo count, got: {debug_messages}"


def test_load_logs_warning_on_json_error(tmp_path, log_capture) -> None:
    """Test that load() logs WARNING/ERROR when JSON parsing fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create invalid JSON file
    db.write_text("not valid json {{{", encoding="utf-8")

    # Load should raise ValueError
    with pytest.raises(ValueError):
        storage.load()

    # Check for WARNING or ERROR log
    warning_error_messages = log_capture.get_messages(logging.WARNING) + log_capture.get_messages(logging.ERROR)
    assert len(warning_error_messages) >= 1, (
        f"Expected at least one WARNING/ERROR log for JSON error, got: {log_capture.get_messages()}"
    )


def test_load_returns_empty_list_logs_debug(tmp_path, log_capture) -> None:
    """Test that load() logs DEBUG when file doesn't exist (returns empty list)."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Load from non-existent file
    loaded = storage.load()

    assert loaded == []

    # Check for DEBUG log indicating 0 todos loaded
    debug_messages = log_capture.get_messages(logging.DEBUG)
    assert len(debug_messages) >= 1, "Expected at least one DEBUG log message"
    combined_message = " ".join(debug_messages)
    assert "0" in combined_message, f"Log should indicate 0 todos, got: {debug_messages}"
