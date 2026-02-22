"""Tests for storage debug logging feature (issue #5230).

This test suite verifies that TodoStorage provides optional debug logging
for troubleshooting storage operations in production.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _get_logger, _is_debug_enabled
from flywheel.todo import Todo


class TestStorageLogging:
    """Tests for storage debug logging."""

    def test_debug_disabled_by_default(self) -> None:
        """Logging should be disabled by default (no TODO_DEBUG env var)."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove TODO_DEBUG if present
            os.environ.pop("TODO_DEBUG", None)
            assert _is_debug_enabled() is False

    def test_debug_enabled_with_todo_debug_env(self) -> None:
        """Logging should be enabled when TODO_DEBUG=1."""
        with patch.dict(os.environ, {"TODO_DEBUG": "1"}):
            assert _is_debug_enabled() is True

    def test_debug_disabled_with_todo_debug_zero(self) -> None:
        """Logging should be disabled when TODO_DEBUG=0."""
        with patch.dict(os.environ, {"TODO_DEBUG": "0"}):
            assert _is_debug_enabled() is False

    def test_load_emits_debug_log_when_enabled(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """DEBUG log should be emitted for load operations with file path and item count."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        # Clear any existing logs
        caplog.clear()

        with patch.dict(os.environ, {"TODO_DEBUG": "1"}):
            # Re-read the logger to pick up env change
            _get_logger()
            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                loaded = storage.load()

        # Verify load returned correct data
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"

        # Check for DEBUG log with file path
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) >= 1, f"Expected DEBUG log, got: {[r.message for r in caplog.records]}"

        # Log should contain file path
        log_msg = debug_records[0].message.lower()
        assert "load" in log_msg, f"Log should mention 'load': {debug_records[0].message}"
        assert str(db) in debug_records[0].message or "todo.json" in debug_records[0].message.lower()

    def test_save_emits_debug_log_when_enabled(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """DEBUG log should be emitted for save operations with file path and item count."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="save test"), Todo(id=2, text="another todo")]

        with patch.dict(os.environ, {"TODO_DEBUG": "1"}):
            _get_logger()
            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                storage.save(todos)

        # Check for DEBUG log
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) >= 1, f"Expected DEBUG log, got: {[r.message for r in caplog.records]}"

        # Log should contain file path and/or count
        log_msg = debug_records[0].message.lower()
        assert "save" in log_msg, f"Log should mention 'save': {debug_records[0].message}"

    def test_load_error_emits_error_log(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """ERROR log should be emitted when load fails (e.g., malformed JSON)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Write malformed JSON
        db.write_text("{ invalid json", encoding="utf-8")

        with patch.dict(os.environ, {"TODO_DEBUG": "1"}):
            _get_logger()
            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"), pytest.raises(ValueError):
                storage.load()

        # Check for ERROR log
        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(error_records) >= 1, f"Expected ERROR log, got: {[r.message for r in caplog.records]}"

        # Log should mention error and file
        log_msg = error_records[0].message.lower()
        assert "error" in log_msg or "failed" in log_msg or "invalid" in log_msg

    def test_save_error_emits_error_log(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """ERROR log should be emitted when save fails (e.g., permission denied)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create the file first
        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        # Make the file read-only to cause save failure (on the directory)
        # We'll mock the save to fail instead
        with (
            patch.dict(os.environ, {"TODO_DEBUG": "1"}),
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
            patch.object(tempfile, "mkstemp", side_effect=OSError("Permission denied")),
            pytest.raises(OSError),
        ):
            _get_logger()
            storage.save([Todo(id=2, text="new")])

        # Check for ERROR log
        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(error_records) >= 1, f"Expected ERROR log, got: {[r.message for r in caplog.records]}"

    def test_no_logging_when_debug_disabled(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """No logs should be emitted when TODO_DEBUG is not set."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="no debug")]

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TODO_DEBUG", None)
            _get_logger()
            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                storage.save(todos)
                storage.load()

        # Should have no log records (or very few if logging is disabled)
        # The key is that debug operations should not spam logs by default
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG and "flywheel.storage" in (r.name or "")]
        assert len(debug_records) == 0, "No debug logs should be emitted when TODO_DEBUG is not set"

    def test_log_includes_item_count_on_save(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """DEBUG log for save should include the count of items being saved."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=i, text=f"todo {i}") for i in range(1, 6)]  # 5 todos

        with patch.dict(os.environ, {"TODO_DEBUG": "1"}):
            _get_logger()
            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                storage.save(todos)

        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) >= 1

        # Log should mention count (5)
        log_msg = debug_records[0].message
        assert "5" in log_msg, f"Log should mention item count '5': {log_msg}"

    def test_log_includes_item_count_on_load(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """DEBUG log for load should include the count of items loaded."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create 3 todos
        todos = [Todo(id=i, text=f"todo {i}") for i in range(1, 4)]  # 3 todos
        storage.save(todos)

        caplog.clear()

        with patch.dict(os.environ, {"TODO_DEBUG": "1"}):
            _get_logger()
            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                loaded = storage.load()

        assert len(loaded) == 3

        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) >= 1

        # Log should mention count (3)
        log_msg = debug_records[0].message
        assert "3" in log_msg, f"Log should mention item count '3': {log_msg}"

    def test_load_file_not_found_no_error_log(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Loading non-existent file should return empty list, log at DEBUG level."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        with patch.dict(os.environ, {"TODO_DEBUG": "1"}):
            _get_logger()
            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                result = storage.load()

        assert result == []  # Non-existent file returns empty list

        # File not found is normal behavior, should not log as ERROR
        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(error_records) == 0, "File not found should not log as ERROR"
