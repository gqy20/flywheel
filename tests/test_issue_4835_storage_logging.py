"""Test logging support for TodoStorage operations.

Issue #4835: Add file operation logging support
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestStorageLogging:
    """Tests for optional logging in TodoStorage."""

    def test_no_logger_param_no_logging(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        """When no logger is passed, no log output should occur."""
        db_path = tmp_path / "test.json"
        storage = TodoStorage(str(db_path))

        # Save and load operations should not produce any logs
        with caplog.at_level(logging.DEBUG):
            todos = [Todo(id=1, text="Test", done=False)]
            storage.save(todos)
            _loaded = storage.load()

        # Should not produce any log records (from storage.py)
        storage_logs = [r for r in caplog.records if "storage" in r.pathname]
        assert len(storage_logs) == 0

    def test_logger_param_save_logs_debug(self, tmp_path: Path):
        """When logger is provided, save should log DEBUG with path/count/elapsed."""
        mock_logger = MagicMock(spec=logging.Logger)
        db_path = tmp_path / "test.json"
        storage = TodoStorage(str(db_path), logger=mock_logger)

        todos = [Todo(id=1, text="Test 1", done=False), Todo(id=2, text="Test 2", done=True)]
        storage.save(todos)

        # Verify save logged at DEBUG level
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args

        # Check the log message format string and args contain key information
        msg = call_args[0][0]
        args = call_args[0][1:]
        assert "save" in msg.lower()
        assert "path" in msg.lower()
        assert str(db_path) in str(args)  # path is passed as an argument
        assert "2" in str(args)  # count of todos
        assert "elapsed" in msg.lower()

    def test_logger_param_load_logs_debug(self, tmp_path: Path):
        """When logger is provided, load should log DEBUG with path/count/elapsed."""
        mock_logger = MagicMock(spec=logging.Logger)
        db_path = tmp_path / "test.json"
        storage = TodoStorage(str(db_path), logger=mock_logger)

        # First save some data
        todos = [Todo(id=1, text="Test 1", done=False), Todo(id=2, text="Test 2", done=True)]
        storage.save(todos)

        # Reset mock to only check load
        mock_logger.reset_mock()

        # Now load
        _loaded = storage.load()

        # Verify load logged at DEBUG level
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args

        # Check the log message format string and args contain key information
        msg = call_args[0][0]
        args = call_args[0][1:]
        assert "load" in msg.lower()
        assert "path" in msg.lower()
        assert str(db_path) in str(args)  # path is passed as an argument
        assert "2" in str(args)  # count of todos
        assert "elapsed" in msg.lower()

    def test_logger_load_empty_file_logs_debug(self, tmp_path: Path):
        """When logger is provided and loading empty/nonexistent file, should log DEBUG."""
        mock_logger = MagicMock(spec=logging.Logger)
        db_path = tmp_path / "test.json"
        storage = TodoStorage(str(db_path), logger=mock_logger)

        # Load from nonexistent file
        _loaded = storage.load()

        # Should still log (even for empty load)
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        msg = call_args[0][0]
        assert "load" in msg.lower()
        assert "0" in msg  # count of todos

    def test_logger_error_on_invalid_json_logs_warning(self, tmp_path: Path):
        """When logger is provided and JSON is invalid, should log at WARNING level."""
        mock_logger = MagicMock(spec=logging.Logger)
        db_path = tmp_path / "test.json"
        storage = TodoStorage(str(db_path), logger=mock_logger)

        # Write invalid JSON
        db_path.write_text("not valid json {{{")

        # Loading should raise and log
        with pytest.raises(ValueError):
            storage.load()

        # Should log at warning level for the error
        assert mock_logger.warning.called or mock_logger.error.called

    def test_logger_error_on_file_too_large_logs_warning(self, tmp_path: Path):
        """When logger is provided and file is too large, should log at WARNING level."""
        mock_logger = MagicMock(spec=logging.Logger)
        db_path = tmp_path / "test.json"
        storage = TodoStorage(str(db_path), logger=mock_logger)

        # Write a valid JSON array larger than limit (10MB)
        # Create a list of simple JSON objects
        items = []
        for i in range(20000):  # 20000 items should exceed 10MB
            items.append(f'{{"id": {i}, "text": "{"x" * 500}", "done": false}}')
        large_content = "[" + ",".join(items) + "]"
        db_path.write_text(large_content)

        # Loading should raise and log
        with pytest.raises(ValueError, match="too large"):
            storage.load()

        # Should log at warning level for the error
        assert mock_logger.warning.called or mock_logger.error.called

    def test_logger_param_accepts_real_logger(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        """Logger parameter should work with real logging.Logger instances."""
        logger = logging.getLogger("test_storage")
        logger.setLevel(logging.DEBUG)

        db_path = tmp_path / "test.json"
        storage = TodoStorage(str(db_path), logger=logger)

        with caplog.at_level(logging.DEBUG, logger="test_storage"):
            todos = [Todo(id=1, text="Test", done=False)]
            storage.save(todos)
            _loaded = storage.load()

        # Should have log records for both save and load
        assert len(caplog.records) >= 2
        messages = [r.message.lower() for r in caplog.records]
        assert any("save" in m for m in messages)
        assert any("load" in m for m in messages)
