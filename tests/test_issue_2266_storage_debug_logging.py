"""Tests for issue #2266: Optional debug logging for storage operations.

This test suite verifies that TodoStorage provides optional debug logging
controlled by the FW_LOG environment variable.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_default_no_logging_output(tmp_path, caplog) -> None:
    """Test that no logging output is produced when FW_LOG is not set.

    This verifies the default behavior - logging should not produce output
    unless explicitly enabled via FW_LOG environment variable.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Clear any existing log configuration
    caplog.clear()

    # Perform storage operations
    todos = [Todo(id=1, text="test todo"), Todo(id=2, text="another todo")]
    storage.save(todos)
    storage.load()

    # Verify no log records were captured
    # With caplog at INFO level, we should see nothing from storage module
    assert len(caplog.records) == 0, "Should not produce logs by default"


def test_fw_log_debug_enables_logging(tmp_path, caplog) -> None:
    """Test that FW_LOG=debug enables debug logging for storage operations.

    When FW_LOG environment variable is set to "debug", the storage module
    should emit debug level log messages.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Set environment variable to enable debug logging
    with patch.dict(os.environ, {"FW_LOG": "debug"}):
        # Clear any existing log configuration
        caplog.clear()

        # Set log level to DEBUG to capture debug messages
        with caplog.at_level(logging.DEBUG):
            # Perform storage operations
            todos = [Todo(id=1, text="debug test"), Todo(id=2, text="more todos")]
            storage.save(todos)

            # Should have captured log records from flywheel.storage
            storage_records = [r for r in caplog.records if r.name.startswith("flywheel.storage")]
            assert len(storage_records) > 0, "Should produce logs when FW_LOG=debug"


def test_load_logs_path_and_count(tmp_path, caplog) -> None:
    """Test that load() logs file path and todo count when debug enabled.

    Verifies that the load operation logs:
    - The file path being loaded
    - The number of todos loaded
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First, create some todos to load
    initial_todos = [Todo(id=1, text="first"), Todo(id=2, text="second"), Todo(id=3, text="third")]
    storage.save(initial_todos)

    # Now test load logging
    with patch.dict(os.environ, {"FW_LOG": "debug"}):
        caplog.clear()

        with caplog.at_level(logging.DEBUG):
            loaded = storage.load()

            # Find storage-related log records
            storage_records = [r for r in caplog.records if r.name.startswith("flywheel.storage")]

            # Should have at least one log from load operation
            load_logs = [r for r in storage_records if "load" in r.message.lower()]
            assert len(load_logs) > 0, "Load should produce log messages"

            # Verify log contains file path information
            has_path_info = any(str(db) in r.message for r in storage_records)
            assert has_path_info, "Log should contain file path"

            # Verify log contains count information (we loaded 3 todos)
            has_count_info = any("3" in r.message for r in storage_records)
            assert has_count_info, "Log should contain todo count"


def test_save_logs_path_and_count(tmp_path, caplog) -> None:
    """Test that save() logs file path and todo count when debug enabled.

    Verifies that the save operation logs:
    - The file path being saved to
    - The number of todos being saved
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos_to_save = [
        Todo(id=1, text="save test 1"),
        Todo(id=2, text="save test 2"),
        Todo(id=3, text="save test 3"),
        Todo(id=4, text="save test 4"),
        Todo(id=5, text="save test 5"),
    ]

    with patch.dict(os.environ, {"FW_LOG": "debug"}):
        caplog.clear()

        with caplog.at_level(logging.DEBUG):
            storage.save(todos_to_save)

            # Find storage-related log records
            storage_records = [r for r in caplog.records if r.name.startswith("flywheel.storage")]

            # Should have at least one log from save operation
            save_logs = [r for r in storage_records if "save" in r.message.lower()]
            assert len(save_logs) > 0, "Save should produce log messages"

            # Verify log contains file path information
            has_path_info = any(str(db) in r.message for r in storage_records)
            assert has_path_info, "Log should contain file path"

            # Verify log contains count information (we saved 5 todos)
            has_count_info = any("5" in r.message for r in storage_records)
            assert has_count_info, "Log should contain todo count"
