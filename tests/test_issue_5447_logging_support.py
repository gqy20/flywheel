"""Tests for logging support in TodoStorage (issue #5447).

This test suite verifies that TodoStorage properly logs key operations
for debugging and production troubleshooting.
"""

from __future__ import annotations

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
        return [r.getMessage() for r in self.records if level is None or r.levelno >= level]

    def get_records_by_level(self, level: int) -> list[logging.LogRecord]:
        """Get log records at a specific level."""
        return [r for r in self.records if r.levelno == level]


@pytest.fixture
def log_capture():
    """Fixture to capture logs from flywheel.storage logger."""
    logger = logging.getLogger("flywheel.storage")
    handler = LogCapture()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    original_level = logger.level
    yield handler
    logger.removeHandler(handler)
    logger.setLevel(original_level)


def test_load_missing_file_logs_debug(tmp_path, log_capture):
    """Test that load() logs DEBUG when file does not exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    result = storage.load()

    assert result == []
    debug_messages = log_capture.get_records_by_level(logging.DEBUG)
    assert len(debug_messages) >= 1
    assert any("not exist" in m.getMessage().lower() for m in debug_messages)


def test_save_success_logs_info(tmp_path, log_capture):
    """Test that save() logs INFO with file path on successful write."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test task")]
    storage.save(todos)

    info_records = log_capture.get_records_by_level(logging.INFO)
    assert len(info_records) >= 1
    # Should log that save was successful with path info
    assert any(str(db) in r.getMessage() or "save" in r.getMessage().lower() for r in info_records)


def test_json_parse_error_logs_error(tmp_path, log_capture):
    """Test that load() logs ERROR when JSON parsing fails."""
    db = tmp_path / "todo.json"
    db.write_text("invalid json {{{", encoding="utf-8")
    storage = TodoStorage(str(db))

    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()

    error_records = log_capture.get_records_by_level(logging.ERROR)
    assert len(error_records) >= 1
    # Should include error details
    assert any(
        "json" in r.getMessage().lower() or "parse" in r.getMessage().lower() for r in error_records
    )


def test_file_too_large_logs_warning_or_error(tmp_path, log_capture):
    """Test that load() logs WARNING or ERROR when file is too large."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file larger than 10MB (11MB of valid JSON)
    # Each element is 23 bytes, need more than 10MB / 23 ≈ 475,000 elements
    large_content = "[" + ",".join(['{"id":1,"text":"test"}'] * 500000) + "]"
    # Ensure we're over the 10MB limit
    assert len(large_content) > 10 * 1024 * 1024
    db.write_text(large_content, encoding="utf-8")

    with pytest.raises(ValueError, match="too large"):
        storage.load()

    # Should log at WARNING or ERROR level
    warning_or_error = [r for r in log_capture.records if r.levelno >= logging.WARNING]
    assert len(warning_or_error) >= 1
    assert any(
        "large" in r.getMessage().lower() or "size" in r.getMessage().lower()
        for r in warning_or_error
    )


def test_load_success_logs_debug(tmp_path, log_capture):
    """Test that load() logs DEBUG on successful load with count."""
    db = tmp_path / "todo.json"
    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}]', encoding="utf-8")
    storage = TodoStorage(str(db))

    result = storage.load()

    assert len(result) == 2
    debug_messages = log_capture.get_records_by_level(logging.DEBUG)
    # Should log successful load
    assert any("load" in m.getMessage().lower() for m in debug_messages)
