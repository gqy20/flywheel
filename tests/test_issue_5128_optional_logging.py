"""Tests for optional logging support in TodoStorage.

This test suite verifies that TodoStorage supports optional logging for
debugging and auditing storage operations (load, save, errors).

Issue: #5128
"""

from __future__ import annotations

import logging
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_accepts_optional_logger_parameter(tmp_path: Path) -> None:
    """Test that TodoStorage.__init__ accepts an optional logger parameter."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_logger")

    # Should not raise - logger parameter is optional
    storage = TodoStorage(str(db), logger=logger)
    assert storage.logger is logger


def test_storage_works_without_logger_backward_compatible(tmp_path: Path) -> None:
    """Test that TodoStorage works without a logger (backward compatibility)."""
    db = tmp_path / "todo.json"

    # Should not raise - logger parameter is optional
    storage = TodoStorage(str(db))
    assert storage.logger is None

    # Basic operations should work without logger
    todos = [Todo(id=1, text="test")]
    storage.save(todos)
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_load_logs_debug_on_success_with_logger(caplog, tmp_path: Path) -> None:
    """Test that load() logs DEBUG message on success when logger is provided."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_load_logger")
    logger.setLevel(logging.DEBUG)

    storage = TodoStorage(str(db), logger=logger)

    # Create some test data
    todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2")]
    storage.save(todos)

    # Load should log DEBUG message
    with caplog.at_level(logging.DEBUG, logger="test_load_logger"):
        loaded = storage.load()

    assert len(loaded) == 2

    # Verify DEBUG log was recorded
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug_records) >= 1

    # Log should contain relevant info: file path, entries count
    log_messages = [r.message for r in debug_records]
    combined_message = " ".join(log_messages)
    assert "load" in combined_message.lower() or "loaded" in combined_message.lower()
    assert str(db) in combined_message or db.name in combined_message
    assert "2" in combined_message  # number of entries


def test_save_logs_debug_on_success_with_logger(caplog, tmp_path: Path) -> None:
    """Test that save() logs DEBUG message on success when logger is provided."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_save_logger")
    logger.setLevel(logging.DEBUG)

    storage = TodoStorage(str(db), logger=logger)

    todos = [Todo(id=1, text="task to save")]

    # Save should log DEBUG message
    with caplog.at_level(logging.DEBUG, logger="test_save_logger"):
        storage.save(todos)

    # Verify DEBUG log was recorded
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug_records) >= 1

    # Log should contain relevant info: file path, operation
    log_messages = [r.message for r in debug_records]
    combined_message = " ".join(log_messages)
    assert "save" in combined_message.lower() or "saved" in combined_message.lower()
    assert str(db) in combined_message or db.name in combined_message


def test_no_logs_without_logger(tmp_path: Path, caplog) -> None:
    """Test that no logs are emitted when no logger is provided."""
    db = tmp_path / "todo.json"

    # Create storage without logger
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Perform operations
    with caplog.at_level(logging.DEBUG):
        storage.save(todos)
        storage.load()

    # No logs should be captured
    assert len(caplog.records) == 0
