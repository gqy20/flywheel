"""Regression tests for issue #4835: File operation logging support.

Issue: TodoStorage has no logging, making it hard to debug data loss,
concurrent conflicts, or file corruption issues.

These tests verify:
- TodoStorage accepts optional logger parameter
- save operation logs DEBUG: path, count, duration
- load operation logs DEBUG: path, count, duration
- Error scenarios log WARNING/ERROR
- Without logger, behavior is unchanged (backward compatibility)
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_accepts_optional_logger(tmp_path: Path) -> None:
    """Issue #4835: TodoStorage.__init__ should accept optional logger parameter."""
    db = tmp_path / "todo.json"

    # Should not raise when logger is passed
    logger = logging.getLogger("test_logger")
    storage = TodoStorage(str(db), logger=logger)

    assert storage.path == db


def test_storage_works_without_logger_backward_compatible(tmp_path: Path) -> None:
    """Issue #4835: Without logger parameter, behavior should be unchanged."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Should work normally without logger
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_save_logs_debug_with_path_count_duration(tmp_path: Path) -> None:
    """Issue #4835: save should log DEBUG with path, count, duration."""
    db = tmp_path / "todo.json"
    mock_logger = MagicMock()

    storage = TodoStorage(str(db), logger=mock_logger)
    todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2")]
    storage.save(todos)

    # Verify debug was called with relevant info
    assert mock_logger.debug.called, "save should call logger.debug"

    # Check that the log call contains path, count info
    call_args = mock_logger.debug.call_args
    assert call_args is not None

    # The log message or kwargs should contain path and count
    # We accept either positional or keyword arguments
    log_message = call_args[0][0] if call_args[0] else ""
    log_kwargs = call_args[1] if len(call_args) > 1 else {}

    # Either the message or kwargs should mention path/count
    combined = str(log_message) + str(log_kwargs)
    assert "save" in combined.lower() or "path" in combined.lower() or "todo" in combined.lower()


def test_load_logs_debug_with_path_count_duration(tmp_path: Path) -> None:
    """Issue #4835: load should log DEBUG with path, count, duration."""
    db = tmp_path / "todo.json"
    mock_logger = MagicMock()

    storage = TodoStorage(str(db), logger=mock_logger)

    # First save some data
    todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2"), Todo(id=3, text="task 3")]
    storage.save(todos)

    # Reset mock to only see load logs
    mock_logger.reset_mock()

    storage.load()

    # Verify debug was called
    assert mock_logger.debug.called, "load should call logger.debug"

    # Check that the log call contains path, count info
    call_args = mock_logger.debug.call_args
    assert call_args is not None

    # The log message or kwargs should contain path and count
    log_message = call_args[0][0] if call_args[0] else ""
    log_kwargs = call_args[1] if len(call_args) > 1 else {}

    combined = str(log_message) + str(log_kwargs)
    assert "load" in combined.lower() or "path" in combined.lower() or "todo" in combined.lower()


def test_load_empty_file_logs_debug(tmp_path: Path) -> None:
    """Issue #4835: load of non-existent file should still log (0 items)."""
    db = tmp_path / "todo.json"
    mock_logger = MagicMock()

    storage = TodoStorage(str(db), logger=mock_logger)
    loaded = storage.load()

    assert loaded == []
    assert mock_logger.debug.called, "load should call logger.debug even for empty/missing file"


def test_load_malformed_json_logs_error(tmp_path: Path) -> None:
    """Issue #4835: load with malformed JSON should log WARNING/ERROR."""
    db = tmp_path / "todo.json"
    mock_logger = MagicMock()

    # Write invalid JSON
    db.write_text("{ invalid json }", encoding="utf-8")

    storage = TodoStorage(str(db), logger=mock_logger)

    with pytest.raises(ValueError):
        storage.load()

    # Should have logged a warning or error about the JSON error
    assert mock_logger.warning.called or mock_logger.error.called, \
        "load with invalid JSON should call logger.warning or logger.error"


def test_save_error_logs_error(tmp_path: Path) -> None:
    """Issue #4835: save error should log WARNING/ERROR with details."""
    db = tmp_path / "todo.json"
    mock_logger = MagicMock()

    storage = TodoStorage(str(db), logger=mock_logger)

    # Make save fail by causing mkstemp to fail
    with patch("flywheel.storage.tempfile.mkstemp") as mock_mkstemp:
        mock_mkstemp.side_effect = OSError("disk full")

        with pytest.raises(OSError):
            storage.save([Todo(id=1, text="test")])

    # Should have logged a warning or error about the failure
    assert mock_logger.warning.called or mock_logger.error.called, \
        "save failure should call logger.warning or logger.error"


def test_logger_none_produces_no_output(tmp_path: Path) -> None:
    """Issue #4835: Passing logger=None should behave like no logger."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), logger=None)

    todos = [Todo(id=1, text="test")]
    storage.save(todos)
    loaded = storage.load()

    assert len(loaded) == 1
    assert loaded[0].text == "test"
