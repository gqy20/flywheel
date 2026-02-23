"""Tests for issue #5447: Add logging support to storage.py.

This test suite verifies that TodoStorage logs key operations for debugging
and production issue tracking.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

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

    def get_messages_by_level_name(self, level_name: str) -> list[str]:
        """Get all log messages at a specific level name (DEBUG, INFO, etc.)."""
        return [r.getMessage() for r in self.records if r.levelname == level_name]


@pytest.fixture
def log_capture():
    """Fixture to capture logs from flywheel.storage logger."""
    logger = logging.getLogger("flywheel.storage")
    handler = LogCapture()
    handler.setLevel(logging.DEBUG)  # Capture all levels
    original_level = logger.level
    original_handlers = logger.handlers[:]

    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    yield handler

    logger.removeHandler(handler)
    logger.setLevel(original_level)
    logger.handlers = original_handlers


class TestLoadLogging:
    """Test logging in the load() method."""

    def test_load_missing_file_logs_debug(self, tmp_path, log_capture):
        """Test that load() logs DEBUG when file doesn't exist."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        result = storage.load()

        assert result == []
        debug_messages = log_capture.get_messages_by_level_name("DEBUG")
        # Should log that file doesn't exist
        assert any(
            "not exist" in msg.lower() or "no file" in msg.lower() for msg in debug_messages
        ), f"Expected DEBUG log about missing file, got: {debug_messages}"

    def test_load_success_logs_debug(self, tmp_path, log_capture):
        """Test that load() logs DEBUG on successful load."""
        db = tmp_path / "todo.json"
        db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")
        storage = TodoStorage(str(db))

        result = storage.load()

        assert len(result) == 1
        debug_messages = log_capture.get_messages_by_level_name("DEBUG")
        # Should log successful load
        assert any("load" in msg.lower() for msg in debug_messages), (
            f"Expected DEBUG log about load, got: {debug_messages}"
        )

    def test_load_json_parse_error_logs_error(self, tmp_path, log_capture):
        """Test that load() logs ERROR when JSON parsing fails."""
        db = tmp_path / "invalid.json"
        db.write_text('{"invalid": json}', encoding="utf-8")
        storage = TodoStorage(str(db))

        with pytest.raises(ValueError, match="Invalid JSON"):
            storage.load()

        error_messages = log_capture.get_messages_by_level_name("ERROR")
        # Should log JSON parse error
        assert any("json" in msg.lower() or "parse" in msg.lower() for msg in error_messages), (
            f"Expected ERROR log about JSON, got: {error_messages}"
        )

    def test_load_file_too_large_logs_warning(self, tmp_path, log_capture):
        """Test that load() logs WARNING when file is too large."""
        db = tmp_path / "large.json"
        # Create a file larger than 10MB
        large_content = "[" + ", ".join(['{"id": 1, "text": "test"}'] * 500000) + "]"
        db.write_text(large_content, encoding="utf-8")
        storage = TodoStorage(str(db))

        with pytest.raises(ValueError, match="too large"):
            storage.load()

        # Should log warning about file size
        warning_or_error = log_capture.get_messages_by_level_name("WARNING")
        assert any("large" in msg.lower() or "size" in msg.lower() for msg in warning_or_error), (
            f"Expected WARNING log about size, got: {warning_or_error}"
        )


class TestSaveLogging:
    """Test logging in the save() method."""

    def test_save_success_logs_info(self, tmp_path, log_capture):
        """Test that save() logs INFO on successful save with file path."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))
        todos = [Todo(id=1, text="test task")]

        storage.save(todos)

        info_messages = log_capture.get_messages_by_level_name("INFO")
        # Should log successful save with file path
        assert any("save" in msg.lower() for msg in info_messages), (
            f"Expected INFO log about save, got: {info_messages}"
        )

    def test_save_logs_debug_for_temp_file_creation(self, tmp_path, log_capture):
        """Test that save() logs DEBUG when creating temp file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))
        todos = [Todo(id=1, text="test")]

        storage.save(todos)

        debug_messages = log_capture.get_messages_by_level_name("DEBUG")
        # Should log about temp file creation
        assert any("temp" in msg.lower() for msg in debug_messages), (
            f"Expected DEBUG log about temp file, got: {debug_messages}"
        )

    def test_save_logs_error_on_write_failure(self, tmp_path, log_capture):
        """Test that save() logs ERROR when write fails during temp file operations."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First, create a file to test error during rename
        storage.save([Todo(id=1, text="initial")])

        # Simulate failure during rename (inside try block) using mock os.replace
        def failing_replace(*args, **kwargs):
            raise OSError("Simulated rename failure")

        import os

        with (
            patch.object(os, "replace", failing_replace),
            pytest.raises(OSError, match="Simulated rename failure"),
        ):
            storage.save([Todo(id=2, text="test")])

        error_messages = log_capture.get_messages_by_level_name("ERROR")
        # Should log write failure
        assert any("save" in msg.lower() or "failed" in msg.lower() for msg in error_messages), (
            f"Expected ERROR log about save failure, got: {error_messages}"
        )
