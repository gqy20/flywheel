"""Tests for logging in TodoStorage load/save operations.

This test suite verifies that TodoStorage can optionally log load/save
operations when a logger is provided.
"""

from __future__ import annotations

import logging
import logging.handlers

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_with_logger_logs_debug_message(tmp_path) -> None:
    """Test that load() logs DEBUG message with file path and entry count when logger provided."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), logger=logging.getLogger("test"))

    # Create a file with 3 todos
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]
    storage.save(todos)

    # Capture logs at DEBUG level
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.MemoryHandler(capacity=100)
    logger.addHandler(handler)

    try:
        loaded = storage.load()
        handler.flush()

        # Verify we got the right data
        assert len(loaded) == 3

        # Verify log was captured (at DEBUG level)
        assert len(handler.buffer) >= 1
        log_record = handler.buffer[0]
        assert log_record.levelno == logging.DEBUG
        # Log should contain file path and count info
        assert str(db) in log_record.getMessage() or "3" in log_record.getMessage()
    finally:
        logger.removeHandler(handler)


def test_save_with_logger_logs_debug_message(tmp_path) -> None:
    """Test that save() logs DEBUG message with file path and entry count when logger provided."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_save")
    storage = TodoStorage(str(db), logger=logger)

    # Capture logs at DEBUG level
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.MemoryHandler(capacity=100)
    logger.addHandler(handler)

    try:
        todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]
        storage.save(todos)
        handler.flush()

        # Verify log was captured (at DEBUG level)
        assert len(handler.buffer) >= 1
        log_record = handler.buffer[0]
        assert log_record.levelno == logging.DEBUG
        # Log should contain file path and count info
        msg = log_record.getMessage()
        assert str(db) in msg or "2" in msg
    finally:
        logger.removeHandler(handler)


def test_default_none_logger_no_logs(tmp_path, caplog) -> None:
    """Test that default behavior (no logger) produces no log output."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))  # No logger provided

    with caplog.at_level(logging.DEBUG):
        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        _loaded = storage.load()

    # No logs should have been produced by storage
    storage_logs = [r for r in caplog.records if "storage" in r.name or "flywheel" in r.name]
    # Storage operations should not produce logs when no logger provided
    assert len(storage_logs) == 0


def test_logger_parameter_can_be_set_at_init(tmp_path) -> None:
    """Test that logger can be passed to __init__ and is stored."""
    logger = logging.getLogger("custom_logger")
    storage = TodoStorage(str(tmp_path / "todo.json"), logger=logger)

    assert storage.logger is logger


def test_logger_default_is_none(tmp_path) -> None:
    """Test that logger defaults to None when not provided."""
    storage = TodoStorage(str(tmp_path / "todo.json"))
    assert storage.logger is None


def test_load_empty_file_with_logger_no_error(tmp_path) -> None:
    """Test that loading a non-existent file with logger doesn't error."""
    db = tmp_path / "nonexistent.json"
    logger = logging.getLogger("test_empty")
    storage = TodoStorage(str(db), logger=logger)

    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.MemoryHandler(capacity=100)
    logger.addHandler(handler)

    try:
        result = storage.load()
        handler.flush()

        # Should return empty list
        assert result == []
        # May or may not log, but should not error
    finally:
        logger.removeHandler(handler)
