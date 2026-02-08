"""Tests for storage operation logging in TodoStorage.

This test suite verifies that TodoStorage provides optional logging
for debugging storage operations (load/save).
"""

from __future__ import annotations

import logging
from unittest.mock import Mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_without_logger_backward_compatible(tmp_path) -> None:
    """Test that load works without a logger (backward compatibility)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create test data
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Load without logger - should work fine
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_save_without_logger_backward_compatible(tmp_path) -> None:
    """Test that save works without a logger (backward compatibility)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save without logger - should work fine
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Verify data was saved
    loaded = storage.load()
    assert len(loaded) == 1


def test_load_with_logger_logs_operation_details(tmp_path) -> None:
    """Test that load with logger logs file path, entry count, and timing."""
    db = tmp_path / "todo.json"
    mock_logger = Mock(spec=logging.Logger)

    storage = TodoStorage(str(db), logger=mock_logger)

    # Create test data
    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]
    storage.save(todos)  # Save without logging for this test

    # Load with logging
    loaded = storage.load()

    # Verify the data was loaded correctly
    assert len(loaded) == 2

    # Verify logger was called with appropriate details
    assert mock_logger.debug.called
    log_message = mock_logger.debug.call_args[0][0]

    # Check that log contains key information
    assert str(db) in log_message or db.name in log_message
    assert "2" in log_message  # Entry count


def test_save_with_logger_logs_operation_details(tmp_path) -> None:
    """Test that save with logger logs file path, entry count, and timing."""
    db = tmp_path / "todo.json"
    mock_logger = Mock(spec=logging.Logger)

    storage = TodoStorage(str(db), logger=mock_logger)

    # Save with logging
    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2"), Todo(id=3, text="task3")]
    storage.save(todos)

    # Verify logger was called with appropriate details
    assert mock_logger.debug.called
    log_message = mock_logger.debug.call_args[0][0]

    # Check that log contains key information
    assert str(db) in log_message or db.name in log_message
    assert "3" in log_message  # Entry count


def test_load_empty_file_with_logger(tmp_path) -> None:
    """Test that loading from non-existent file with logger logs appropriately."""
    db = tmp_path / "nonexistent.json"
    mock_logger = Mock(spec=logging.Logger)

    storage = TodoStorage(str(db), logger=mock_logger)

    # Load from non-existent file
    loaded = storage.load()

    # Should return empty list
    assert loaded == []

    # Logger should still be called (for the operation attempt)
    assert mock_logger.debug.called


def test_logger_parameter_accepts_none(tmp_path) -> None:
    """Test that logger parameter accepts None explicitly."""
    db = tmp_path / "todo.json"

    # Should not raise any errors
    storage = TodoStorage(str(db), logger=None)

    todos = [Todo(id=1, text="test")]
    storage.save(todos)
    loaded = storage.load()

    assert len(loaded) == 1


def test_load_logs_include_timing_information(tmp_path) -> None:
    """Test that load logs include timing/duration information."""
    db = tmp_path / "todo.json"
    mock_logger = Mock(spec=logging.Logger)

    storage = TodoStorage(str(db), logger=mock_logger)

    # Create test data
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Load with logging
    storage.load()

    # Check that timing information is logged
    log_message = mock_logger.debug.call_args[0][0]
    # Timing should be included (check for common timing indicators)
    assert any(keyword in log_message.lower() for keyword in ["ms", "s", "time", "duration", "took"])


def test_save_logs_include_timing_information(tmp_path) -> None:
    """Test that save logs include timing/duration information."""
    db = tmp_path / "todo.json"
    mock_logger = Mock(spec=logging.Logger)

    storage = TodoStorage(str(db), logger=mock_logger)

    # Save with logging
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Check that timing information is logged
    log_message = mock_logger.debug.call_args[0][0]
    # Timing should be included (check for common timing indicators)
    assert any(keyword in log_message.lower() for keyword in ["ms", "s", "time", "duration", "took"])


def test_multiple_operations_with_same_logger(tmp_path) -> None:
    """Test that the same logger instance is used across multiple operations."""
    db = tmp_path / "todo.json"
    mock_logger = Mock(spec=logging.Logger)

    storage = TodoStorage(str(db), logger=mock_logger)

    # Perform multiple operations
    todos1 = [Todo(id=1, text="first")]
    storage.save(todos1)

    storage.load()

    todos2 = [Todo(id=1, text="updated"), Todo(id=2, text="second")]
    storage.save(todos2)

    loaded2 = storage.load()

    # All operations should have been logged
    assert mock_logger.debug.call_count >= 4  # save, load, save, load

    # Verify final state
    assert len(loaded2) == 2
    assert loaded2[0].text == "updated"
    assert loaded2[1].text == "second"
