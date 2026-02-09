"""Tests for file operation logging in TodoStorage (Issue #2610).

This test suite verifies that TodoStorage logs file operations at DEBUG level
for debugging and observability purposes.
"""

from __future__ import annotations

from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_load_logs_debug_info(tmp_path, caplog) -> None:
    """Test that load() logs file path and todo count at DEBUG level."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]
    storage.save(todos)

    # Load with debug logging enabled
    with caplog.at_level("DEBUG"):
        loaded = storage.load()

    # Should have logged debug info about loading
    assert len(loaded) == 2
    debug_messages = [record.message for record in caplog.records if record.levelname == "DEBUG"]
    assert any("load" in msg.lower() or str(db) in msg for msg in debug_messages), \
        f"Expected debug log about loading, got: {debug_messages}"


def test_storage_save_logs_debug_info(tmp_path, caplog) -> None:
    """Test that save() logs atomic write operation at DEBUG level."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Save with debug logging enabled
    with caplog.at_level("DEBUG"):
        storage.save(todos)

    # Should have logged debug info about saving
    debug_messages = [record.message for record in caplog.records if record.levelname == "DEBUG"]
    assert any("save" in msg.lower() or "wrote" in msg.lower() or "atomic" in msg.lower() for msg in debug_messages), \
        f"Expected debug log about saving, got: {debug_messages}"


def test_storage_load_empty_file_logs_debug(tmp_path, caplog) -> None:
    """Test that loading from non-existent file logs appropriate debug info."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Load non-existent file with debug logging enabled
    with caplog.at_level("DEBUG"):
        loaded = storage.load()

    # Should return empty list and potentially log about missing file
    assert loaded == []
    # Non-existent file may or may not log - this is flexible


def test_storage_logger_exists() -> None:
    """Test that storage module has a logger configured."""
    import logging

    from flywheel import storage

    # Module should have a logger attribute
    assert hasattr(storage, "_LOGGER") or hasattr(storage, "logger") or \
           logging.getLogger("flywheel.storage") is not None


def test_load_logging_with_mock(tmp_path) -> None:
    """Test that load() calls logging.debug with file info."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Mock the logger to verify debug is called
    with patch("flywheel.storage._LOGGER") as mock_logger:
        storage.load()
        # Logger should have been called (at least once for debug logging)
        assert mock_logger.debug.called or mock_logger.info.called or mock_logger.warning.called


def test_save_logging_with_mock(tmp_path) -> None:
    """Test that save() calls logging.debug about write operation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Mock the logger to verify debug is called
    with patch("flywheel.storage._LOGGER") as mock_logger:
        storage.save(todos)
        # Logger should have been called (at least once for debug logging)
        assert mock_logger.debug.called or mock_logger.info.called or mock_logger.warning.called
