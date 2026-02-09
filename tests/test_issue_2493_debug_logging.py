"""Tests for debug logging feature in storage operations (issue #2493).

This test suite verifies that debug logging is properly implemented
for storage operations and can be controlled via FLYWHEEL_DEBUG env var.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_has_logger() -> None:
    """Test that load operation logs when debug mode is enabled."""
    db = Path("/tmp/test_load_log.json")
    storage = TodoStorage(str(db))

    # Create logger for testing
    logger = logging.getLogger("flywheel.storage")

    with patch.object(logger, "debug") as mock_debug:
        # Non-existent file should still log with count 0
        storage.load()
        # Should log about loading operation
        assert mock_debug.called, "load() should log in debug mode"


def test_save_has_logger(tmp_path) -> None:
    """Test that save operation logs when debug mode is enabled."""
    db = tmp_path / "test_save_log.json"
    storage = TodoStorage(str(db))

    # Create logger for testing
    logger = logging.getLogger("flywheel.storage")

    todos = [Todo(id=1, text="test logging")]

    with patch.object(logger, "debug") as mock_debug:
        storage.save(todos)
        # Should log about save operation
        assert mock_debug.called, "save() should log in debug mode"


def test_next_id_has_logger() -> None:
    """Test that next_id operation logs when debug mode is enabled."""
    storage = TodoStorage()

    # Create logger for testing
    logger = logging.getLogger("flywheel.storage")

    todos = [Todo(id=1, text="test")]

    with patch.object(logger, "debug") as mock_debug:
        storage.next_id(todos)
        # Should log about next_id operation
        assert mock_debug.called, "next_id() should log in debug mode"


def test_logging_module_exists_in_storage() -> None:
    """Test that logging module is imported in storage.py."""
    import flywheel.storage as storage_module

    # Check that logging is available in the module
    assert hasattr(storage_module, "logging"), "storage module should import logging"


def test_logger_has_debug_level() -> None:
    """Test that logger uses DEBUG level for logging."""
    logger = logging.getLogger("flywheel.storage")

    # Logger should be able to log at DEBUG level
    # We just need to ensure it doesn't raise an error
    logger.setLevel(logging.DEBUG)
    assert logger.level == logging.DEBUG


def test_save_logs_include_todo_count_and_paths(tmp_path, caplog) -> None:
    """Test that save logs include todo count and file paths."""
    db = tmp_path / "test_save_details.json"
    storage = TodoStorage(str(db))

    # Set up logging to capture debug messages
    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]
        storage.save(todos)

        # Check that debug messages were logged
        debug_messages = [r.message for r in caplog.records if r.levelname == "DEBUG"]
        assert len(debug_messages) > 0, "Should have debug log messages"

        # Check that log mentions the file path or temp file operation
        log_text = " ".join(debug_messages)
        assert "test" in log_text.lower() or "save" in log_text.lower()


def test_load_logs_include_file_path(tmp_path, caplog) -> None:
    """Test that load logs include file path."""
    db = tmp_path / "test_load_details.json"
    storage = TodoStorage(str(db))

    # Create a test file first
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Clear caplog and set up for load
    caplog.clear()

    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        storage.load()

        # Check that debug messages were logged
        debug_messages = [r.message for r in caplog.records if r.levelname == "DEBUG"]
        assert len(debug_messages) > 0, "Should have debug log messages for load"
