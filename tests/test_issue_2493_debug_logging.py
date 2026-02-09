"""Tests for debug logging feature in storage operations.

Issue #2493: Add debug logging for storage operations to help diagnose
file I/O issues, concurrent access problems, and performance bottlenecks.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_logs_debug_info_when_enabled(tmp_path, caplog) -> None:
    """Test that load() logs file path and todo count when debug logging is enabled."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]
    storage.save(todos)

    # Enable debug logging for the storage module
    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        loaded = storage.load()

    # Verify logs contain file path and todo count
    assert len(loaded) == 2
    debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
    assert any(str(db) in msg and "2" in msg for msg in debug_messages), \
        f"Expected debug log with file path and count. Got: {debug_messages}"


def test_load_logs_nothing_when_debug_disabled(tmp_path, caplog) -> None:
    """Test that load() produces no output when debug logging is disabled."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Load with logging disabled (default WARNING level)
    loaded = storage.load()

    # Verify no debug logs
    assert len(loaded) == 1
    debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
    assert len(debug_messages) == 0, \
        f"Expected no debug logs. Got: {debug_messages}"


def test_save_logs_debug_info_when_enabled(tmp_path, caplog) -> None:
    """Test that save() logs file path, temp file path, and todo count when debug is enabled."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="save test"), Todo(id=2, text="another")]

    # Enable debug logging for the storage module
    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        storage.save(todos)

    # Verify logs contain file path and todo count
    debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
    assert any(str(db) in msg and "2" in msg for msg in debug_messages), \
        f"Expected debug log with file path and count. Got: {debug_messages}"


def test_save_logs_nothing_when_debug_disabled(tmp_path, caplog) -> None:
    """Test that save() produces no output when debug logging is disabled."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Save with logging disabled (default WARNING level)
    storage.save(todos)

    # Verify no debug logs
    debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
    assert len(debug_messages) == 0, \
        f"Expected no debug logs. Got: {debug_messages}"


def test_next_id_logs_debug_info_when_enabled(tmp_path, caplog) -> None:
    """Test that next_id() logs the computed ID when debug logging is enabled."""
    storage = TodoStorage(str(tmp_path / "todo.json"))

    todos = [Todo(id=1, text="first"), Todo(id=5, text="second")]

    # Enable debug logging for the storage module
    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        next_id = storage.next_id(todos)

    # Verify the ID is computed correctly
    assert next_id == 6

    # Verify logs contain the computed ID
    debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
    assert any("6" in msg for msg in debug_messages), \
        f"Expected debug log with computed ID. Got: {debug_messages}"


def test_cli_respects_flywheel_debug_env_var(tmp_path, monkeypatch, caplog) -> None:
    """Test that CLI enables debug logging when FLYWHEEL_DEBUG=1 is set."""
    from flywheel.cli import build_parser, run_command

    db = str(tmp_path / "debug.json")

    # Set FLYWHEEL_DEBUG environment variable
    monkeypatch.setenv("FLYWHEEL_DEBUG", "1")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "add", "debug test"])

    with caplog.at_level(logging.DEBUG):
        run_command(args)

    # Verify debug logs were produced
    debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
    assert len(debug_messages) > 0, \
        f"Expected debug logs when FLYWHEEL_DEBUG=1. Got: {debug_messages}"


def test_cli_respects_debug_flag(tmp_path, caplog) -> None:
    """Test that CLI enables debug logging when --debug flag is used."""
    from flywheel.cli import build_parser, run_command

    db = str(tmp_path / "debug_flag.json")

    # The --debug flag should enable debug logging
    # We need to configure logging to capture DEBUG level
    with caplog.at_level(logging.DEBUG), \
         patch("sys.argv", ["todo", "--debug", "--db", db, "add", "debug flag test"]):
        parser = build_parser()
        args = parser.parse_args(["--debug", "--db", db, "add", "debug flag test"])
        run_command(args)

    # Verify debug logs were produced
    debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
    assert len(debug_messages) > 0, \
        f"Expected debug logs with --debug flag. Got: {debug_messages}"
