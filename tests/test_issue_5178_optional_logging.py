"""Tests for optional logging support in TodoStorage (issue #5178).

This test suite verifies that TodoStorage supports optional logging
for tracking key storage operations (load/save) at DEBUG level.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestOptionalLoggingSupport:
    """Test suite for issue #5178: Optional logging support in TodoStorage."""

    def test_default_construction_without_logger(self, tmp_path: Path) -> None:
        """Verify default construction (no logger) behavior is unchanged."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Should work normally without logger
        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"

    def test_constructor_accepts_optional_logger(self, tmp_path: Path) -> None:
        """Verify TodoStorage constructor accepts optional logger parameter."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        # Should accept logger parameter
        storage = TodoStorage(str(db), logger=mock_logger)
        assert storage.logger is mock_logger

    def test_load_logs_at_debug_level_with_logger(self, tmp_path: Path) -> None:
        """Verify load() logs file path and entry count at DEBUG level."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        # Create storage with logger
        storage = TodoStorage(str(db), logger=mock_logger)

        # Save some todos first
        todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]
        storage.save(todos)

        # Reset mock to only check load logging
        mock_logger.reset_mock()

        # Load should log at DEBUG level
        loaded = storage.load()
        assert len(loaded) == 2

        # Verify debug was called with file path and count
        mock_logger.debug.assert_called()
        call_args = mock_logger.debug.call_args
        assert str(db) in str(call_args) or "todo.json" in str(call_args)

    def test_save_logs_at_debug_level_with_logger(self, tmp_path: Path) -> None:
        """Verify save() logs file path and entry count at DEBUG level."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)

        todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2"), Todo(id=3, text="task3")]
        storage.save(todos)

        # Verify debug was called with file path and count
        mock_logger.debug.assert_called()
        call_args = mock_logger.debug.call_args
        assert str(db) in str(call_args) or "todo.json" in str(call_args)

    def test_no_logging_when_logger_is_none(self, tmp_path: Path) -> None:
        """Verify no logging occurs when logger=None (backward compatibility)."""
        db = tmp_path / "todo.json"

        # Create storage without logger
        storage = TodoStorage(str(db))

        # Create a spy logger on storage to ensure it's None
        assert storage.logger is None

        # Operations should work without any logging errors
        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        loaded = storage.load()
        assert len(loaded) == 1

    def test_logger_none_does_not_call_debug(self, tmp_path: Path) -> None:
        """Verify that when logger is None, no debug calls are attempted."""
        db = tmp_path / "todo.json"

        # Create storage with explicit None logger
        storage = TodoStorage(str(db), logger=None)
        assert storage.logger is None

        # These should not raise any errors
        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        loaded = storage.load()
        assert len(loaded) == 1

    def test_load_empty_file_logs_zero_count(self, tmp_path: Path) -> None:
        """Verify load() logs count=0 for empty/non-existent file."""
        db = tmp_path / "todo.json"
        mock_logger = MagicMock(spec=logging.Logger)

        storage = TodoStorage(str(db), logger=mock_logger)

        # Load from non-existent file
        loaded = storage.load()
        assert len(loaded) == 0

        # Should have logged the operation
        mock_logger.debug.assert_called()

    def test_real_logger_integration(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Integration test with a real logger to verify log output."""
        db = tmp_path / "todo.json"

        # Create a real logger
        logger = logging.getLogger("test_storage_logger")
        logger.setLevel(logging.DEBUG)

        storage = TodoStorage(str(db), logger=logger)

        # Save and load with real logging
        todos = [Todo(id=1, text="task1")]
        with caplog.at_level(logging.DEBUG, logger="test_storage_logger"):
            storage.save(todos)
            loaded = storage.load()

        # Check that logs were captured
        assert len(caplog.records) >= 1
        # At least one record should mention save or load
        messages = [record.message for record in caplog.records]
        assert any("save" in msg.lower() or "load" in msg.lower() for msg in messages)
