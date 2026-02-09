"""Tests for issue #2610: File operation logging in TodoStorage.

Verifies that TodoStorage logs file operations at DEBUG level for
improved observability and debugging capability.
"""

from __future__ import annotations

from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_logs_debug_info(tmp_path) -> None:
    """Test that load() logs file path and todo count at DEBUG level."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create some todos to load
    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]
    storage.save(todos)

    # Mock the logger to verify debug calls
    with patch("flywheel.storage.logger") as mock_logger:
        storage.load()

        # Verify debug was called at least once with file path info
        assert mock_logger.debug.called, "logger.debug should be called during load"
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        # Check that the file path is logged
        assert any(str(db) in call for call in debug_calls), f"File path {db} should be in debug logs"


def test_load_empty_file_logs_debug_info(tmp_path) -> None:
    """Test that load() logs when file doesn't exist (returns empty list)."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    with patch("flywheel.storage.logger") as mock_logger:
        loaded = storage.load()

        # Should return empty list
        assert loaded == []
        # Debug logging should still occur
        assert mock_logger.debug.called, "logger.debug should be called even when file doesn't exist"


def test_save_logs_debug_info(tmp_path) -> None:
    """Test that save() logs atomic write operation at DEBUG level."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test task")]

    with patch("flywheel.storage.logger") as mock_logger:
        storage.save(todos)

        # Verify debug was called for save operation
        assert mock_logger.debug.called, "logger.debug should be called during save"
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        # Should log something about write/save operation
        assert any("save" in call.lower() or "write" in call.lower() for call in debug_calls), \
            "Debug logs should mention save/write operation"


def test_logger_exists_and_configured() -> None:
    """Test that storage module has a properly configured logger."""
    import flywheel.storage

    # Verify logger exists
    assert hasattr(flywheel.storage, "logger"), "storage module should have a logger"

    logger = flywheel.storage.logger
    # Logger name should match module
    assert logger.name == "flywheel.storage", f"Logger name should be 'flywheel.storage', got '{logger.name}'"


def test_load_logs_elapsed_time(tmp_path) -> None:
    """Test that load() logs timing information."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="task")]
    storage.save(todos)

    with patch("flywheel.storage.logger") as mock_logger:
        storage.load()

        # Debug calls should include timing info
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        # Look for timing-related keywords
        timing_keywords = ["elapsed", "time", "ms", "seconds"]
        has_timing = any(
            any(keyword in call.lower() for keyword in timing_keywords)
            for call in debug_calls
        )
        assert has_timing, "Debug logs should include timing information"
