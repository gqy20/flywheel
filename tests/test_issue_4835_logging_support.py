"""Tests for logging support in TodoStorage (Issue #4835).

This test suite verifies that TodoStorage supports optional logging
for debugging data loss, concurrency conflicts, or file corruption.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestLoggingSupport:
    """Test suite for optional logging in TodoStorage."""

    def test_no_logger_no_logs(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that without a logger parameter, no logs are produced."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]

        with caplog.at_level(logging.DEBUG):
            storage.save(todos)
            loaded = storage.load()

        # No logs should be captured when no logger is provided
        assert len(caplog.records) == 0
        assert len(loaded) == 1
        assert loaded[0].text == "test"

    def test_logger_parameter_in_init(self, tmp_path: Path) -> None:
        """Test that TodoStorage accepts an optional logger parameter."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)

        assert storage.logger is mock_logger

    def test_save_logs_path_count_and_duration(self, tmp_path: Path) -> None:
        """Test that save logs DEBUG with path, count, and duration."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)
        todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]

        storage.save(todos)

        # Verify debug was called with path, count, and timing info
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        log_msg = call_args[0][0]

        # Check that log contains key information
        assert "save" in log_msg.lower()
        assert str(db) in log_msg or db.name in log_msg
        assert "2" in log_msg  # count

    def test_load_logs_path_count_and_duration(self, tmp_path: Path) -> None:
        """Test that load logs DEBUG with path, count, and duration."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)

        # First save some data
        todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2"), Todo(id=3, text="task3")]
        storage.save(todos)

        # Reset mock to focus on load call
        mock_logger.reset_mock()

        loaded = storage.load()

        # Verify debug was called with path, count, and timing info
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        log_msg = call_args[0][0]

        # Check that log contains key information
        assert "load" in log_msg.lower()
        assert str(db) in log_msg or db.name in log_msg
        assert "3" in log_msg  # count
        assert len(loaded) == 3

    def test_load_nonexistent_file_no_error_log(self, tmp_path: Path) -> None:
        """Test that loading a nonexistent file doesn't produce error logs."""
        db = tmp_path / "nonexistent.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)

        loaded = storage.load()

        # File doesn't exist, so no data to load - shouldn't log errors
        assert len(loaded) == 0
        # No logging for non-existent file (normal case)
        mock_logger.debug.assert_not_called()
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

    def test_load_invalid_json_logs_warning(self, tmp_path: Path) -> None:
        """Test that loading invalid JSON logs a warning with error details."""
        db = tmp_path / "invalid.json"
        mock_logger = MagicMock(spec=logging.Logger)

        # Write invalid JSON
        db.write_text("{ invalid json", encoding="utf-8")

        storage = TodoStorage(str(db), logger=mock_logger)

        with pytest.raises(ValueError):
            storage.load()

        # Should have logged a warning about the invalid JSON
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        log_msg = call_args[0][0]

        assert "invalid" in log_msg.lower() or "json" in log_msg.lower()

    def test_save_error_logs_error(self, tmp_path: Path) -> None:
        """Test that save errors log with error details."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)
        todos = [Todo(id=1, text="test")]

        # Simulate write failure during os.replace
        with (
            patch("flywheel.storage.os.replace", side_effect=OSError("disk full")),
            pytest.raises(OSError),
        ):
            storage.save(todos)

        # Should have logged an error
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        log_msg = call_args[0][0]

        assert "save" in log_msg.lower() or "error" in log_msg.lower()

    def test_backward_compatibility_without_logger(self, tmp_path: Path) -> None:
        """Test that existing code without logger parameter still works."""
        db = tmp_path / "todo.json"

        # Create storage without logger (existing behavior)
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="backward compatible")]
        storage.save(todos)
        loaded = storage.load()

        assert len(loaded) == 1
        assert loaded[0].text == "backward compatible"

    def test_none_logger_same_as_no_logger(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that passing logger=None is the same as not passing logger."""
        db = tmp_path / "todo.json"

        storage = TodoStorage(str(db), logger=None)

        todos = [Todo(id=1, text="test")]

        with caplog.at_level(logging.DEBUG):
            storage.save(todos)
            loaded = storage.load()

        # No logs should be captured when logger is None
        assert len(caplog.records) == 0
        assert len(loaded) == 1
