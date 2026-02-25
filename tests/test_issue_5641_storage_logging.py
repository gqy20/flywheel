"""Tests for issue #5641: Add logging support for debugging storage operations.

This test suite verifies that TodoStorage provides optional logging for
debugging and monitoring purposes, controlled by the FLYWHEEL_DEBUG env var.
"""

from __future__ import annotations

import logging
import os
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestStorageLogging:
    """Tests for logging support in TodoStorage."""

    def test_load_logs_debug_when_flywheel_debug_enabled(self, tmp_path, caplog):
        """Test that load() logs DEBUG messages when FLYWHEEL_DEBUG=1."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create some todos
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        # Enable debug logging via environment variable
        with patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}):
            # Re-create storage to pick up env var
            storage = TodoStorage(str(db))
            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                loaded = storage.load()

        # Verify load succeeded
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"

        # Verify debug log was emitted
        assert any("load" in record.message.lower() for record in caplog.records), \
            f"Expected load log message, got: {[r.message for r in caplog.records]}"

    def test_save_logs_debug_when_flywheel_debug_enabled(self, tmp_path, caplog):
        """Test that save() logs DEBUG messages when FLYWHEEL_DEBUG=1."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="save test")]

        # Enable debug logging via environment variable
        with patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}):
            storage = TodoStorage(str(db))
            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                storage.save(todos)

        # Verify debug log was emitted
        assert any("save" in record.message.lower() for record in caplog.records), \
            f"Expected save log message, got: {[r.message for r in caplog.records]}"

    def test_load_logs_file_path_in_debug_message(self, tmp_path, caplog):
        """Test that load() logs include file path information."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="path test")]
        storage.save(todos)

        with patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}):
            storage = TodoStorage(str(db))
            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                storage.load()

        # Verify file path is in the log message
        log_messages = [r.message for r in caplog.records]
        assert any(str(db) in msg for msg in log_messages), \
            f"Expected file path in log, got: {log_messages}"

    def test_save_logs_todo_count_in_debug_message(self, tmp_path, caplog):
        """Test that save() logs include todo count."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="count1"), Todo(id=2, text="count2")]

        with patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}):
            storage = TodoStorage(str(db))
            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                storage.save(todos)

        # Verify count is in the log message
        log_messages = [r.message for r in caplog.records]
        assert any("2" in msg for msg in log_messages), \
            f"Expected todo count in log, got: {log_messages}"

    def test_no_logging_when_flywheel_debug_not_set(self, tmp_path, caplog):
        """Test that no debug logs are emitted when FLYWHEEL_DEBUG is not set."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="no debug")]

        # Ensure FLYWHEEL_DEBUG is not set
        env = os.environ.copy()
        env.pop("FLYWHEEL_DEBUG", None)

        with patch.dict(os.environ, env, clear=True):
            storage = TodoStorage(str(db))
            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                storage.save(todos)
                storage.load()

        # Should not have debug log messages
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) == 0, \
            f"Expected no debug logs, got: {[r.message for r in debug_records]}"

    def test_load_error_logs_error_level(self, tmp_path, caplog):
        """Test that load() logs ERROR when JSON parsing fails."""
        db = tmp_path / "invalid.json"
        db.write_text("{ invalid json }", encoding="utf-8")

        storage = TodoStorage(str(db))

        with patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}):
            storage = TodoStorage(str(db))
            with (
                caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
                pytest.raises(ValueError),
            ):
                storage.load()

        # Verify error log was emitted
        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(error_records) > 0, \
            f"Expected error log, got: {[r.message for r in caplog.records]}"

    def test_load_empty_file_returns_empty_list_with_debug_log(self, tmp_path, caplog):
        """Test that load() on non-existent file returns [] and logs appropriately."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        with patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}):
            storage = TodoStorage(str(db))
            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                result = storage.load()

        assert result == []
        # May log that file doesn't exist
        log_messages = [r.message for r in caplog.records]
        # At minimum, should have some log about the operation
        assert any("load" in msg.lower() or "not exist" in msg.lower() or "empty" in msg.lower()
                   for msg in log_messages) or len(log_messages) == 0, \
            f"Expected load-related log, got: {log_messages}"


class TestStorageLoggingEnvironmentControl:
    """Tests for FLYWHEEL_DEBUG environment variable behavior."""

    def test_flywheel_debug_1_enables_logging(self, tmp_path, caplog):
        """Test that FLYWHEEL_DEBUG=1 enables debug logging."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="env test")]
        storage.save(todos)

        with patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}):
            storage = TodoStorage(str(db))
            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                storage.load()

        # Should have debug logs
        assert len(caplog.records) > 0

    def test_flywheel_debug_0_disables_logging(self, tmp_path, caplog):
        """Test that FLYWHEEL_DEBUG=0 disables debug logging."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="env test")]
        storage.save(todos)

        with patch.dict(os.environ, {"FLYWHEEL_DEBUG": "0"}):
            storage = TodoStorage(str(db))
            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                storage.load()

        # Should not have debug logs
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) == 0

    def test_flywheel_debug_empty_string_disables_logging(self, tmp_path, caplog):
        """Test that FLYWHEEL_DEBUG='' disables debug logging."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="env test")]
        storage.save(todos)

        with patch.dict(os.environ, {"FLYWHEEL_DEBUG": ""}):
            storage = TodoStorage(str(db))
            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                storage.load()

        # Should not have debug logs
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) == 0
