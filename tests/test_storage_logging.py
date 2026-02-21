"""Tests for logging in TodoStorage load/save operations.

This test suite verifies that TodoStorage can optionally log load/save operations
for debugging purposes, while maintaining backward-compatible silent default behavior.
"""

from __future__ import annotations

import logging
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_logs_debug_when_logger_provided(tmp_path: Path, caplog) -> None:
    """Test that load() logs DEBUG message with file path and entry count when logger is provided."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create some todos
    todos = [Todo(id=1, text="first"), Todo(id=2, text="second"), Todo(id=3, text="third")]
    storage.save(todos)

    # Create a logger and pass it to storage
    test_logger = logging.getLogger("test_storage")
    storage_with_logger = TodoStorage(str(db), logger=test_logger)

    with caplog.at_level(logging.DEBUG, logger="test_storage"):
        loaded = storage_with_logger.load()

    # Verify data loaded correctly
    assert len(loaded) == 3

    # Verify log was captured
    assert any("load" in record.message.lower() for record in caplog.records), \
        f"Expected 'load' in log messages, got: {[r.message for r in caplog.records]}"
    assert any(str(db) in record.message for record in caplog.records), \
        f"Expected file path in log messages, got: {[r.message for r in caplog.records]}"
    assert any("3" in record.message for record in caplog.records), \
        f"Expected entry count '3' in log messages, got: {[r.message for r in caplog.records]}"


def test_save_logs_debug_when_logger_provided(tmp_path: Path, caplog) -> None:
    """Test that save() logs DEBUG message with file path and entry count when logger is provided."""
    db = tmp_path / "todo.json"

    # Create a logger and pass it to storage
    test_logger = logging.getLogger("test_storage_save")
    storage = TodoStorage(str(db), logger=test_logger)

    todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]

    with caplog.at_level(logging.DEBUG, logger="test_storage_save"):
        storage.save(todos)

    # Verify log was captured
    assert any("save" in record.message.lower() for record in caplog.records), \
        f"Expected 'save' in log messages, got: {[r.message for r in caplog.records]}"
    assert any(str(db) in record.message for record in caplog.records), \
        f"Expected file path in log messages, got: {[r.message for r in caplog.records]}"
    assert any("2" in record.message for record in caplog.records), \
        f"Expected entry count '2' in log messages, got: {[r.message for r in caplog.records]}"


def test_default_no_logger_is_silent(tmp_path: Path, caplog) -> None:
    """Test that default behavior (no logger) produces no log output."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Capture all logging at DEBUG level
    with caplog.at_level(logging.DEBUG):
        # Save and load without logger
        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        storage.load()

    # No log records should be produced
    assert len(caplog.records) == 0, \
        f"Expected no log records, got: {[r.message for r in caplog.records]}"


def test_logger_none_parameter_is_silent(tmp_path: Path, caplog) -> None:
    """Test that passing logger=None produces no log output."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), logger=None)

    # Capture all logging at DEBUG level
    with caplog.at_level(logging.DEBUG):
        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        storage.load()

    # No log records should be produced
    assert len(caplog.records) == 0, \
        f"Expected no log records, got: {[r.message for r in caplog.records]}"
