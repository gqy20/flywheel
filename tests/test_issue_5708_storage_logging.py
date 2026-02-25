"""Tests for storage operation logging feature (issue #5708).

This test suite verifies that TodoStorage can optionally log operations
to aid debugging and audit trails.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestStorageLogging:
    """Tests for optional logging in TodoStorage."""

    def test_load_with_logger_none_does_not_error(self, tmp_path: Path) -> None:
        """Test that load() works without logger (backward compatibility)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), logger=None)

        # Should not raise any errors
        todos = storage.load()
        assert todos == []

    def test_save_with_logger_none_does_not_error(self, tmp_path: Path) -> None:
        """Test that save() works without logger (backward compatibility)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), logger=None)

        todos = [Todo(id=1, text="test")]
        # Should not raise any errors
        storage.save(todos)

    def test_load_logs_debug_on_success(self, tmp_path: Path) -> None:
        """Test that load() logs DEBUG message with file path and record count."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)

        # Create some data to load
        todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]
        storage.save(todos)

        # Reset mock to clear save log
        mock_logger.reset_mock()

        # Load the data
        loaded = storage.load()
        assert len(loaded) == 2

        # Verify debug was called with path and count
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert str(db) in str(call_args)
        assert "2" in str(call_args)  # record count

    def test_save_logs_debug_on_success(self, tmp_path: Path) -> None:
        """Test that save() logs DEBUG message with file path and record count."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        # Verify debug was called with path and count
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert str(db) in str(call_args)
        assert "1" in str(call_args)  # record count

    def test_load_empty_file_logs_zero_records(self, tmp_path: Path) -> None:
        """Test that loading non-existent file logs 0 records."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)

        # Load from non-existent file
        todos = storage.load()
        assert len(todos) == 0

        # Verify debug was called with count 0
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert "0" in str(call_args)  # record count

    def test_no_logging_overhead_when_logger_is_none(self, tmp_path: Path) -> None:
        """Test that logger=None produces no log output (zero overhead)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), logger=None)

        # Perform operations - should not attempt any logging
        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        loaded = storage.load()

        assert len(loaded) == 1
        # If logger is None, no logging should occur (this is implicit)
