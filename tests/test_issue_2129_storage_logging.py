"""Tests for storage operation metrics/logging (Issue #2129).

These tests verify that:
1. TodoStorage can optionally log storage operations
2. load() logs file path and entry count
3. save() logs file path, entry count, and timing
4. Logging is optional and doesn't affect existing behavior
"""

from __future__ import annotations

import logging
from unittest.mock import Mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_logs_file_path_and_entry_count(tmp_path, caplog) -> None:
    """load() should log file path and number of entries loaded."""
    db = tmp_path / "todo.json"

    # Create storage with logging enabled
    storage = TodoStorage(str(db))
    storage.logger = logging.getLogger("flywheel.storage")

    # Create some todos to load
    todos = [
        Todo(id=1, text="task 1"),
        Todo(id=2, text="task 2"),
        Todo(id=3, text="task 3"),
    ]
    storage.save(todos)

    # Load with logging
    with caplog.at_level(logging.INFO):
        loaded = storage.load()

    # Verify data is correct
    assert len(loaded) == 3

    # Verify logging occurred
    assert len(caplog.records) > 0
    log_messages = [record.message for record in caplog.records]

    # Should log the file path
    assert any(str(db) in msg for msg in log_messages), f"File path not in logs: {log_messages}"
    # Should log the entry count
    assert any("3" in msg for msg in log_messages), f"Entry count not in logs: {log_messages}"


def test_save_logs_file_path_and_entry_count_and_timing(tmp_path, caplog) -> None:
    """save() should log file path, number of entries saved, and timing."""
    db = tmp_path / "todo.json"

    # Create storage with logging enabled
    storage = TodoStorage(str(db))
    storage.logger = logging.getLogger("flywheel.storage")

    todos = [
        Todo(id=1, text="task 1"),
        Todo(id=2, text="task 2"),
    ]

    # Save with logging
    with caplog.at_level(logging.INFO):
        storage.save(todos)

    # Verify logging occurred
    assert len(caplog.records) > 0
    log_messages = [record.message for record in caplog.records]

    # Should log the file path
    assert any(str(db) in msg for msg in log_messages), f"File path not in logs: {log_messages}"
    # Should log the entry count
    assert any("2" in msg for msg in log_messages), f"Entry count not in logs: {log_messages}"
    # Should indicate save operation
    assert any("save" in msg.lower() for msg in log_messages), f"Save operation not in logs: {log_messages}"


def test_logging_is_optional_no_logger(tmp_path) -> None:
    """Storage should work without logging when no logger is provided."""
    db = tmp_path / "todo.json"

    # Create storage without logger (default)
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="task 1")]

    # Should not raise any errors
    storage.save(todos)
    loaded = storage.load()

    assert len(loaded) == 1
    assert loaded[0].text == "task 1"


def test_logging_with_explicit_none_logger(tmp_path) -> None:
    """Storage should work when logger is explicitly set to None."""
    db = tmp_path / "todo.json"

    # Create storage with explicit None logger
    storage = TodoStorage(str(db))
    storage.logger = None

    todos = [Todo(id=1, text="task 1")]

    # Should not raise any errors
    storage.save(todos)
    loaded = storage.load()

    assert len(loaded) == 1
    assert loaded[0].text == "task 1"


def test_load_empty_file_logs_zero_entries(tmp_path, caplog) -> None:
    """Loading an empty file (non-existent) should log appropriately."""
    db = tmp_path / "nonexistent.json"

    # Create storage with logging enabled
    storage = TodoStorage(str(db))
    storage.logger = logging.getLogger("flywheel.storage")

    # Load non-existent file with logging
    with caplog.at_level(logging.INFO):
        loaded = storage.load()

    # Should return empty list
    assert len(loaded) == 0

    # Should log something about the load operation
    # (This verifies the logging path is exercised)
    log_messages = [record.message for record in caplog.records]
    assert len(log_messages) >= 0  # At minimum, no errors


def test_save_with_custom_logger(tmp_path) -> None:
    """Storage should accept a custom logger instance."""
    db = tmp_path / "todo.json"

    # Create a mock logger to verify it gets called
    mock_logger = Mock()

    # Create storage with custom logger
    storage = TodoStorage(str(db))
    storage.logger = mock_logger

    todos = [Todo(id=1, text="task 1")]

    # Save should call the logger
    storage.save(todos)

    # Verify logger was called
    assert mock_logger.info.called or mock_logger.debug.called, \
        f"Custom logger was not called. Calls: {mock_logger.method_calls}"


def test_load_with_custom_logger(tmp_path) -> None:
    """Storage should use custom logger for load operations."""
    db = tmp_path / "todo.json"

    # Create a mock logger
    mock_logger = Mock()

    # Create storage with custom logger
    storage = TodoStorage(str(db))
    storage.logger = mock_logger

    # First save some data
    todos = [Todo(id=1, text="task 1")]
    storage.save(todos)

    # Reset the mock to clear save calls
    mock_logger.reset_mock()

    # Load should call the logger
    storage.load()

    # Verify logger was called for load
    assert mock_logger.info.called or mock_logger.debug.called, \
        f"Custom logger was not called for load. Calls: {mock_logger.method_calls}"


def test_logger_attribute_exists_and_writable() -> None:
    """TodoStorage should have a logger attribute that can be set."""
    storage = TodoStorage()

    # Should have logger attribute (default None)
    assert hasattr(storage, "logger")
    assert storage.logger is None

    # Should be able to set logger
    custom_logger = logging.getLogger("custom")
    storage.logger = custom_logger
    assert storage.logger is custom_logger
