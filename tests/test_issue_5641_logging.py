"""Tests for logging support in TodoStorage.

This test suite verifies that TodoStorage logs operations for debugging
and monitoring purposes when FLYWHEEL_DEBUG=1 is set.

Issue: #5641
"""

from __future__ import annotations

import logging
import os
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestLoggingFeature:
    """Test suite for issue #5641: logging support in storage operations."""

    def test_load_logs_debug_when_flywheel_debug_enabled(self, tmp_path, caplog) -> None:
        """When FLYWHEEL_DEBUG=1, load() should log DEBUG level messages."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create some todos to load
        todos = [Todo(id=1, text="test todo"), Todo(id=2, text="another")]
        storage.save(todos)

        # Clear any existing records
        caplog.clear()

        # Enable debug mode and load
        with (
            patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}),
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
        ):
            loaded = storage.load()

        # Verify data loaded correctly
        assert len(loaded) == 2

        # Verify debug log was recorded
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) >= 1, "Expected at least one DEBUG log record"
        # Log should contain file path
        log_messages = [r.message for r in debug_records]
        assert any("load" in msg.lower() for msg in log_messages), f"Expected 'load' in log messages: {log_messages}"

    def test_save_logs_debug_when_flywheel_debug_enabled(self, tmp_path, caplog) -> None:
        """When FLYWHEEL_DEBUG=1, save() should log DEBUG level messages."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]

        # Clear any existing records
        caplog.clear()

        # Enable debug mode and save
        with (
            patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}),
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
        ):
            storage.save(todos)

        # Verify debug log was recorded
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) >= 1, "Expected at least one DEBUG log record"
        log_messages = [r.message for r in debug_records]
        assert any("save" in msg.lower() for msg in log_messages), f"Expected 'save' in log messages: {log_messages}"

    def test_load_logs_error_on_json_decode_error(self, tmp_path, caplog) -> None:
        """When load() encounters JSON decode error, it should log ERROR level."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Write invalid JSON
        db.write_text("{ invalid json", encoding="utf-8")

        # Clear any existing records
        caplog.clear()

        # Enable debug mode and attempt load
        with (
            patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}),
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
            pytest.raises(ValueError, match="Invalid JSON"),
        ):
            storage.load()

        # Verify error log was recorded
        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(error_records) >= 1, "Expected at least one ERROR log record for JSON decode failure"
        log_messages = [r.message for r in error_records]
        assert any("json" in msg.lower() or "error" in msg.lower() for msg in log_messages), \
            f"Expected JSON/error in log messages: {log_messages}"

    def test_save_logs_error_on_permission_denied(self, tmp_path, caplog) -> None:
        """When save() encounters OSError, it should log ERROR level."""
        import tempfile as tempfile_module

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a mock that raises OSError during mkstemp
        def failing_mkstemp(*args, **kwargs):
            raise OSError("Simulated permission denied")

        todos = [Todo(id=1, text="test")]
        caplog.clear()

        with (
            patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}),
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
            patch.object(tempfile_module, "mkstemp", failing_mkstemp),
            pytest.raises(OSError, match="Simulated permission denied"),
        ):
            storage.save(todos)

        # Verify error log was recorded
        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(error_records) >= 1, "Expected at least one ERROR log record for permission error"
        log_messages = [r.message for r in error_records]
        assert any("error" in msg.lower() for msg in log_messages), \
            f"Expected error in log messages: {log_messages}"

    def test_no_logging_when_flywheel_debug_not_set(self, tmp_path, caplog) -> None:
        """When FLYWHEEL_DEBUG is not set, no debug logs should be emitted."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        caplog.clear()

        # Without FLYWHEEL_DEBUG set
        env = os.environ.copy()
        env.pop("FLYWHEEL_DEBUG", None)
        with (
            patch.dict(os.environ, env, clear=True),
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
        ):
            loaded = storage.load()

        # Should have loaded successfully but no debug logs
        assert len(loaded) == 1
        # When FLYWHEEL_DEBUG is not set, debug logs should not be emitted
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        # The logger should not emit debug records when debug mode is off
        assert len(debug_records) == 0, f"Expected no DEBUG logs when FLYWHEEL_DEBUG not set, got: {[r.message for r in debug_records]}"

    def test_log_includes_file_path(self, tmp_path, caplog) -> None:
        """Log messages should include the file path being operated on."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        caplog.clear()

        with (
            patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}),
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
        ):
            storage.load()

        # Log should contain file path
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) >= 1
        all_messages = " ".join(r.message for r in debug_records)
        assert str(db) in all_messages or "todo.json" in all_messages, \
            f"Expected file path in log messages: {all_messages}"

    def test_log_includes_todo_count(self, tmp_path, caplog) -> None:
        """Log messages should include the count of todos loaded/saved."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test1"), Todo(id=2, text="test2"), Todo(id=3, text="test3")]

        caplog.clear()

        with (
            patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}),
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
        ):
            storage.save(todos)

        # Log should mention count
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        all_messages = " ".join(r.message for r in debug_records)
        # Should mention the count (3 todos)
        assert "3" in all_messages, f"Expected todo count in log messages: {all_messages}"
