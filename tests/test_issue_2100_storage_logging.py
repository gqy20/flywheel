"""Tests for storage operation logging (Issue #2100).

These tests verify that:
1. A get_logger() function returns a configured logger instance
2. load() logs DEBUG on success with file path and count
3. load() logs ERROR on failure with exception details
4. save() logs DEBUG on success with file path and count
5. save() logs ERROR on failure with exception details
6. TODO_LOG_LEVEL environment variable controls log level
"""

from __future__ import annotations

import logging

import pytest

from flywheel.storage import TodoStorage, get_logger
from flywheel.todo import Todo


def test_get_logger_returns_logger_instance() -> None:
    """get_logger() should return a configured logger instance."""
    logger = get_logger()
    assert isinstance(logger, logging.Logger)
    assert logger.name == "flywheel.storage"


def test_get_logger_respects_todo_log_level_env_var(monkeypatch) -> None:
    """get_logger() should respect TODO_LOG_LEVEL environment variable."""
    # Set TODO_LOG_LEVEL to DEBUG
    monkeypatch.setenv("TODO_LOG_LEVEL", "DEBUG")
    logger = get_logger()
    assert logger.level == logging.DEBUG

    # Reset for other tests
    monkeypatch.delenv("TODO_LOG_LEVEL", raising=False)


def test_get_logger_defaults_to_warning_level(monkeypatch) -> None:
    """get_logger() should default to WARNING level when env var not set."""
    # Ensure TODO_LOG_LEVEL is not set
    monkeypatch.delenv("TODO_LOG_LEVEL", raising=False)
    logger = get_logger()
    assert logger.level == logging.WARNING


def test_load_logs_debug_on_success_with_file_path_and_count(
    tmp_path, caplog, monkeypatch
) -> None:
    """load() should log DEBUG level with file path and todo count on success."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]
    storage.save(todos)

    # Set log level to DEBUG to capture logs
    monkeypatch.setenv("TODO_LOG_LEVEL", "DEBUG")
    with caplog.at_level(logging.DEBUG):
        storage.load()

    # Verify DEBUG log was recorded
    assert len(caplog.records) > 0
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug_records) > 0
    # Should contain file path
    assert any(str(db) in record.getMessage() for record in debug_records)
    # Should contain count
    assert any("2" in record.getMessage() for record in debug_records)


def test_load_logs_error_on_json_decode_failure(tmp_path, caplog) -> None:
    """load() should log ERROR level with exception details on JSON decode error."""
    db = tmp_path / "malformed.json"
    storage = TodoStorage(str(db))

    # Create malformed JSON
    db.write_text('[{"id": 1, "text": "task1"}', encoding="utf-8")

    # Set log level to ERROR to capture logs
    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(ValueError, match="Invalid JSON"),
    ):
        storage.load()

    # Verify ERROR log was recorded
    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_records) > 0
    # Should mention the error
    assert any(
        "JSON" in record.getMessage() or "json" in record.getMessage()
        for record in error_records
    )


def test_load_logs_error_on_file_size_limit_exceeded(tmp_path, caplog) -> None:
    """load() should log ERROR level when file size exceeds limit."""
    db = tmp_path / "huge.json"
    storage = TodoStorage(str(db))

    # Create a file larger than the limit
    db.write_text("x" * 11 * 1024 * 1024, encoding="utf-8")

    # Set log level to ERROR to capture logs
    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(ValueError, match="too large"),
    ):
        storage.load()

    # Verify ERROR log was recorded
    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_records) > 0


def test_save_logs_debug_on_success_with_file_path_and_count(
    tmp_path, caplog, monkeypatch
) -> None:
    """save() should log DEBUG level with file path and todo count on success."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]

    # Set log level to DEBUG to capture logs
    monkeypatch.setenv("TODO_LOG_LEVEL", "DEBUG")
    with caplog.at_level(logging.DEBUG):
        storage.save(todos)

    # Verify DEBUG log was recorded
    assert len(caplog.records) > 0
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug_records) > 0
    # Should contain file path
    assert any(str(db) in record.getMessage() for record in debug_records)
    # Should contain count
    assert any("2" in record.getMessage() for record in debug_records)


def test_save_logs_error_on_permission_denied(tmp_path, caplog, monkeypatch) -> None:
    """save() should log ERROR level when permission is denied."""
    # Create a read-only directory
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    readonly_dir.chmod(0o444)

    # Update db path to point to read-only directory
    readonly_db = readonly_dir / "test.json"
    storage_readonly = TodoStorage(str(readonly_db))

    # Set log level to ERROR to capture logs
    with caplog.at_level(logging.ERROR):
        try:
            with pytest.raises(OSError):
                storage_readonly.save([Todo(id=1, text="task1")])
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)


def test_save_logs_error_on_directory_creation_failure(
    tmp_path, caplog, monkeypatch
) -> None:
    """save() should log ERROR level when directory creation fails."""
    # This tests the _ensure_parent_directory logging
    db = tmp_path / "subdir" / "test.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="task1")]

    # Set log level to DEBUG to capture logs
    monkeypatch.setenv("TODO_LOG_LEVEL", "DEBUG")
    with caplog.at_level(logging.DEBUG):
        storage.save(todos)

    # Verify DEBUG log was recorded for directory creation
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug_records) > 0
    # Should mention directory creation
    assert any(
        "directory" in record.getMessage().lower() or "dir" in record.getMessage().lower()
        for record in debug_records
    )


def test_logger_respects_log_level_filtering(tmp_path, caplog, monkeypatch) -> None:
    """When TODO_LOG_LEVEL=ERROR, DEBUG logs should not be output."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Set log level to ERROR
    monkeypatch.setenv("TODO_LOG_LEVEL", "ERROR")

    todos = [Todo(id=1, text="task1")]

    # Set log level to DEBUG to capture all logs
    with caplog.at_level(logging.DEBUG):
        storage.save(todos)

    # DEBUG logs should not be recorded when level is ERROR
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug_records) == 0

    # Reset for other tests
    monkeypatch.delenv("TODO_LOG_LEVEL", raising=False)
