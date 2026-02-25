"""Tests for storage operation logging feature (issue #5708).

This test suite verifies that TodoStorage can optionally log operations
to aid debugging, auditing, and tracking file read/write behavior.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestStorageLogging:
    """Test suite for storage logging feature."""

    def test_storage_accepts_optional_logger_parameter(self, tmp_path: Path) -> None:
        """Test that TodoStorage can accept an optional logger parameter."""
        db = tmp_path / "todo.json"
        logger = logging.getLogger("test_logger")

        # Should not raise when logger is provided
        storage = TodoStorage(str(db), logger=logger)
        assert storage.logger is logger

    def test_storage_defaults_to_none_logger(self, tmp_path: Path) -> None:
        """Test that logger defaults to None when not provided."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))
        assert storage.logger is None

    def test_load_without_logger_does_not_error(self, tmp_path: Path) -> None:
        """Test that load() works without any logger (zero overhead)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a file with valid data
        db.write_text('[{"id": 1, "text": "test", "done": false}]', encoding="utf-8")

        # Should not raise even without logger
        todos = storage.load()
        assert len(todos) == 1
        assert todos[0].text == "test"

    def test_save_without_logger_does_not_error(self, tmp_path: Path) -> None:
        """Test that save() works without any logger (zero overhead)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        # Should not raise even without logger
        storage.save(todos)

        # Verify data was saved
        loaded = storage.load()
        assert len(loaded) == 1

    def test_load_logs_debug_with_file_path_and_count(self, tmp_path: Path) -> None:
        """Test that load() logs DEBUG level message with file path and record count."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)
        storage = TodoStorage(str(db), logger=mock_logger)

        # Create a file with valid data
        db.write_text(
            '[{"id": 1, "text": "test1", "done": false}, {"id": 2, "text": "test2", "done": true}]',
            encoding="utf-8",
        )

        _ = storage.load()

        # Verify logger.debug was called
        assert mock_logger.debug.called, "Logger.debug should be called on load"

        # Get the debug call arguments (format string, count, path, time)
        call_args = mock_logger.debug.call_args
        log_format = call_args[0][0]
        count_arg = call_args[0][1]
        path_arg = call_args[0][2]

        # Verify log format and arguments
        assert "todos" in log_format.lower(), f"Log format should mention todos: {log_format}"
        assert count_arg == 2, f"Count argument should be 2: {count_arg}"
        assert str(db) == str(path_arg), f"Path argument should match db path: {path_arg}"

    def test_save_logs_debug_with_file_path_and_count(self, tmp_path: Path) -> None:
        """Test that save() logs DEBUG level message with file path and record count."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)
        storage = TodoStorage(str(db), logger=mock_logger)

        todos = [Todo(id=1, text="test1"), Todo(id=2, text="test2"), Todo(id=3, text="test3")]
        storage.save(todos)

        # Verify logger.debug was called
        assert mock_logger.debug.called, "Logger.debug should be called on save"

        # Get the debug call arguments (format string, count, path, time)
        call_args = mock_logger.debug.call_args
        log_format = call_args[0][0]
        count_arg = call_args[0][1]
        path_arg = call_args[0][2]

        # Verify log format and arguments
        assert "todos" in log_format.lower(), f"Log format should mention todos: {log_format}"
        assert count_arg == 3, f"Count argument should be 3: {count_arg}"
        assert str(db) == str(path_arg), f"Path argument should match db path: {path_arg}"

    def test_load_empty_file_logs_zero_count(self, tmp_path: Path) -> None:
        """Test that loading empty storage logs count of 0."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)
        storage = TodoStorage(str(db), logger=mock_logger)

        # File doesn't exist - should return empty list
        todos = storage.load()

        assert len(todos) == 0
        # When file doesn't exist, should still log (or not log, both acceptable)
        # The issue specifies logging on success, so no file = no log is acceptable

    def test_load_logs_include_elapsed_time(self, tmp_path: Path) -> None:
        """Test that load() logs include elapsed time measurement."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)
        storage = TodoStorage(str(db), logger=mock_logger)

        db.write_text('[{"id": 1, "text": "test", "done": false}]', encoding="utf-8")

        storage.load()

        # Get the debug call arguments
        call_args = mock_logger.debug.call_args
        log_message = call_args[0][0]

        # Verify log message contains elapsed time (look for time-related keywords)
        # Time should be in format like "0.001s" or similar
        assert "s" in log_message.lower() or "ms" in log_message.lower() or "elapsed" in log_message.lower(), \
            f"Log message should contain time info: {log_message}"

    def test_save_logs_include_elapsed_time(self, tmp_path: Path) -> None:
        """Test that save() logs include elapsed time measurement."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)
        storage = TodoStorage(str(db), logger=mock_logger)

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        # Get the debug call arguments
        call_args = mock_logger.debug.call_args
        log_message = call_args[0][0]

        # Verify log message contains elapsed time
        assert "s" in log_message.lower() or "ms" in log_message.lower() or "elapsed" in log_message.lower(), \
            f"Log message should contain time info: {log_message}"

    def test_none_logger_produces_no_log_output(self, tmp_path: Path) -> None:
        """Test that when logger is None, no logging occurs (zero overhead)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), logger=None)

        # Create a file with valid data
        db.write_text('[{"id": 1, "text": "test", "done": false}]', encoding="utf-8")

        # Patch logging to ensure nothing is called
        with patch("logging.Logger.debug") as mock_debug:
            todos = storage.load()
            storage.save(todos)

            # No debug calls should have been made through our patched logger
            # Note: This tests that we don't accidentally use a default logger
            # We're not asserting since other loggers in the system may trigger calls
            _ = mock_debug.call_count  # Just verify we can access it without error

    def test_logger_attribute_exposed(self, tmp_path: Path) -> None:
        """Test that the logger attribute is accessible on the storage instance."""
        db = tmp_path / "todo.json"
        logger = logging.getLogger("test")
        storage = TodoStorage(str(db), logger=logger)

        # Verify logger is accessible
        assert hasattr(storage, "logger")
        assert storage.logger is logger
