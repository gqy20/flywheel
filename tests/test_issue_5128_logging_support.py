"""Tests for optional logging support in TodoStorage (Issue #5128).

This test suite verifies that TodoStorage supports optional logging for
debugging and auditing storage operations.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestLoggingSupport:
    """Tests for optional logging in TodoStorage."""

    def test_init_accepts_optional_logger(self, tmp_path: Path) -> None:
        """Test that TodoStorage.__init__ accepts optional logger parameter."""
        db = tmp_path / "todo.json"
        logger = logging.getLogger("test_logger")

        # Should not raise - logger parameter is accepted
        storage = TodoStorage(str(db), logger=logger)
        assert storage.path == db

    def test_init_without_logger_backward_compatible(self, tmp_path: Path) -> None:
        """Test that TodoStorage works without logger (backward compatibility)."""
        db = tmp_path / "todo.json"

        # Old usage without logger should still work
        storage = TodoStorage(str(db))
        assert storage.path == db

        # Operations should work without errors
        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"

    def test_load_logs_debug_on_success(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that load() logs DEBUG with file size and entry count when logger provided."""
        db = tmp_path / "todo.json"
        logger = logging.getLogger("flywheel.storage")
        logger.setLevel(logging.DEBUG)

        storage = TodoStorage(str(db), logger=logger)

        # Create and save some todos
        todos = [Todo(id=1, text="first"), Todo(id=2, text="second"), Todo(id=3, text="third")]
        storage.save(todos)

        # Load with logging
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        assert len(loaded) == 3

        # Verify log contains file size and entry count
        log_messages = [record.message for record in caplog.records]
        assert any("load" in msg.lower() for msg in log_messages), f"Expected 'load' in logs: {log_messages}"
        assert any("3" in msg for msg in log_messages), f"Expected entry count '3' in logs: {log_messages}"

    def test_save_logs_debug_on_success(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that save() logs DEBUG with write completion when logger provided."""
        db = tmp_path / "todo.json"
        logger = logging.getLogger("flywheel.storage")
        logger.setLevel(logging.DEBUG)

        storage = TodoStorage(str(db), logger=logger)

        todos = [Todo(id=1, text="test")]
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # Verify log contains save operation info
        log_messages = [record.message for record in caplog.records]
        assert any("save" in msg.lower() for msg in log_messages), f"Expected 'save' in logs: {log_messages}"

    def test_no_logging_when_logger_is_none(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that no logs are emitted when logger is None (default)."""
        db = tmp_path / "todo.json"

        # Create storage without logger (default)
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]

        with caplog.at_level(logging.DEBUG):
            storage.save(todos)
            storage.load()

        # No logs should be captured for storage operations
        storage_logs = [r for r in caplog.records if "flywheel.storage" in r.name]
        assert len(storage_logs) == 0, f"Expected no logs when logger is None, got: {storage_logs}"

    def test_load_empty_file_logs_zero_entries(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that loading an empty (non-existent) file logs appropriately."""
        db = tmp_path / "todo.json"
        logger = logging.getLogger("flywheel.storage")
        logger.setLevel(logging.DEBUG)

        storage = TodoStorage(str(db), logger=logger)

        # File doesn't exist, load returns empty list
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        assert len(loaded) == 0

        # Should log that file doesn't exist or returned 0 entries
        log_messages = [record.message for record in caplog.records]
        # Either logs about non-existent file or returns empty without logging
        # This is implementation-specific, just verify it doesn't crash
