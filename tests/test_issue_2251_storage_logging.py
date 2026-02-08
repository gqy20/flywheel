"""Tests for storage logging (issue #2251).

This test suite verifies that TodoStorage operations log appropriately
for debugging and audit purposes.
"""

from __future__ import annotations

import logging

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_logs_on_success(tmp_path, caplog) -> None:
    """Test that successful load operations log at INFO level."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Load with logging capture
    with caplog.at_level(logging.INFO):
        loaded = storage.load()

    assert len(loaded) == 1
    # Should log the load operation
    assert any("load" in record.message.lower() for record in caplog.records)


def test_load_includes_file_path_and_count(tmp_path, caplog) -> None:
    """Test that load logs include file path and record count."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]
    storage.save(todos)

    # Load with logging capture
    with caplog.at_level(logging.INFO):
        storage.load()

    # Check logs contain file path and count
    log_messages = [record.message for record in caplog.records]
    assert any(str(db) in msg for msg in log_messages), "Log should include file path"
    assert any("3" in msg for msg in log_messages), "Log should include record count"


def test_save_logs_on_success(tmp_path, caplog) -> None:
    """Test that successful save operations log at INFO level."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Save with logging capture
    with caplog.at_level(logging.INFO):
        storage.save(todos)

    # Should log the save operation
    assert any("save" in record.message.lower() for record in caplog.records)


def test_save_includes_file_path_and_count(tmp_path, caplog) -> None:
    """Test that save logs include file path and record count."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
    ]

    # Save with logging capture
    with caplog.at_level(logging.INFO):
        storage.save(todos)

    # Check logs contain file path and count
    log_messages = [record.message for record in caplog.records]
    assert any(str(db) in msg for msg in log_messages), "Log should include file path"
    assert any("2" in msg for msg in log_messages), "Log should include record count"


def test_load_logs_error_before_raising(tmp_path, caplog) -> None:
    """Test that load errors are logged before raising exceptions."""
    db = tmp_path / "todo.json"
    # Write invalid JSON
    db.write_text("{ invalid json", encoding="utf-8")

    storage = TodoStorage(str(db))

    # Load with logging capture
    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(ValueError, match="Invalid JSON"),
    ):
        storage.load()

    # Should log the error
    assert any(record.levelno >= logging.ERROR for record in caplog.records)


def test_save_logs_error_before_raising(tmp_path, caplog) -> None:
    """Test that save errors are logged before raising exceptions."""
    # Create a file that blocks directory creation
    db = tmp_path / "blockfile" / "todo.json"
    # Create the blockfile
    db.parent.write_text("I am a file, not a directory")

    storage = TodoStorage(str(db))

    # Save with logging capture
    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(ValueError),
    ):
        storage.save([Todo(id=1, text="test")])

    # Should log the error
    assert any(record.levelno >= logging.ERROR for record in caplog.records)


def test_load_nonexistent_returns_empty_no_error_log(tmp_path, caplog) -> None:
    """Test that loading nonexistent file returns empty list without error."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Load with logging capture
    with caplog.at_level(logging.WARNING):
        loaded = storage.load()

    assert loaded == []
    # Should not log errors for nonexistent file (expected case)
    assert not any(record.levelno >= logging.ERROR for record in caplog.records)


def test_logger_respects_log_level_debug(tmp_path, caplog) -> None:
    """Test that DEBUG level can be configured for verbose output."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Set DEBUG level
    with caplog.at_level(logging.DEBUG):
        storage.save(todos)
        storage.load()

    # Should have some log records
    assert len(caplog.records) > 0
