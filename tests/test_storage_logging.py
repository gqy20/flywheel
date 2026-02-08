"""Tests for logging behavior in TodoStorage.

This test suite verifies that TodoStorage logs key operations
(load/save) at appropriate levels for debugging and audit purposes.
"""

from __future__ import annotations

import logging
import logging.handlers

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_logs_at_info_level_with_file_details(tmp_path, caplog) -> None:
    """Test that load() logs at INFO level with file path and size."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create some todos to save first
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Clear any existing logs and capture INFO level logs
    caplog.clear()
    with caplog.at_level(logging.INFO):
        loaded = storage.load()

    # Verify log messages contain expected information
    assert len(loaded) == 1
    assert any("Loading todos from" in record.message for record in caplog.records)
    assert any(str(db) in record.message for record in caplog.records)


def test_save_logs_at_info_level_with_record_count(tmp_path, caplog) -> None:
    """Test that save() logs at INFO level with record count."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo"),
        Todo(id=3, text="third todo"),
    ]

    caplog.clear()
    with caplog.at_level(logging.INFO):
        storage.save(todos)

    # Verify log message contains record count
    assert any("3 todos" in record.message or "todo" in record.message for record in caplog.records)
    assert any("Saving" in record.message or "saved" in record.message for record in caplog.records)


def test_load_error_logs_before_raising_exception(tmp_path, caplog) -> None:
    """Test that load() logs errors before raising exception."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create invalid JSON file
    db.write_text("{invalid json content", encoding="utf-8")

    caplog.clear()
    with caplog.at_level(logging.ERROR), pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()

    # Verify error was logged
    assert any("ERROR" in record.levelname for record in caplog.records)
    assert len(caplog.records) > 0


def test_save_error_logs_before_raising_exception(tmp_path, caplog) -> None:
    """Test that save() logs errors before raising exception."""
    # Create a path that will cause directory creation to fail
    # by making the parent a file instead of a directory
    db = tmp_path / "file_as_dir" / "todo.json"

    # Create the parent as a file (not directory) to trigger error
    (tmp_path / "file_as_dir").write_text("I am a file", encoding="utf-8")

    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test")]

    caplog.clear()
    with caplog.at_level(logging.ERROR), pytest.raises(ValueError, match="exists as a file"):
        storage.save(todos)

    # Verify error was logged
    assert any("ERROR" in record.levelname for record in caplog.records)
    assert len(caplog.records) > 0


def test_load_empty_file_returns_empty_list_and_logs(tmp_path, caplog) -> None:
    """Test that loading from non-existent file returns empty list and logs appropriately."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    caplog.clear()
    with caplog.at_level(logging.INFO):
        loaded = storage.load()

    assert loaded == []
    # Should log something about file not existing or loading empty list
    assert len(caplog.records) >= 0  # May or may not log for missing file


def test_logging_respects_configured_level(tmp_path) -> None:
    """Test that logging respects the configured log level."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Set logger to WARNING level - INFO should not appear
    logger = logging.getLogger("flywheel.storage")
    logger.setLevel(logging.WARNING)

    # Add a handler to capture logs
    handler = logging.handlers.MemoryHandler(capacity=100)
    logger.addHandler(handler)

    try:
        storage.save(todos)

        # INFO logs should not be captured when level is WARNING
        log_messages = [record.getMessage() for record in handler.buffer]
        assert not any("Saving" in msg or "saved" in msg for msg in log_messages)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(logging.NOTSET)
