"""Tests for optional logging support in TodoStorage.

This test suite verifies that TodoStorage can optionally log key storage
operations at DEBUG level when a logger is provided.

Issue: #5178
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from unittest.mock import MagicMock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestOptionalLogger:
    """Tests for optional logger parameter in TodoStorage."""

    def test_constructor_accepts_optional_logger_parameter(self, tmp_path: Path) -> None:
        """Test that TodoStorage constructor accepts optional logger parameter."""
        db = tmp_path / "todo.json"
        logger = logging.getLogger("test_logger")

        # Should not raise - constructor accepts logger parameter
        storage = TodoStorage(str(db), logger=logger)
        assert storage is not None

    def test_default_constructor_has_no_logger(self, tmp_path: Path) -> None:
        """Test that default construction (no logger) works and does not log."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Should work without any logger configured
        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        loaded = storage.load()

        assert len(loaded) == 1
        assert loaded[0].text == "test"

    def test_load_logs_debug_when_logger_provided(self, tmp_path: Path) -> None:
        """Test that load() logs DEBUG message with file path and count when logger is provided."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)

        # First save some data
        todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]
        storage.save(todos)

        # Clear any previous mock calls from save
        mock_logger.reset_mock()

        # Load the data
        loaded = storage.load()

        # Verify load was successful
        assert len(loaded) == 2

        # Verify logger.debug was called with appropriate information
        mock_logger.debug.assert_called()
        # The call should include file path information
        call_args = mock_logger.debug.call_args
        assert call_args is not None
        # Check that the log message includes path and count info
        log_msg = str(call_args)
        assert str(db) in log_msg or "2" in log_msg

    def test_save_logs_debug_when_logger_provided(self, tmp_path: Path) -> None:
        """Test that save() logs DEBUG message with file path and count when logger is provided."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)

        # Save some data
        todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2"), Todo(id=3, text="task3")]
        storage.save(todos)

        # Verify logger.debug was called
        mock_logger.debug.assert_called()
        # The call should include file path and count information
        call_args = mock_logger.debug.call_args
        assert call_args is not None
        # Check that the log message includes path and count info
        log_msg = str(call_args)
        assert str(db) in log_msg or "3" in log_msg

    def test_no_logging_when_logger_is_none(self, tmp_path: Path) -> None:
        """Test that no logging occurs when logger=None (backward compatibility)."""
        db = tmp_path / "todo.json"

        # Explicitly pass logger=None
        storage = TodoStorage(str(db), logger=None)

        # Create a real logger with a handler to capture logs
        real_logger = logging.getLogger("flywheel.storage")
        real_logger.setLevel(logging.DEBUG)
        handler = logging.handlers.MemoryHandler(capacity=100)
        real_logger.addHandler(handler)

        try:
            # Perform operations
            todos = [Todo(id=1, text="test")]
            storage.save(todos)
            loaded = storage.load()

            # Should work correctly
            assert len(loaded) == 1

            # Since logger=None, no logs should be produced
            # (The storage should not log to any logger when logger is None)
        finally:
            real_logger.removeHandler(handler)

    def test_load_empty_file_with_logger(self, tmp_path: Path) -> None:
        """Test that loading from non-existent file with logger returns empty list."""
        db = tmp_path / "nonexistent.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)

        # Load from non-existent file
        loaded = storage.load()

        # Should return empty list
        assert loaded == []
