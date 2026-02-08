"""Tests for issue #2100: Add logging capability for storage operations.

This test suite verifies that TodoStorage provides logging for debugging
and auditing purposes, controlled by TODO_LOG_LEVEL environment variable.
"""

from __future__ import annotations

import logging

import pytest

from flywheel.storage import TodoStorage, get_logger
from flywheel.todo import Todo


def test_get_logger_returns_configured_logger() -> None:
    """Verify get_logger() returns a properly configured logger instance."""
    logger = get_logger()
    assert isinstance(logger, logging.Logger)
    assert logger.name == "flywheel.storage"


def test_get_logger_respects_todo_log_level_env_var(monkeypatch, tmp_path) -> None:
    """Verify logger level can be controlled via TODO_LOG_LEVEL environment variable."""
    # Test DEBUG level
    monkeypatch.setenv("TODO_LOG_LEVEL", "DEBUG")
    logger_debug = get_logger()
    assert logger_debug.level == logging.DEBUG

    # Test ERROR level
    monkeypatch.setenv("TODO_LOG_LEVEL", "ERROR")
    logger_error = get_logger()
    assert logger_error.level == logging.ERROR


def test_get_logger_defaults_to_warning_when_env_not_set(monkeypatch) -> None:
    """Verify logger defaults to WARNING level when TODO_LOG_LEVEL is not set."""
    monkeypatch.delenv("TODO_LOG_LEVEL", raising=False)
    logger = get_logger()
    assert logger.level == logging.WARNING


def test_load_logs_debug_on_success(tmp_path, monkeypatch, caplog) -> None:
    """Verify load() logs DEBUG level on success with file path and count."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]
    storage.save(todos)

    # Enable DEBUG logging and capture logs
    monkeypatch.setenv("TODO_LOG_LEVEL", "DEBUG")
    logger = get_logger()
    logger.setLevel(logging.DEBUG)

    with caplog.at_level(logging.DEBUG):
        loaded = storage.load()

    # Verify log contains file path and count
    assert len(loaded) == 2
    assert any(
        "Loaded" in record.message and str(db) in record.message and "2" in record.message
        for record in caplog.records
    ), f"Expected debug log with file path and count. Got: {[r.message for r in caplog.records]}"


def test_load_logs_error_on_json_decode_error(tmp_path, monkeypatch, caplog) -> None:
    """Verify load() logs ERROR level when JSON is invalid."""
    db = tmp_path / "corrupt.json"
    storage = TodoStorage(str(db))

    # Create invalid JSON file
    db.write_text("{invalid json", encoding="utf-8")

    # Enable ERROR logging and capture logs
    monkeypatch.setenv("TODO_LOG_LEVEL", "ERROR")
    logger = get_logger()
    logger.setLevel(logging.ERROR)

    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(ValueError, match="Invalid JSON"),
    ):
        storage.load()

    # Verify error log contains exception details
    assert any(
        "ERROR" in record.levelname and
        ("Invalid JSON" in record.message or "load" in record.message.lower())
        for record in caplog.records
    ), f"Expected error log for invalid JSON. Got: {[r.message for r in caplog.records]}"


def test_save_logs_debug_on_success(tmp_path, monkeypatch, caplog) -> None:
    """Verify save() logs DEBUG level on success with file path and count."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2"), Todo(id=3, text="task3")]

    # Enable DEBUG logging and capture logs
    monkeypatch.setenv("TODO_LOG_LEVEL", "DEBUG")
    logger = get_logger()
    logger.setLevel(logging.DEBUG)

    with caplog.at_level(logging.DEBUG):
        storage.save(todos)

    # Verify log contains file path and count
    assert any(
        "Saved" in record.message and str(db) in record.message and "3" in record.message
        for record in caplog.records
    ), f"Expected debug log with file path and count. Got: {[r.message for r in caplog.records]}"


def test_save_logs_error_on_permission_denied(tmp_path, monkeypatch, caplog) -> None:
    """Verify save() logs ERROR level when an OSError occurs."""
    from unittest.mock import patch

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="task1")]

    # Enable ERROR logging and capture logs
    monkeypatch.setenv("TODO_LOG_LEVEL", "ERROR")
    logger = get_logger()
    logger.setLevel(logging.ERROR)

    # Mock os.replace to simulate permission denied error
    def failing_replace(*args, **kwargs):
        raise OSError("[Errno 13] Permission denied")

    with (
        caplog.at_level(logging.ERROR),
        patch("flywheel.storage.os.replace", failing_replace),
        pytest.raises(OSError, match="Permission denied"),
    ):
        storage.save(todos)

    # Verify error log was created
    assert any(
        record.levelname == "ERROR" and
        ("save" in record.message.lower() or "permission" in record.message.lower() or "failed" in record.message.lower())
        for record in caplog.records
    ), f"Expected error log for permission denied. Got: {[r.message for r in caplog.records]}"


def test_debug_logs_not_emitted_at_error_level(tmp_path, monkeypatch, caplog) -> None:
    """Verify DEBUG logs are not emitted when TODO_LOG_LEVEL is set to ERROR."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="task1")]

    # Set to ERROR level (above DEBUG)
    monkeypatch.setenv("TODO_LOG_LEVEL", "ERROR")
    logger = get_logger()
    logger.setLevel(logging.ERROR)

    with caplog.at_level(logging.ERROR):
        storage.save(todos)
        storage.load()

    # Verify no DEBUG logs were emitted
    debug_records = [r for r in caplog.records if r.levelname == "DEBUG"]
    assert len(debug_records) == 0, f"Expected no DEBUG logs at ERROR level. Got: {[r.message for r in debug_records]}"


def test_ensure_parent_directory_logs_on_creation(tmp_path, monkeypatch, caplog) -> None:
    """Verify _ensure_parent_directory logs when creating parent directory."""
    db = tmp_path / "subdir" / "nested" / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="task1")]

    # Enable DEBUG logging
    monkeypatch.setenv("TODO_LOG_LEVEL", "DEBUG")
    logger = get_logger()
    logger.setLevel(logging.DEBUG)

    with caplog.at_level(logging.DEBUG):
        storage.save(todos)

    # Verify log for directory creation
    assert any(
        "Created directory" in record.message or "parent" in record.message.lower()
        for record in caplog.records
    ), f"Expected log for directory creation. Got: {[r.message for r in caplog.records]}"
