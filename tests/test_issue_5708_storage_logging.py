"""Tests for issue #5708: Add logging functionality to TodoStorage.

This test suite verifies that TodoStorage supports optional logging for
load() and save() operations to aid debugging and audit trail.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestTodoStorageLogging:
    """Tests for optional logging in TodoStorage."""

    def test_storage_accepts_optional_logger_parameter(self) -> None:
        """TodoStorage.__init__ should accept an optional logger parameter."""
        # Should not raise
        logger = logging.getLogger("test_logger")
        storage = TodoStorage(path="/tmp/test.json", logger=logger)
        assert storage.logger is logger

    def test_storage_defaults_to_none_logger(self) -> None:
        """TodoStorage should default to None logger if not provided."""
        storage = TodoStorage(path="/tmp/test.json")
        assert storage.logger is None

    def test_load_logs_debug_with_logger(self, tmp_path: Path) -> None:
        """load() should log DEBUG message with file path and record count when logger is provided."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save some test data
        todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2")]
        storage.save(todos)

        # Create storage with mock logger
        mock_logger = MagicMock(spec=logging.Logger)
        storage_with_logger = TodoStorage(str(db), logger=mock_logger)

        # Load should trigger logging
        loaded = storage_with_logger.load()

        # Verify data loaded correctly
        assert len(loaded) == 2

        # Verify logger.debug was called
        mock_logger.debug.assert_called()
        # Check the call contains relevant info
        call_args = mock_logger.debug.call_args
        assert "load" in str(call_args).lower()
        assert "todo.json" in str(call_args) or str(db) in str(call_args)

    def test_save_logs_debug_with_logger(self, tmp_path: Path) -> None:
        """save() should log DEBUG message with file path and record count when logger is provided."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)
        storage = TodoStorage(str(db), logger=mock_logger)

        # Save should trigger logging
        todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2"), Todo(id=3, text="task 3")]
        storage.save(todos)

        # Verify logger.debug was called
        mock_logger.debug.assert_called()
        # Check the call contains relevant info
        call_args = mock_logger.debug.call_args
        assert "save" in str(call_args).lower()
        assert "todo.json" in str(call_args) or str(db) in str(call_args)

    def test_no_logging_when_logger_is_none(self, tmp_path: Path) -> None:
        """When logger is None, no logging should occur (zero overhead)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), logger=None)

        # Patch logging.getLogger to ensure it's never called
        with patch("flywheel.storage.logging") as mock_logging:
            todos = [Todo(id=1, text="task")]
            storage.save(todos)
            _ = storage.load()

            # Verify no logging module calls were made
            assert not mock_logging.debug.called
            assert not mock_logging.info.called

    def test_load_logs_record_count(self, tmp_path: Path) -> None:
        """load() debug log should include the number of records loaded."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save 5 records
        todos = [Todo(id=i, text=f"task {i}") for i in range(1, 6)]
        storage.save(todos)

        # Load with logger
        mock_logger = MagicMock(spec=logging.Logger)
        storage_with_logger = TodoStorage(str(db), logger=mock_logger)
        storage_with_logger.load()

        # Check that record count (5) is in the log message
        call_args = mock_logger.debug.call_args
        assert "5" in str(call_args)

    def test_save_logs_record_count(self, tmp_path: Path) -> None:
        """save() debug log should include the number of records saved."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)
        storage = TodoStorage(str(db), logger=mock_logger)

        # Save 3 records
        todos = [Todo(id=i, text=f"task {i}") for i in range(1, 4)]
        storage.save(todos)

        # Check that record count (3) is in the log message
        call_args = mock_logger.debug.call_args
        assert "3" in str(call_args)

    def test_load_empty_file_logs_zero_records(self, tmp_path: Path) -> None:
        """load() should log 0 records when loading empty/non-existent file."""
        db = tmp_path / "nonexistent.json"
        mock_logger = MagicMock(spec=logging.Logger)
        storage = TodoStorage(str(db), logger=mock_logger)

        # Load from non-existent file
        loaded = storage.load()

        # Should return empty list
        assert loaded == []

        # Should still log the operation
        mock_logger.debug.assert_called()
        call_args = mock_logger.debug.call_args
        assert "0" in str(call_args)

    def test_backwards_compatibility_without_logger(self, tmp_path: Path) -> None:
        """Existing code without logger parameter should continue to work."""
        db = tmp_path / "todo.json"
        # Old usage without logger parameter
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="backwards compatible")]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "backwards compatible"
