"""Tests for issue #2266: Optional debug logging for storage operations.

This test suite verifies that TodoStorage provides optional debug logging
controlled via the FW_LOG environment variable.
"""

from __future__ import annotations

import logging

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_no_logging_by_default(tmp_path, caplog) -> None:
    """Verify no log output when FW_LOG not set."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Ensure FW_LOG is not set
    import os
    env_backup = os.environ.get("FW_LOG")
    if "FW_LOG" in os.environ:
        del os.environ["FW_LOG"]

    try:
        with caplog.at_level(logging.DEBUG):
            # Save and load operations should not produce logs
            todos = [Todo(id=1, text="test todo")]
            storage.save(todos)
            loaded = storage.load()

        # Should have no log records from flywheel.storage
        storage_logs = [
            r for r in caplog.records if r.name == "flywheel.storage"
        ]
        assert len(storage_logs) == 0, "Should not log when FW_LOG not set"
        assert len(loaded) == 1
    finally:
        # Restore environment
        if env_backup is not None:
            os.environ["FW_LOG"] = env_backup


def test_logging_enabled_with_fw_log_debug(tmp_path, monkeypatch, caplog) -> None:
    """Verify debug logs when FW_LOG=debug."""
    monkeypatch.setenv("FW_LOG", "debug")

    # Force re-import to pick up environment variable
    import importlib

    import flywheel.storage
    importlib.reload(flywheel.storage)

    db = tmp_path / "todo.json"
    storage = flywheel.storage.TodoStorage(str(db))

    with caplog.at_level(logging.DEBUG):
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)
        storage.load()

    # Should have log records from flywheel.storage
    storage_logs = [
        r for r in caplog.records if r.name == "flywheel.storage"
    ]
    assert len(storage_logs) >= 2, "Should log when FW_LOG=debug"


def test_log_contains_file_path(tmp_path, monkeypatch, caplog) -> None:
    """Verify logs include file path."""
    monkeypatch.setenv("FW_LOG", "debug")

    # Force re-import to pick up environment variable
    import importlib

    import flywheel.storage
    importlib.reload(flywheel.storage)

    db = tmp_path / "todo.json"
    storage = flywheel.storage.TodoStorage(str(db))

    with caplog.at_level(logging.DEBUG):
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

    # Check for file path in log messages
    storage_logs = [
        r for r in caplog.records if r.name == "flywheel.storage"
    ]
    assert any(str(db) in r.message for r in storage_logs), \
        "Logs should include file path"


def test_log_contains_item_count(tmp_path, monkeypatch, caplog) -> None:
    """Verify logs include number of todos."""
    monkeypatch.setenv("FW_LOG", "debug")

    # Force re-import to pick up environment variable
    import importlib

    import flywheel.storage
    importlib.reload(flywheel.storage)

    db = tmp_path / "todo.json"
    storage = flywheel.storage.TodoStorage(str(db))

    with caplog.at_level(logging.DEBUG):
        todos = [
            Todo(id=1, text="first"),
            Todo(id=2, text="second"),
            Todo(id=3, text="third"),
        ]
        storage.save(todos)
        storage.load()

    # Check for count in log messages
    storage_logs = [
        r for r in caplog.records if r.name == "flywheel.storage"
    ]
    # Should see "3" in at least one log message (the count)
    assert any("3" in r.message for r in storage_logs), \
        "Logs should include item count"


def test_load_logging_on_nonexistent_file(tmp_path, monkeypatch, caplog) -> None:
    """Verify logging for load on missing file."""
    monkeypatch.setenv("FW_LOG", "debug")

    # Force re-import to pick up environment variable
    import importlib

    import flywheel.storage
    importlib.reload(flywheel.storage)

    db = tmp_path / "nonexistent.json"
    storage = flywheel.storage.TodoStorage(str(db))

    with caplog.at_level(logging.DEBUG):
        loaded = storage.load()

    # Should still log the load attempt
    storage_logs = [
        r for r in caplog.records if r.name == "flywheel.storage"
    ]
    # At minimum, should have a log for loading from nonexistent file
    assert len(storage_logs) >= 1, "Should log load operation"
    assert len(loaded) == 0, "Nonexistent file should return empty list"


def test_save_and_load_timing(tmp_path, monkeypatch, caplog) -> None:
    """Verify logs include timing information."""
    monkeypatch.setenv("FW_LOG", "debug")

    # Force re-import to pick up environment variable
    import importlib

    import flywheel.storage
    importlib.reload(flywheel.storage)

    db = tmp_path / "todo.json"
    storage = flywheel.storage.TodoStorage(str(db))

    with caplog.at_level(logging.DEBUG):
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)
        storage.load()

    # Check for timing information in save logs
    storage_logs = [
        r for r in caplog.records if r.name == "flywheel.storage"
    ]
    # Look for timing-related keywords (ms, seconds, took, etc.)
    timing_keywords = ["ms", "seconds", "took", "elapsed"]
    has_timing = any(
        any(keyword in r.message.lower() for keyword in timing_keywords)
        for r in storage_logs
    )
    assert has_timing, "Logs should include timing information for save operation"
