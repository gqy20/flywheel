"""Tests for logging support in TodoStorage.

This test suite verifies that TodoStorage emits appropriate log messages
for debugging file operations, as requested in issue #2925.
"""

from __future__ import annotations

import logging

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestLoggingSupport:
    """Tests for logging support in TodoStorage operations."""

    def test_load_logs_debug_message_with_path_and_count(self, tmp_path, caplog):
        """TodoStorage.load() should log DEBUG message with file path and entry count."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a file with some todos
        todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]
        storage.save(todos)

        # Load with DEBUG level logging
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        # Verify load succeeded
        assert len(loaded) == 2

        # Verify DEBUG log was emitted
        debug_logs = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_logs) >= 1, "Expected at least one DEBUG log message"

        # Verify log contains relevant information
        log_messages = [r.message for r in debug_logs]
        log_text = " ".join(log_messages).lower()

        # Should mention loading/loading action
        assert "load" in log_text, f"Log should mention 'load': {log_messages}"

        # Should mention the count
        assert "2" in log_text or "two" in log_text, (
            f"Log should mention entry count: {log_messages}"
        )

    def test_load_logs_file_path(self, tmp_path, caplog):
        """TodoStorage.load() should log the file path being loaded."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a file with a todo
        storage.save([Todo(id=1, text="test")])

        # Load with DEBUG level logging
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.load()

        # Verify log contains the file path
        debug_logs = [r for r in caplog.records if r.levelno == logging.DEBUG]
        log_messages = [r.message for r in debug_logs]
        log_text = " ".join(log_messages)

        # Should mention the filename
        assert "todo.json" in log_text or str(db) in log_text, (
            f"Log should mention file path: {log_messages}"
        )

    def test_save_logs_debug_message_with_count(self, tmp_path, caplog):
        """TodoStorage.save() should log DEBUG message with entry count."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="first"), Todo(id=2, text="second"), Todo(id=3, text="third")]

        # Save with DEBUG level logging
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # Verify DEBUG log was emitted
        debug_logs = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_logs) >= 1, "Expected at least one DEBUG log message"

        # Verify log contains count information
        log_messages = [r.message for r in debug_logs]
        log_text = " ".join(log_messages).lower()

        # Should mention saving action
        assert "save" in log_text, f"Log should mention 'save': {log_messages}"

        # Should mention the count
        assert "3" in log_text or "three" in log_text, (
            f"Log should mention entry count: {log_messages}"
        )

    def test_save_logs_file_path(self, tmp_path, caplog):
        """TodoStorage.save() should log the file path being saved to."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save with DEBUG level logging
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save([Todo(id=1, text="test")])

        # Verify log contains the file path
        debug_logs = [r for r in caplog.records if r.levelno == logging.DEBUG]
        log_messages = [r.message for r in debug_logs]
        log_text = " ".join(log_messages)

        # Should mention the filename
        assert "todo.json" in log_text or str(db) in log_text, (
            f"Log should mention file path: {log_messages}"
        )

    def test_load_returns_empty_list_when_file_does_not_exist(self, tmp_path, caplog):
        """TodoStorage.load() should return empty list for non-existent file."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        # Load with DEBUG level logging
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            result = storage.load()

        # Should return empty list
        assert result == []

    def test_invalid_json_logs_warning(self, tmp_path, caplog):
        """TodoStorage.load() should log WARNING for invalid JSON."""
        db = tmp_path / "invalid.json"
        storage = TodoStorage(str(db))

        # Create file with invalid JSON
        db.write_text("not valid json {", encoding="utf-8")

        # Load with WARNING level logging
        with (
            caplog.at_level(logging.WARNING, logger="flywheel.storage"),
            pytest.raises(ValueError, match="Invalid JSON"),
        ):
            storage.load()

        # Verify WARNING log was emitted
        warning_logs = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_logs) >= 1, "Expected WARNING log for invalid JSON"

        # Verify log mentions JSON error
        log_messages = [r.message for r in warning_logs]
        log_text = " ".join(log_messages).lower()
        assert "json" in log_text or "invalid" in log_text, (
            f"Log should mention JSON issue: {log_messages}"
        )

    def test_no_logging_at_info_or_above_for_normal_ops(self, tmp_path, caplog):
        """Normal operations should not emit INFO or higher level logs by default."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save and load with INFO level (should not see any logs)
        with caplog.at_level(logging.INFO, logger="flywheel.storage"):
            storage.save([Todo(id=1, text="test")])
            storage.load()

        # Should not have any INFO, WARNING, or ERROR logs
        info_or_higher = [r for r in caplog.records if r.levelno >= logging.INFO]
        assert len(info_or_higher) == 0, (
            f"Normal ops should not emit INFO+ logs: {[r.message for r in info_or_higher]}"
        )
