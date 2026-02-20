"""Tests for storage debug logging feature (issue #4668).

This test suite verifies that TodoStorage produces DEBUG level logs
for load/save operations including file path, operation type, and data count.
"""

from __future__ import annotations

import logging
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestStorageDebugLogging:
    """Test debug logging for storage operations."""

    def test_load_produces_debug_log_with_path_and_count(self, tmp_path: Path, caplog) -> None:
        """Test that load produces DEBUG log with file path and data count."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save some todos first
        todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2")]
        storage.save(todos)

        # Load with DEBUG level logging
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        assert len(loaded) == 2

        # Verify debug log was produced
        debug_messages = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_messages) >= 1

        # Verify log contains file path
        log_message = debug_messages[0].message
        assert "load" in log_message.lower()
        assert str(db) in log_message or "todo.json" in log_message
        # Verify log contains data count
        assert "2" in log_message

    def test_save_produces_debug_log_with_path_and_count(self, tmp_path: Path, caplog) -> None:
        """Test that save produces DEBUG log with file path and data count."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2"), Todo(id=3, text="task 3")]

        # Save with DEBUG level logging
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # Verify debug log was produced
        debug_messages = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_messages) >= 1

        # Verify log contains file path and operation type
        log_message = debug_messages[0].message
        assert "save" in log_message.lower()
        assert str(db) in log_message or "todo.json" in log_message
        # Verify log contains data count
        assert "3" in log_message

    def test_load_empty_file_produces_debug_log(self, tmp_path: Path, caplog) -> None:
        """Test that load of empty file (no file) produces DEBUG log."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Load non-existent file with DEBUG level logging
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        assert len(loaded) == 0

        # Verify debug log was produced
        debug_messages = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_messages) >= 1

        # Verify log contains indication of empty/no file
        log_message = debug_messages[0].message
        assert "load" in log_message.lower()

    def test_default_config_no_log_output(self, tmp_path: Path, caplog) -> None:
        """Test that default config (WARNING level) produces no DEBUG logs."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # By default, logging is at WARNING level, so DEBUG should not appear
        todos = [Todo(id=1, text="task 1")]
        storage.save(todos)
        storage.load()

        # Note: This test verifies that logs are at DEBUG level, not emitted at WARNING
        # The actual filtering is done by the logging system based on configured level
        # By default no logs should be captured as the level is WARNING
        assert len(caplog.records) == 0
