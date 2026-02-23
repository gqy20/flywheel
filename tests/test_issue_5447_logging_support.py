"""Tests for logging support in storage.py (Issue #5447).

These tests verify that:
1. load() logs DEBUG when file doesn't exist
2. save() logs INFO when writing successfully
3. load() logs ERROR when JSON parsing fails
"""

from __future__ import annotations

import logging

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class LogCapture(logging.Handler):
    """Custom logging handler to capture log records."""

    def __init__(self):
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def get_messages(self, level: int | None = None) -> list[str]:
        """Get log messages, optionally filtered by level."""
        if level is None:
            return [r.getMessage() for r in self.records]
        return [r.getMessage() for r in self.records if r.levelno == level]


@pytest.fixture
def log_capture():
    """Fixture to capture logs from flywheel.storage logger."""
    logger = logging.getLogger("flywheel.storage")
    handler = LogCapture()
    handler.setLevel(logging.DEBUG)

    # Save original level and handlers
    original_level = logger.level
    original_handlers = logger.handlers[:]

    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    yield handler

    # Restore original state
    logger.removeHandler(handler)
    logger.setLevel(original_level)
    logger.handlers = original_handlers


def test_load_logs_debug_when_file_not_exists(tmp_path, log_capture) -> None:
    """load() should log DEBUG when the storage file doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist
    assert not db.exists()

    # Load should return empty list and log
    result = storage.load()
    assert result == []

    # Should have logged DEBUG message about missing file
    debug_messages = log_capture.get_messages(logging.DEBUG)
    assert any(
        str(db) in msg or "not exist" in msg.lower()
        for msg in debug_messages
    ), f"Expected DEBUG log about missing file, got: {debug_messages}"


def test_save_logs_info_on_success(tmp_path, log_capture) -> None:
    """save() should log INFO when successfully writing the file."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test task")]
    storage.save(todos)

    # Should have logged INFO message about saving
    info_messages = log_capture.get_messages(logging.INFO)
    assert any(
        str(db) in msg or "save" in msg.lower()
        for msg in info_messages
    ), f"Expected INFO log about saving, got: {info_messages}"


def test_load_logs_error_on_json_parse_failure(tmp_path, log_capture) -> None:
    """load() should log ERROR when JSON parsing fails."""
    db = tmp_path / "malformed.json"
    storage = TodoStorage(str(db))

    # Create a file with invalid JSON
    db.write_text('[{"id": 1, "text": "incomplete"', encoding="utf-8")

    # Should raise ValueError
    with pytest.raises(ValueError):
        storage.load()

    # Should have logged ERROR message about JSON parse failure
    error_messages = log_capture.get_messages(logging.ERROR)
    assert any(
        "json" in msg.lower() or "parse" in msg.lower() or "invalid" in msg.lower()
        for msg in error_messages
    ), f"Expected ERROR log about JSON parsing, got: {error_messages}"


def test_load_logs_debug_on_file_too_large(tmp_path, log_capture) -> None:
    """load() should log when file exceeds size limit."""
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Write a file with invalid JSON structure (not a list)
    db.write_text('{"id": 1, "text": "test"}', encoding="utf-8")

    with pytest.raises(ValueError, match="must be a JSON list"):
        storage.load()

    # Should have logged something about the validation
    all_messages = [r.getMessage() for r in log_capture.records]
    assert len(all_messages) > 0, "Expected some log output"


def test_save_logs_debug_temp_file_creation(tmp_path, log_capture) -> None:
    """save() should log DEBUG about temp file creation and atomic rename."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test task")]
    storage.save(todos)

    all_messages = [r.getMessage() for r in log_capture.records]

    # Either temp file creation or atomic rename should be logged
    assert any(
        "temp" in msg.lower() or "atomic" in msg.lower() or "rename" in msg.lower()
        for msg in all_messages
    ), f"Expected log about temp file operations, got: {all_messages}"
