"""Regression tests for issue #2816: Add logging module for debugging file operations.

Issue: Storage operations lack logging, making debugging file permissions,
directory creation, atomic writes, etc. difficult.

This test FAILS before the fix (logger doesn't exist) and PASSES after the fix.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_has_logger_module(tmp_path) -> None:
    """Issue #2816: storage.py should import logging and have a logger."""
    # Import the storage module to check if logging is imported
    import flywheel.storage as storage_module

    # Check that logging has been imported
    assert hasattr(storage_module, 'logging'), (
        "storage.py should import logging module"
    )

    # Check that there's a module-level logger
    assert hasattr(storage_module, 'logger'), (
        "storage.py should define a module-level logger"
    )


def test_load_logs_debug_message_with_file_size(tmp_path) -> None:
    """Issue #2816: load() should log debug messages including file size."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a test file with content
    todos = [Todo(id=1, text="test todo for logging")]
    storage.save(todos)

    # Set up a mock handler to capture log messages
    import flywheel.storage as storage_module
    logger = storage_module.logger

    # Create a mock to track debug calls
    with patch.object(logger, 'debug') as mock_debug:
        # Load the file
        storage.load()

        # Verify debug was called
        assert mock_debug.called, (
            "load() should log debug messages"
        )

        # Verify the log message contains file size information
        log_messages = [str(call.args[0]) for call in mock_debug.call_args_list]
        assert any('size' in msg.lower() or 'byte' in msg.lower() for msg in log_messages), (
            f"load() should log file size. Got messages: {log_messages}"
        )


def test_save_logs_debug_message_for_atomic_write(tmp_path) -> None:
    """Issue #2816: save() should log debug messages for atomic write steps."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo for logging")]

    # Set up a mock to track log messages
    import flywheel.storage as storage_module
    logger = storage_module.logger

    with patch.object(logger, 'debug') as mock_debug:
        # Save todos
        storage.save(todos)

        # Verify debug was called for atomic write steps
        assert mock_debug.called, (
            "save() should log debug messages for atomic write steps"
        )

        # Verify the log message mentions atomic write or temp file
        log_messages = [str(call.args[0]) for call in mock_debug.call_args_list]
        assert any(
            'atomic' in msg.lower() or 'temp' in msg.lower() or 'write' in msg.lower()
            for msg in log_messages
        ), (
            f"save() should log atomic write steps. Got messages: {log_messages}"
        )


def test_ensure_parent_directory_logs_debug_message(tmp_path) -> None:
    """Issue #2816: _ensure_parent_directory() should log directory creation."""
    db = tmp_path / "subdir" / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Set up a mock to track log messages
    import flywheel.storage as storage_module
    logger = storage_module.logger

    with patch.object(logger, 'debug') as mock_debug:
        # Save (which triggers _ensure_parent_directory)
        storage.save(todos)

        # Verify debug was called for directory creation
        assert mock_debug.called, (
            "_ensure_parent_directory() should log debug messages"
        )

        # Verify the log message mentions directory creation
        log_messages = [str(call.args[0]) for call in mock_debug.call_args_list]
        assert any(
            'dir' in msg.lower() or 'create' in msg.lower() or 'mkdir' in msg.lower()
            for msg in log_messages
        ), (
            f"_ensure_parent_directory() should log directory creation. Got messages: {log_messages}"
        )


def test_logging_does_not_affect_existing_functionality(tmp_path) -> None:
    """Issue #2816: Adding logging should not break existing functionality."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Test basic save/load still works
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second", done=True),
    ]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first"
    assert loaded[1].text == "second"
    assert loaded[1].done is True


def test_logger_is_module_level_logger(tmp_path) -> None:
    """Issue #2816: storage.py should use logging.getLogger(__name__)."""
    import flywheel.storage as storage_module

    logger = storage_module.logger

    # Verify it's a proper logger instance
    assert isinstance(logger, logging.Logger), (
        "logger should be a logging.Logger instance"
    )

    # Verify it has the correct module name
    assert logger.name == 'flywheel.storage', (
        f"logger should have name 'flywheel.storage', got '{logger.name}'"
    )
