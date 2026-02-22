"""Tests for optional logging support in TodoStorage.

This test suite verifies that TodoStorage supports optional logging
for tracking storage operations (load, save) for debugging and auditing.

Issue: #5128 - Add optional logging support
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_logger_parameter_accepted(tmp_path: Path) -> None:
    """Test that TodoStorage accepts an optional logger parameter."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_logger")

    # Should not raise
    storage = TodoStorage(str(db), logger=logger)
    assert storage.path == Path(str(db))


def test_no_logger_backward_compatible(tmp_path: Path) -> None:
    """Test that TodoStorage works without logger (backward compatibility)."""
    db = tmp_path / "todo.json"

    # Should not raise - no logger parameter
    storage = TodoStorage(str(db))

    # Operations should work normally
    todos = [Todo(id=1, text="test")]
    storage.save(todos)
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_load_logs_debug_on_success(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that load() logs DEBUG with file size and entry count on success."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("flywheel.storage")
    logger.setLevel(logging.DEBUG)

    storage = TodoStorage(str(db), logger=logger)

    # Create some todos and save
    todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]
    storage.save(todos)

    # Load and check logs
    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        loaded = storage.load()

    assert len(loaded) == 2

    # Check for debug log with entry count
    debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
    # Should have a log mentioning the load operation with entry count
    assert any("load" in msg.lower() for msg in debug_messages), f"No load message in: {debug_messages}"


def test_load_logs_debug_on_missing_file(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that load() logs DEBUG when file doesn't exist."""
    db = tmp_path / "nonexistent.json"
    logger = logging.getLogger("flywheel.storage")
    logger.setLevel(logging.DEBUG)

    storage = TodoStorage(str(db), logger=logger)

    # Load from non-existent file
    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        loaded = storage.load()

    assert loaded == []

    # Check for debug log about missing file
    debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
    # Should have a log about returning empty or file not existing
    assert any("load" in msg.lower() or "empty" in msg.lower() or "not exist" in msg.lower()
               for msg in debug_messages), f"No missing file message in: {debug_messages}"


def test_save_logs_debug_on_success(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that save() logs DEBUG with completion message on success."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("flywheel.storage")
    logger.setLevel(logging.DEBUG)

    storage = TodoStorage(str(db), logger=logger)

    todos = [Todo(id=1, text="test")]
    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        storage.save(todos)

    # Check for debug log about save completion
    debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
    assert any("save" in msg.lower() for msg in debug_messages), f"No save message in: {debug_messages}"


def test_logger_none_works_as_expected(tmp_path: Path) -> None:
    """Test that passing logger=None works same as no logger."""
    db = tmp_path / "todo.json"

    storage = TodoStorage(str(db), logger=None)

    # Operations should work normally
    todos = [Todo(id=1, text="test")]
    storage.save(todos)
    loaded = storage.load()
    assert len(loaded) == 1
