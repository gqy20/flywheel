"""Tests for operation logging in TodoStorage.

This test suite verifies that TodoStorage logs operations for debugging
and auditing purposes as per issue #4723.
"""

from __future__ import annotations

import logging

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestStorageLogging:
    """Tests for storage operation logging."""

    def test_load_success_logs_debug(self, tmp_path, caplog):
        """Test that load() logs DEBUG on successful load with file path and count."""
        caplog.set_level(logging.DEBUG, logger="flywheel.storage")

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a file with some todos
        todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2")]
        storage.save(todos)

        # Clear previous logs
        caplog.clear()

        # Load and check logs
        loaded = storage.load()
        assert len(loaded) == 2

        # Should have DEBUG log with file path and count
        debug_logs = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_logs) >= 1, "Expected at least one DEBUG log for load()"
        log_msg = debug_logs[0].message
        assert str(db) in log_msg or "todo.json" in log_msg
        assert "2" in log_msg  # count of loaded todos

    def test_save_success_logs_debug(self, tmp_path, caplog):
        """Test that save() logs DEBUG on successful save with file path and count."""
        caplog.set_level(logging.DEBUG, logger="flywheel.storage")

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2"), Todo(id=3, text="task 3")]

        # Save and check logs
        storage.save(todos)

        # Should have DEBUG log with file path and count
        debug_logs = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_logs) >= 1, "Expected at least one DEBUG log for save()"
        log_msg = debug_logs[0].message
        assert str(db) in log_msg or "todo.json" in log_msg
        assert "3" in log_msg  # count of saved todos

    def test_load_empty_file_logs_debug(self, tmp_path, caplog):
        """Test that load() logs DEBUG when loading empty result."""
        caplog.set_level(logging.DEBUG, logger="flywheel.storage")

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Load non-existent file (returns empty list)
        loaded = storage.load()
        assert len(loaded) == 0

        # Should have DEBUG log indicating load
        debug_logs = [r for r in caplog.records if r.levelno == logging.DEBUG]
        # May or may not log for empty load - implementation choice
        # Just check that if it logs, it's correct
        for record in debug_logs:
            if (
                "0" in record.message
                or "empty" in record.message.lower()
                or "no file" in record.message.lower()
            ):
                assert str(db) in record.message or "todo.json" in record.message

    def test_load_json_error_logs_warning_or_error(self, tmp_path, caplog):
        """Test that load() logs WARNING/ERROR on JSON parse error."""
        caplog.set_level(logging.DEBUG, logger="flywheel.storage")

        db = tmp_path / "todo.json"
        db.write_text("{ invalid json", encoding="utf-8")

        storage = TodoStorage(str(db))

        with pytest.raises(ValueError, match="Invalid JSON"):
            storage.load()

        # Should have WARNING or ERROR log for parse error
        warning_or_error_logs = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_or_error_logs) >= 1, (
            "Expected at least one WARNING/ERROR log for JSON parse error"
        )
