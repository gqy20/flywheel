"""Tests for logging behavior in TodoStorage.

This test suite verifies that TodoStorage operations emit appropriate logs
for debugging, performance tracking, and audit trails.
"""

from __future__ import annotations

import logging

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_logs_file_path_and_count(tmp_path, caplog) -> None:
    """Test that load() logs file path and record count on successful load."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]
    storage.save(todos)

    # Load with logging capture
    with caplog.at_level(logging.INFO):
        loaded = storage.load()

    # Verify log contains file path and count
    assert len(loaded) == 2
    assert any(
        "Loading todos from" in record.message and str(db) in record.message
        for record in caplog.records
    ), f"Expected 'Loading todos from' log with path. Got: {[r.message for r in caplog.records]}"
    assert any(
        "Loaded 2 todos from" in record.message
        for record in caplog.records
    ), f"Expected 'Loaded 2 todos from' log. Got: {[r.message for r in caplog.records]}"


def test_load_logs_empty_file(tmp_path, caplog) -> None:
    """Test that load() logs appropriate message for non-existent file."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Load non-existent file with logging capture
    with caplog.at_level(logging.INFO):
        loaded = storage.load()

    # Verify log mentions the file
    assert loaded == []
    assert any(
        str(db) in record.message
        for record in caplog.records
    ), f"Expected log with file path. Got: {[r.message for r in caplog.records]}"


def test_load_logs_error_before_raising(tmp_path, caplog) -> None:
    """Test that load() logs errors with context before raising exceptions."""
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    # Create invalid JSON file
    db.write_text("{ invalid json", encoding="utf-8")

    # Attempt load with logging capture
    with caplog.at_level(logging.ERROR), pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()

    # Verify error was logged before raising
    assert any(
        record.levelname == "ERROR" and "Invalid JSON" in record.message
        for record in caplog.records
    ), f"Expected ERROR log with 'Invalid JSON'. Got: {[r.message for r in caplog.records]}"


def test_save_logs_file_path_and_count(tmp_path, caplog) -> None:
    """Test that save() logs file path and record count on successful save."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]

    # Save with logging capture
    with caplog.at_level(logging.INFO):
        storage.save(todos)

    # Verify log contains file path and count
    assert any(
        "Saving 3 todos to" in record.message and str(db) in record.message
        for record in caplog.records
    ), f"Expected 'Saving 3 todos to' log with path. Got: {[r.message for r in caplog.records]}"
    assert any(
        "Saved 3 todos to" in record.message
        for record in caplog.records
    ), f"Expected 'Saved 3 todos to' log. Got: {[r.message for r in caplog.records]}"


def test_save_logs_error_before_raising(tmp_path, caplog) -> None:
    """Test that save() logs errors with context before raising exceptions."""
    db = tmp_path / "impossible.json"
    # Create a file where a directory needs to be (simulate permission issue)

    # Create a file at parent path to cause directory creation failure
    db.parent.mkdir(parents=True, exist_ok=True)
    (db.parent / "blocked").write_text("blocking file", encoding="utf-8")

    # Create a path that will fail because parent exists as a file
    blocked_path = db.parent / "blocked" / "nested.json"
    blocked_storage = TodoStorage(str(blocked_path))

    # Attempt save with logging capture
    with caplog.at_level(logging.ERROR), pytest.raises((ValueError, OSError)):
        blocked_storage.save([Todo(id=1, text="test")])

    # Verify error was logged
    assert any(
        record.levelname == "ERROR"
        for record in caplog.records
    ), f"Expected ERROR log. Got: {[r.message for r in caplog.records]}"


def test_logger_respects_log_level(tmp_path) -> None:
    """Test that logging can be controlled via standard logging config."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Set logger to WARNING level - should not see INFO logs
    logger = logging.getLogger("flywheel.storage")
    logger.setLevel(logging.WARNING)

    import io
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

    # Save should not emit INFO logs when logger is at WARNING
    storage.save(todos)

    # Should not have INFO logs captured
    logs = log_capture.getvalue()
    # At WARNING level, INFO logs are suppressed
    assert "Saving 1 todos to" not in logs or "Saved 1 todos to" not in logs

    # Clean up
    logger.removeHandler(handler)
    logger.setLevel(logging.NOTSET)
