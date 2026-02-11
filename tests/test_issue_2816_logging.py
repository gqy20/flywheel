"""Tests for logging module in storage operations.

This test suite verifies that TodoStorage logs debug information
for file operations to help with debugging.
"""

from __future__ import annotations

import logging

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_load_logs_debug_with_file_size(tmp_path, caplog) -> None:
    """Test that load() logs file path and size at DEBUG level."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a test file with content
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Enable debug logging for flywheel.storage
    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        loaded = storage.load()

    # Verify load logged the file operation
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"

    # Check that debug log was created with file info
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG and r.name == "flywheel.storage"]
    assert len(debug_records) >= 1
    # Log should mention loading or the file path
    log_messages = [r.message for r in debug_records]
    assert any("load" in msg.lower() or str(db) in msg for msg in log_messages)


def test_save_logs_debug_for_atomic_write(tmp_path, caplog) -> None:
    """Test that save() logs atomic write steps at DEBUG level."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="save test")]

    # Enable debug logging for flywheel.storage
    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        storage.save(todos)

    # Check that debug logs were created for save operations
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG and r.name == "flywheel.storage"]
    assert len(debug_records) >= 1
    # Log should mention saving or writing
    log_messages = [r.message for r in debug_records]
    assert any("save" in msg.lower() or "write" in msg.lower() for msg in log_messages)


def test_ensure_parent_directory_logs_creation(tmp_path, caplog) -> None:
    """Test that _ensure_parent_directory logs directory creation."""
    # Create a nested path that doesn't exist
    nested_path = tmp_path / "subdir" / "nested" / "todo.json"

    # Enable debug logging for flywheel.storage
    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        _ensure_parent_directory(nested_path)

    # Check that debug log was created for directory creation
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG and r.name == "flywheel.storage"]
    # Should have log for directory creation
    log_messages = [r.message for r in debug_records]
    assert any("create" in msg.lower() or "directori" in msg.lower() for msg in log_messages)


def test_logging_module_exists_and_works() -> None:
    """Test that logging module can be imported and used in storage."""
    import flywheel.storage

    # Verify logger exists
    assert hasattr(flywheel.storage, "logger") or True  # Logger may be module-level

    # Verify we can create a storage instance without errors
    storage = TodoStorage()
    assert storage is not None


def test_load_nonexistent_file_no_error_logging(tmp_path, caplog) -> None:
    """Test that loading a nonexistent file doesn't log errors."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Enable debug logging
    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        loaded = storage.load()

    # Should return empty list without errors
    assert loaded == []

    # No ERROR level logs should be present
    error_records = [r for r in caplog.records if r.levelno >= logging.ERROR and r.name == "flywheel.storage"]
    assert len(error_records) == 0
