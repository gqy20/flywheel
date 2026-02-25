"""Tests for optional logging support in storage operations.

This test suite verifies that TodoStorage can optionally log debug information
about load/save operations for debugging purposes.

Issue: #5669 - Add optional logging support for debugging storage operations
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_no_logging_by_default(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that verbose=False produces no debug logs."""
    caplog.set_level(logging.DEBUG)

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), verbose=False)

    todos = [Todo(id=1, text="test task")]
    storage.save(todos)
    loaded = storage.load()

    # Verify operations work
    assert len(loaded) == 1
    assert loaded[0].text == "test task"

    # Verify no debug logs were produced by storage
    storage_logs = [r for r in caplog.records if "flywheel.storage" in r.name]
    assert len(storage_logs) == 0, f"Expected no logs, got: {storage_logs}"


def test_storage_load_logs_debug_when_verbose_true(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that verbose=True logs debug info on load operations."""
    caplog.set_level(logging.DEBUG)

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), verbose=True)

    # Create initial data
    todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2")]
    storage.save(todos)

    # Clear previous logs
    caplog.clear()

    # Load should produce debug log
    loaded = storage.load()

    # Verify data loaded correctly
    assert len(loaded) == 2

    # Verify debug log was produced
    storage_logs = [r for r in caplog.records if "flywheel.storage" in r.name]
    assert len(storage_logs) >= 1, f"Expected at least 1 log, got: {storage_logs}"

    # Verify log contains expected information
    load_log = storage_logs[0]
    assert load_log.levelno == logging.DEBUG
    assert str(db) in load_log.message or "load" in load_log.message.lower()
    # Should mention item count
    assert "2" in load_log.message


def test_storage_save_logs_debug_when_verbose_true(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that verbose=True logs debug info on save operations."""
    caplog.set_level(logging.DEBUG)

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), verbose=True)

    todos = [Todo(id=1, text="test task")]
    storage.save(todos)

    # Verify debug log was produced
    storage_logs = [r for r in caplog.records if "flywheel.storage" in r.name]
    assert len(storage_logs) >= 1, f"Expected at least 1 log, got: {storage_logs}"

    # Verify log contains expected information
    save_log = storage_logs[0]
    assert save_log.levelno == logging.DEBUG
    assert str(db) in save_log.message or "save" in save_log.message.lower()


def test_storage_load_empty_file_logs_when_verbose(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that verbose=True logs debug info when loading non-existent file."""
    caplog.set_level(logging.DEBUG)

    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db), verbose=True)

    loaded = storage.load()

    # Should return empty list for non-existent file
    assert loaded == []

    # Should still log the load attempt
    storage_logs = [r for r in caplog.records if "flywheel.storage" in r.name]
    assert len(storage_logs) >= 1, f"Expected at least 1 log, got: {storage_logs}"


def test_storage_with_custom_logger(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that TodoStorage can use a custom logger when provided."""
    caplog.set_level(logging.DEBUG)

    # Create a custom logger
    custom_logger = logging.getLogger("custom.storage.logger")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), logger=custom_logger)

    todos = [Todo(id=1, text="test")]
    storage.save(todos)
    storage.load()

    # Should have logs from the custom logger
    custom_logs = [r for r in caplog.records if "custom.storage.logger" in r.name]
    assert len(custom_logs) >= 2, f"Expected at least 2 logs from custom logger, got: {custom_logs}"
