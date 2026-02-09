"""Tests for file operation logging in TodoStorage (issue #2610).

This test suite verifies that TodoStorage logs file operations for debugging
and observability.
"""

from __future__ import annotations

from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_logs_debug_info(tmp_path) -> None:
    """Test that load() logs file path and todo count at DEBUG level."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create some todos first
    todos = [Todo(id=1, text="test task")]
    storage.save(todos)

    # Mock the logger to verify debug calls
    with patch("flywheel.storage.logger") as mock_logger:
        storage.load()

        # Verify DEBUG level logging was called
        mock_logger.debug.assert_called()
        # Check that the log call includes file path information
        call_args = str(mock_logger.debug.call_args)
        assert str(db) in call_args or "todo.json" in call_args


def test_load_logs_empty_file_handling(tmp_path) -> None:
    """Test that load() logs when file doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    with patch("flywheel.storage.logger") as mock_logger:
        result = storage.load()

        # Should return empty list
        assert result == []
        # Debug logging should still occur
        mock_logger.debug.assert_called()


def test_save_logs_atomic_write(tmp_path) -> None:
    """Test that save() logs atomic write operation at DEBUG level."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test task"), Todo(id=2, text="another task")]

    with patch("flywheel.storage.logger") as mock_logger:
        storage.save(todos)

        # Verify DEBUG level logging was called
        mock_logger.debug.assert_called()
        # Check that the log call includes write-related information
        call_args = str(mock_logger.debug.call_args)
        assert any(word in call_args.lower() for word in ["save", "write", "todo", "atomic"])


def test_logger_module_level_exists() -> None:
    """Test that storage module has a module-level logger."""
    import flywheel.storage

    # Verify logger exists at module level
    assert hasattr(flywheel.storage, "logger")
    # Verify it's a proper logger with debug method
    assert hasattr(flywheel.storage.logger, "debug")
