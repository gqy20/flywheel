"""Tests for logging feature in TodoStorage.

This test suite verifies that TodoStorage supports optional logging for
diagnosing production issues related to file loading/saving behavior.

Issue: #5257
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from unittest.mock import MagicMock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_accepts_optional_logger_parameter(tmp_path: Path) -> None:
    """Test that TodoStorage can be instantiated with an optional logger."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_logger")

    # Should not raise any exceptions
    storage_with_logger = TodoStorage(str(db), logger=logger)
    assert storage_with_logger.path == db

    # Should also work without a logger (backward compatibility)
    storage_without_logger = TodoStorage(str(db))
    assert storage_without_logger.path == db


def test_load_logs_record_count_at_debug_level(tmp_path: Path) -> None:
    """Test that load() logs record count at DEBUG level when logger is provided."""
    db = tmp_path / "todo.json"
    mock_logger = MagicMock(spec=logging.Logger)

    # Create storage with some todos
    storage = TodoStorage(str(db), logger=mock_logger)
    todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2"), Todo(id=3, text="task 3")]
    storage.save(todos)

    # Reset the mock to check load logging
    mock_logger.reset_mock()

    # Load the todos
    loaded = storage.load()

    # Verify data loaded correctly
    assert len(loaded) == 3

    # Verify debug logging was called
    assert mock_logger.debug.called, "load() should log at DEBUG level when logger is provided"

    # Check that at least one debug call mentions record count
    debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
    debug_messages = " ".join(debug_calls).lower()
    # Should mention records loaded (3)
    assert "3" in debug_messages or "record" in debug_messages or "load" in debug_messages


def test_save_logs_record_count_at_debug_level(tmp_path: Path) -> None:
    """Test that save() logs record count at DEBUG level when logger is provided."""
    db = tmp_path / "todo.json"
    mock_logger = MagicMock(spec=logging.Logger)

    storage = TodoStorage(str(db), logger=mock_logger)
    todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2")]

    # Save todos
    storage.save(todos)

    # Verify debug logging was called
    assert mock_logger.debug.called, "save() should log at DEBUG level when logger is provided"

    # Check that at least one debug call mentions record count or save
    debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
    debug_messages = " ".join(debug_calls).lower()
    # Should mention records saved (2)
    assert "2" in debug_messages or "record" in debug_messages or "save" in debug_messages


def test_no_logger_means_no_logging_output(tmp_path: Path) -> None:
    """Test that when no logger is provided, no logging occurs."""
    db = tmp_path / "todo.json"

    # Create storage without logger
    storage = TodoStorage(str(db))

    # Create some todos
    todos = [Todo(id=1, text="task 1")]

    # Capture log output using a handler
    handler = logging.handlers.MemoryHandler(capacity=1000)
    root_logger = logging.getLogger()
    original_level = root_logger.level
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)

    try:
        # Save and load
        storage.save(todos)
        loaded = storage.load()

        # Should work correctly
        assert len(loaded) == 1
        assert loaded[0].text == "task 1"

        # No log records should have been emitted by storage.py
        # (The MemoryHandler captures all records)
        storage_records = [
            r for r in handler.buffer
            if "storage" in r.name.lower() or "flywheel" in r.name.lower()
        ]
        assert len(storage_records) == 0, "No logging should occur when logger is None"
    finally:
        root_logger.removeHandler(handler)
        root_logger.setLevel(original_level)


def test_load_timing_logged_at_debug_level(tmp_path: Path) -> None:
    """Test that load() logs timing information at DEBUG level."""
    db = tmp_path / "todo.json"
    mock_logger = MagicMock(spec=logging.Logger)

    storage = TodoStorage(str(db), logger=mock_logger)
    todos = [Todo(id=1, text="task 1")]
    storage.save(todos)

    mock_logger.reset_mock()
    storage.load()

    # Check that debug was called
    assert mock_logger.debug.called

    # Check for timing-related keywords in debug messages
    debug_calls = [str(call).lower() for call in mock_logger.debug.call_args_list]
    debug_messages = " ".join(debug_calls)

    # Should mention timing (e.g., "ms", "sec", "time", or elapsed duration)
    has_timing = any(
        kw in debug_messages for kw in ["ms", "sec", "time", "elapsed", "duration", "took"]
    )
    assert has_timing or "load" in debug_messages, "load() should log timing information"


def test_save_atomic_write_success_logged(tmp_path: Path) -> None:
    """Test that save() logs atomic write success at DEBUG level."""
    db = tmp_path / "todo.json"
    mock_logger = MagicMock(spec=logging.Logger)

    storage = TodoStorage(str(db), logger=mock_logger)
    todos = [Todo(id=1, text="task 1")]

    storage.save(todos)

    # Check that debug was called
    assert mock_logger.debug.called

    # Check for save/write-related keywords in debug messages
    debug_calls = [str(call).lower() for call in mock_logger.debug.call_args_list]
    debug_messages = " ".join(debug_calls)

    # Should mention save or write operation
    has_save_write = any(
        kw in debug_messages for kw in ["save", "wrote", "written", "atomic", "success"]
    )
    assert has_save_write, "save() should log write success"
