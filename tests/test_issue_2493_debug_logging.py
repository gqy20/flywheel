"""Tests for issue #2493: Debug logging for storage operations.

This test suite verifies that debug logging is available for storage operations
when FLYWHEEL_DEBUG environment variable is set.
"""

from __future__ import annotations

import logging
import os

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_logs_debug_info_when_env_set(tmp_path, caplog) -> None:
    """Test that load() logs debug info when FLYWHEEL_DEBUG=1."""
    # Create a test database file
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Set debug environment variable
    old_env = os.environ.get("FLYWHEEL_DEBUG")
    os.environ["FLYWHEEL_DEBUG"] = "1"

    try:
        with caplog.at_level(logging.DEBUG):
            storage.load()

        # Should log load operation with file path and todo count
        assert len(caplog.records) > 0
        debug_messages = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("load" in str(r.message).lower() for r in debug_messages)
        assert any(str(db) in str(r.message) for r in debug_messages)
        assert any("1" in str(r.message) or "todo" in str(r.message).lower() for r in debug_messages)
    finally:
        if old_env is None:
            os.environ.pop("FLYWHEEL_DEBUG", None)
        else:
            os.environ["FLYWHEEL_DEBUG"] = old_env


def test_load_no_logging_when_env_not_set(tmp_path, caplog) -> None:
    """Test that load() does not log when FLYWHEEL_DEBUG is not set."""
    # Create a test database file
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Ensure debug environment variable is not set
    old_env = os.environ.pop("FLYWHEEL_DEBUG", None)

    try:
        with caplog.at_level(logging.DEBUG):
            storage.load()

        # Should not log any debug messages from flywheel.storage
        storage_logs = [r for r in caplog.records if r.name.startswith("flywheel.storage")]
        assert len(storage_logs) == 0
    finally:
        if old_env is not None:
            os.environ["FLYWHEEL_DEBUG"] = old_env


def test_save_logs_debug_info_when_env_set(tmp_path, caplog) -> None:
    """Test that save() logs debug info when FLYWHEEL_DEBUG=1."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Set debug environment variable
    old_env = os.environ.get("FLYWHEEL_DEBUG")
    os.environ["FLYWHEEL_DEBUG"] = "1"

    try:
        todos = [Todo(id=1, text="test todo")]

        with caplog.at_level(logging.DEBUG):
            storage.save(todos)

        # Should log save operation with file path, temp file path, and todo count
        assert len(caplog.records) > 0
        debug_messages = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("save" in str(r.message).lower() for r in debug_messages)
        assert any(str(db) in str(r.message) for r in debug_messages)
        assert any(".tmp" in str(r.message) or "temp" in str(r.message).lower() for r in debug_messages)
        assert any("1" in str(r.message) or "todo" in str(r.message).lower() for r in debug_messages)
    finally:
        if old_env is None:
            os.environ.pop("FLYWHEEL_DEBUG", None)
        else:
            os.environ["FLYWHEEL_DEBUG"] = old_env


def test_save_no_logging_when_env_not_set(tmp_path, caplog) -> None:
    """Test that save() does not log when FLYWHEEL_DEBUG is not set."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Ensure debug environment variable is not set
    old_env = os.environ.pop("FLYWHEEL_DEBUG", None)

    try:
        todos = [Todo(id=1, text="test todo")]

        with caplog.at_level(logging.DEBUG):
            storage.save(todos)

        # Should not log any debug messages from flywheel.storage
        storage_logs = [r for r in caplog.records if r.name.startswith("flywheel.storage")]
        assert len(storage_logs) == 0
    finally:
        if old_env is not None:
            os.environ["FLYWHEEL_DEBUG"] = old_env


def test_next_id_logs_debug_info_when_env_set(tmp_path, caplog) -> None:
    """Test that next_id() logs debug info when FLYWHEEL_DEBUG=1."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Set debug environment variable
    old_env = os.environ.get("FLYWHEEL_DEBUG")
    os.environ["FLYWHEEL_DEBUG"] = "1"

    try:
        todos = [Todo(id=1, text="test todo")]

        with caplog.at_level(logging.DEBUG):
            storage.next_id(todos)

        # Should log next_id operation
        assert len(caplog.records) > 0
        debug_messages = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("next" in str(r.message).lower() or "id" in str(r.message).lower() for r in debug_messages)
    finally:
        if old_env is None:
            os.environ.pop("FLYWHEEL_DEBUG", None)
        else:
            os.environ["FLYWHEEL_DEBUG"] = old_env


def test_logging_does_not_break_existing_functionality(tmp_path) -> None:
    """Test that logging does not break existing storage functionality."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Test basic operations still work
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"

    # Test next_id
    next_id = storage.next_id(loaded)
    assert next_id == 2


def test_empty_file_load_logs_when_env_set(tmp_path, caplog) -> None:
    """Test that load() logs when file doesn't exist and FLYWHEEL_DEBUG=1."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Set debug environment variable
    old_env = os.environ.get("FLYWHEEL_DEBUG")
    os.environ["FLYWHEEL_DEBUG"] = "1"

    try:
        with caplog.at_level(logging.DEBUG):
            loaded = storage.load()

        # Should return empty list and log
        assert loaded == []
        assert len(caplog.records) > 0
    finally:
        if old_env is None:
            os.environ.pop("FLYWHEEL_DEBUG", None)
        else:
            os.environ["FLYWHEEL_DEBUG"] = old_env
