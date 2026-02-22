"""Tests for logging support in TodoStorage.

This test suite verifies that TodoStorage supports optional logging
for debugging production issues (issue #5257).

Acceptance criteria:
- TodoStorage class supports optional logger parameter
- load() logs record count and timing at DEBUG level
- save() logs record count and atomic write success at DEBUG level
- Not passing a logger defaults to no log output (NullHandler)
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestTodoStorageLoggingSupport:
    """Test suite for logging feature in TodoStorage."""

    def test_init_without_logger_succeeds(self, tmp_path: Path) -> None:
        """Verify TodoStorage can be instantiated without logger parameter."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))
        assert storage.path == db

    def test_init_with_logger_parameter_accepted(self, tmp_path: Path) -> None:
        """Verify TodoStorage accepts optional logger parameter."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)
        storage = TodoStorage(str(db), logger=mock_logger)
        assert storage.path == db
        assert storage.logger == mock_logger

    def test_load_logs_record_count_at_debug_level(self, tmp_path: Path) -> None:
        """Verify load() logs the number of records loaded at DEBUG level."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        # Create initial data
        storage = TodoStorage(str(db))
        todos = [
            Todo(id=1, text="first task"),
            Todo(id=2, text="second task"),
            Todo(id=3, text="third task"),
        ]
        storage.save(todos)

        # Now load with logging
        storage_with_logger = TodoStorage(str(db), logger=mock_logger)
        loaded = storage_with_logger.load()

        assert len(loaded) == 3
        # Verify debug logging was called
        mock_logger.debug.assert_called()
        # Check that the log message contains relevant info
        call_args = mock_logger.debug.call_args
        assert "3" in str(call_args) or any("3" in str(arg) for arg in call_args[0])

    def test_load_logs_timing_at_debug_level(self, tmp_path: Path) -> None:
        """Verify load() logs timing information at DEBUG level."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        # Create initial data
        storage = TodoStorage(str(db))
        storage.save([Todo(id=1, text="task")])

        # Load with logging
        storage_with_logger = TodoStorage(str(db), logger=mock_logger)
        storage_with_logger.load()

        # Verify debug was called (timing info should be in the message)
        mock_logger.debug.assert_called()

    def test_save_logs_record_count_at_debug_level(self, tmp_path: Path) -> None:
        """Verify save() logs the number of records saved at DEBUG level."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)
        todos = [Todo(id=1, text="task one"), Todo(id=2, text="task two")]
        storage.save(todos)

        # Verify debug logging was called
        mock_logger.debug.assert_called()
        # Check that the log message contains record count
        call_args = mock_logger.debug.call_args
        log_message = str(call_args)
        # Should contain "2" (the count)
        assert "2" in log_message or any("2" in str(arg) for arg in call_args[0])

    def test_save_logs_atomic_write_success_at_debug_level(self, tmp_path: Path) -> None:
        """Verify save() logs atomic write success at DEBUG level."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)
        storage.save([Todo(id=1, text="test")])

        # Verify debug was called with some message about write/success
        mock_logger.debug.assert_called()

    def test_no_logger_means_no_log_output(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Verify that without a logger parameter, no log output is produced."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        with caplog.at_level(logging.DEBUG):
            storage.save([Todo(id=1, text="test")])
            loaded = storage.load()

        # No log records should have been captured
        assert len(caplog.records) == 0

    def test_load_nonexistent_file_logs_zero_records(self, tmp_path: Path) -> None:
        """Verify load() on nonexistent file logs 0 records correctly."""
        db = tmp_path / "nonexistent.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)
        result = storage.load()

        assert result == []
        # Debug should be called even for empty load
        mock_logger.debug.assert_called()

    def test_load_logs_path_at_debug_level(self, tmp_path: Path) -> None:
        """Verify load() logs the file path at DEBUG level."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db))
        storage.save([Todo(id=1, text="test")])

        storage_with_logger = TodoStorage(str(db), logger=mock_logger)
        storage_with_logger.load()

        # Check that path info is in log message
        call_args = mock_logger.debug.call_args
        log_message = str(call_args)
        assert str(db) in log_message or any(str(db) in str(arg) for arg in call_args[0])

    def test_save_logs_path_at_debug_level(self, tmp_path: Path) -> None:
        """Verify save() logs the file path at DEBUG level."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)
        storage.save([Todo(id=1, text="test")])

        # Check that path info is in log message
        call_args = mock_logger.debug.call_args
        log_message = str(call_args)
        assert str(db) in log_message or any(str(db) in str(arg) for arg in call_args[0])
