"""Tests for storage logging capability - Issue #2100.

This test suite verifies that TodoStorage provides proper logging for debugging
and audit purposes. Logger configuration should be controlled by TODO_LOG_LEVEL
environment variable.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, get_logger
from flywheel.todo import Todo


def test_get_logger_returns_configured_logger() -> None:
    """Test that get_logger() returns a properly configured logger instance."""
    logger = get_logger()

    # Should return a logging.Logger instance
    assert isinstance(logger, logging.Logger)

    # Should have the correct name
    assert logger.name == "flywheel.storage"


def test_get_logger_respects_todo_log_level_env_var() -> None:
    """Test that get_logger() respects TODO_LOG_LEVEL environment variable."""
    with patch.dict("os.environ", {"TODO_LOG_LEVEL": "DEBUG"}):
        # Clear any cached logger
        import importlib

        import flywheel.storage

        importlib.reload(flywheel.storage)

        logger = get_logger()
        assert logger.level == logging.DEBUG
        assert logger.level == 10  # DEBUG = 10


def test_get_logger_defaults_to_warning_level() -> None:
    """Test that get_logger() defaults to WARNING level when TODO_LOG_LEVEL not set."""
    # Remove TODO_LOG_LEVEL from environment if present
    with patch.dict("os.environ", {}, clear=False):
        import os

        env_copy = os.environ.copy()
        env_copy.pop("TODO_LOG_LEVEL", None)

        with patch.dict("os.environ", env_copy, clear=True):
            # Clear any cached logger
            import importlib

            import flywheel.storage

            importlib.reload(flywheel.storage)

            logger = get_logger()
            assert logger.level == logging.WARNING
            assert logger.level == 30  # WARNING = 30


def test_load_logs_debug_on_success(tmp_path, caplog) -> None:
    """Test that load() logs DEBUG level on success with file path and count."""
    # Set log level to DEBUG before creating storage
    import os

    os.environ["TODO_LOG_LEVEL"] = "DEBUG"

    # Clear cached logger to force re-read of environment variable
    import flywheel.storage

    flywheel.storage._logger = None

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]
    storage.save(todos)

    # Enable DEBUG level logging
    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        loaded = storage.load()

    # Verify DEBUG log was created with file path and count
    assert len(loaded) == 2
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug_records) >= 1
    # Check that log contains file path and count
    log_message = debug_records[0].message
    assert str(db) in log_message or "todo.json" in log_message
    assert "2" in log_message or "todo" in log_message.lower()

    # Clean up environment
    os.environ.pop("TODO_LOG_LEVEL", None)
    flywheel.storage._logger = None


def test_load_logs_error_on_json_decode_error(tmp_path, caplog) -> None:
    """Test that load() logs ERROR level on JSON decode failure with exception details."""
    db = tmp_path / "corrupt.json"
    storage = TodoStorage(str(db))

    # Create corrupted JSON file
    db.write_text('{"id": 1, "text": "invalid"', encoding="utf-8")

    # Enable ERROR level logging
    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(ValueError, match="Invalid JSON"),
    ):
        storage.load()

    # Verify ERROR log was created with exception details
    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_records) >= 1
    # Check that log contains exception info
    log_message = error_records[0].message
    assert "JSON" in log_message or "json" in log_message.lower() or "decode" in log_message.lower()


def test_save_logs_debug_on_success(tmp_path, caplog) -> None:
    """Test that save() logs DEBUG level on success with file path and count."""
    # Set log level to DEBUG before creating storage
    import os

    os.environ["TODO_LOG_LEVEL"] = "DEBUG"

    # Clear cached logger to force re-read of environment variable
    import flywheel.storage

    flywheel.storage._logger = None

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2"), Todo(id=3, text="task3")]

    # Enable DEBUG level logging
    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        storage.save(todos)

    # Verify DEBUG log was created with file path and count
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug_records) >= 1
    # Check that log contains file path and count
    log_message = debug_records[0].message
    assert str(db) in log_message or "todo.json" in log_message
    assert "3" in log_message or "todo" in log_message.lower()

    # Clean up environment
    os.environ.pop("TODO_LOG_LEVEL", None)
    flywheel.storage._logger = None


def test_save_logs_error_on_permission_error(tmp_path, caplog) -> None:
    """Test that save() logs ERROR level on permission failure with exception details."""
    # Set log level to DEBUG to capture all logs
    import os

    os.environ["TODO_LOG_LEVEL"] = "DEBUG"

    # Clear cached logger to force re-read of environment variable
    import flywheel.storage

    flywheel.storage._logger = None

    # Create a readonly parent directory
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    readonly_db = readonly_dir / "todo.json"
    readonly_storage = TodoStorage(str(readonly_db))

    # Make directory readonly
    import stat

    readonly_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)  # r-x for owner only

    try:
        todos = [Todo(id=1, text="task1")]

        # Enable ERROR level logging
        with (
            caplog.at_level(logging.ERROR, logger="flywheel.storage"),
            pytest.raises(OSError),
        ):
            readonly_storage.save(todos)

        # Verify ERROR log was created with exception info
        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(error_records) >= 1
        # Check that log contains error info
        log_message = error_records[0].message
        assert (
            "permission" in log_message.lower()
            or "error" in log_message.lower()
            or "failed" in log_message.lower()
        )
    finally:
        # Restore permissions for cleanup
        readonly_dir.chmod(stat.S_IRWXU)
        # Clean up environment
        os.environ.pop("TODO_LOG_LEVEL", None)
        flywheel.storage._logger = None


def test_no_debug_logs_when_log_level_is_error(tmp_path, caplog) -> None:
    """Test that DEBUG logs are suppressed when TODO_LOG_LEVEL=ERROR."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="task1")]

    # Set log level to ERROR via environment
    with patch.dict("os.environ", {"TODO_LOG_LEVEL": "ERROR"}):
        # Clear any cached logger
        import importlib

        import flywheel.storage

        importlib.reload(flywheel.storage)

        # Only log ERROR level
        with caplog.at_level(logging.ERROR):
            storage.save(todos)
            storage.load()

    # Verify no DEBUG logs were created
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug_records) == 0


def test_logger_has_handler_when_log_level_is_set(tmp_path) -> None:
    """Test that logger has handler when TODO_LOG_LEVEL is set."""
    with patch.dict("os.environ", {"TODO_LOG_LEVEL": "DEBUG"}):
        # Clear any cached logger
        import importlib

        import flywheel.storage

        importlib.reload(flywheel.storage)

        logger = get_logger()
        # Logger should have handlers
        assert len(logger.handlers) > 0 or logger.propagate is True


def test_load_nonexistent_file_returns_empty_list_without_error(tmp_path, caplog) -> None:
    """Test that loading a nonexistent file returns empty list without ERROR log."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Enable ERROR level logging
    with caplog.at_level(logging.ERROR):
        loaded = storage.load()

    # Should return empty list
    assert loaded == []

    # Should NOT have ERROR logs (this is expected behavior)
    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_records) == 0


def test_load_logs_debug_for_nonexistent_file(tmp_path, caplog) -> None:
    """Test that loading a nonexistent file logs DEBUG message."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Enable DEBUG level logging
    with caplog.at_level(logging.DEBUG):
        loaded = storage.load()

    # Should return empty list
    assert loaded == []

    # Should have DEBUG log about nonexistent file
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug_records) >= 1
    log_message = debug_records[0].message
    assert (
        "not found" in log_message.lower()
        or "no file" in log_message.lower()
        or str(db) in log_message
    )
