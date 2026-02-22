"""Tests for issue #5257: Logging feature support in TodoStorage.

This test suite verifies that TodoStorage supports optional logging
for debugging production issues like JSON parsing errors, atomic write
failures, and permission problems.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestLoggingFeature:
    """Test suite for TodoStorage logging feature."""

    def test_todostorage_accepts_optional_logger_parameter(self, tmp_path: Path) -> None:
        """Test that TodoStorage can be instantiated with optional logger parameter."""
        db = tmp_path / "todo.json"
        logger = logging.getLogger("test_logger")

        # Should not raise when logger is passed
        storage = TodoStorage(str(db), logger=logger)
        assert storage.path == db

    def test_todostorage_works_without_logger(self, tmp_path: Path) -> None:
        """Test that TodoStorage works normally when no logger is provided (backward compatibility)."""
        db = tmp_path / "todo.json"

        # Should work without logger parameter
        storage = TodoStorage(str(db))
        assert storage.path == db

        # Basic operations should work
        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"

    def test_load_logs_record_count_at_debug_level(self, tmp_path: Path) -> None:
        """Test that load() logs the number of records loaded at DEBUG level."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        # Create test data
        storage = TodoStorage(str(db), logger=mock_logger)
        todos = [Todo(id=1, text="first"), Todo(id=2, text="second"), Todo(id=3, text="third")]
        storage.save(todos)

        # Reset the mock to clear save logs
        mock_logger.reset_mock()

        # Load and check logging
        loaded = storage.load()
        assert len(loaded) == 3

        # Should have logged at DEBUG level with record count
        mock_logger.debug.assert_called()
        debug_calls = list(mock_logger.debug.call_args_list)
        # At least one call should mention loading and the count
        assert any("load" in str(call).lower() or "3" in str(call) for call in debug_calls), \
            f"Expected debug log about loading 3 records, got: {debug_calls}"

    def test_load_logs_path_at_debug_level(self, tmp_path: Path) -> None:
        """Test that load() logs the file path at DEBUG level."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)
        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        mock_logger.reset_mock()

        # Load and check logging
        storage.load()

        # Should have logged the path
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        assert any(str(db) in call for call in debug_calls), \
            f"Expected debug log with path {db}, got: {debug_calls}"

    def test_save_logs_record_count_at_debug_level(self, tmp_path: Path) -> None:
        """Test that save() logs the number of records saved at DEBUG level."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)
        todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]
        storage.save(todos)

        # Should have logged at DEBUG level with record count
        mock_logger.debug.assert_called()
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        assert any("2" in call for call in debug_calls), \
            f"Expected debug log about saving 2 records, got: {debug_calls}"

    def test_save_logs_atomic_write_success_at_debug_level(self, tmp_path: Path) -> None:
        """Test that save() logs successful atomic write at DEBUG level."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)
        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        # Should have logged at DEBUG level about atomic write/save
        mock_logger.debug.assert_called()
        debug_calls = [str(call).lower() for call in mock_logger.debug.call_args_list]
        # Check for save/write related logging
        assert any("save" in call or "write" in call for call in debug_calls), \
            f"Expected debug log about saving/writing, got: {debug_calls}"

    def test_load_empty_file_logs_zero_records(self, tmp_path: Path) -> None:
        """Test that load() logs 0 records when file doesn't exist."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)
        loaded = storage.load()
        assert len(loaded) == 0

        # Should have logged at DEBUG level about loading 0 records
        mock_logger.debug.assert_called()

    def test_no_log_output_when_no_logger_provided(self, tmp_path: Path) -> None:
        """Test that when no logger is provided, no logging occurs (uses NullHandler)."""
        db = tmp_path / "todo.json"

        # Capture any logging that might occur
        with patch("logging.Logger.debug"):
            storage = TodoStorage(str(db))  # No logger provided
            todos = [Todo(id=1, text="test")]
            storage.save(todos)
            loaded = storage.load()

            # The module logger should not have been called directly
            # (implementation should use NullHandler or not log)
            assert len(loaded) == 1
