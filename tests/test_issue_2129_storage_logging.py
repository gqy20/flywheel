"""Tests for issue #2129: Storage operation metrics/logging for debugging.

This test suite verifies that TodoStorage provides optional logging for
load() and save() operations to help debug file I/O issues.
"""

from __future__ import annotations

import logging
from unittest.mock import Mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_logs_file_path_and_entry_count(tmp_path, caplog) -> None:
    """Test that load() logs file path and entry count when logger is provided."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create test data
    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]
    storage.save(todos)

    # Create a new storage instance with a logger
    logger = logging.getLogger("test_storage")
    logger.setLevel(logging.DEBUG)
    storage_with_logger = TodoStorage(str(db), logger=logger)

    # Load with logging enabled
    with caplog.at_level(logging.DEBUG):
        loaded = storage_with_logger.load()

    # Verify logs contain file path and entry count
    assert len(loaded) == 2
    assert any(str(db) in record.message for record in caplog.records), \
        f"Expected file path {db} in logs, got: {[r.message for r in caplog.records]}"
    assert any("2" in record.message for record in caplog.records), \
        f"Expected entry count in logs, got: {[r.message for r in caplog.records]}"


def test_save_logs_file_path_entry_count_and_duration(tmp_path, caplog) -> None:
    """Test that save() logs file path, entry count, and duration when logger is provided."""
    db = tmp_path / "todo.json"

    logger = logging.getLogger("test_storage_save")
    logger.setLevel(logging.DEBUG)
    storage = TodoStorage(str(db), logger=logger)

    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2"), Todo(id=3, text="task3")]

    # Save with logging enabled
    with caplog.at_level(logging.DEBUG):
        storage.save(todos)

    # Verify logs contain file path, entry count, and timing info
    assert any(str(db) in record.message for record in caplog.records), \
        f"Expected file path {db} in logs, got: {[r.message for r in caplog.records]}"
    assert any("3" in record.message for record in caplog.records), \
        f"Expected entry count in logs, got: {[r.message for r in caplog.records]}"
    # Should have timing/duration logged
    assert any(
        any(word in record.message.lower() for word in ["ms", "s", "duration", "time", "took"])
        for record in caplog.records
    ), f"Expected timing info in logs, got: {[r.message for r in caplog.records]}"


def test_logger_disabled_when_none(tmp_path, caplog) -> None:
    """Test that no logging occurs when logger is None (default)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), logger=None)

    todos = [Todo(id=1, text="task1")]

    # Operations should not produce any logs when logger is None
    with caplog.at_level(logging.DEBUG):
        storage.save(todos)
        storage.load()

    assert len(caplog.records) == 0, \
        f"Expected no logs when logger=None, got: {[r.message for r in caplog.records]}"


def test_logger_works_with_custom_logger(tmp_path) -> None:
    """Test that a custom/mock logger receives correct log calls."""
    db = tmp_path / "todo.json"

    # Create a mock logger to track calls
    mock_logger = Mock()
    storage = TodoStorage(str(db), logger=mock_logger)

    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]

    # Save should trigger logger.debug/info calls
    storage.save(todos)

    # Verify logger was called for save
    assert mock_logger.called or mock_logger.debug.called or mock_logger.info.called, \
        "Expected logger to be called during save()"

    # Load should also trigger logger calls
    storage.load()

    # Verify logger was called for load as well
    call_count = (
        (mock_logger.call_count if mock_logger.called else 0) +
        mock_logger.debug.call_count +
        mock_logger.info.call_count
    )
    assert call_count > 0, "Expected logger to be called during load()"


def test_load_empty_file_logs_zero_entries(tmp_path, caplog) -> None:
    """Test that loading a non-existent file logs 0 entries."""
    db = tmp_path / "nonexistent.json"

    logger = logging.getLogger("test_storage_empty")
    logger.setLevel(logging.DEBUG)
    storage = TodoStorage(str(db), logger=logger)

    # Load from non-existent file should return empty list and log
    with caplog.at_level(logging.DEBUG):
        loaded = storage.load()

    assert len(loaded) == 0
    # Should still log the operation
    assert any(str(db) in record.message for record in caplog.records), \
        f"Expected file path in logs for empty load, got: {[r.message for r in caplog.records]}"
