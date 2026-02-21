"""Tests for storage logging feature (issue #5044).

This test suite verifies that TodoStorage supports optional logging
to help diagnose issues when storage operations fail.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_accepts_optional_logger(tmp_path: Path) -> None:
    """Test that TodoStorage constructor accepts optional logger parameter."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_storage")
    storage = TodoStorage(str(db), logger=logger)
    assert storage.logger is logger


def test_storage_works_without_logger(tmp_path: Path) -> None:
    """Test that TodoStorage works normally when no logger is provided."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    assert storage.logger is None

    # Basic operations should work without any logger
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_load_logs_on_json_decode_error(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that load() logs at DEBUG level when JSON decode error occurs."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_storage_decode")
    logger.setLevel(logging.DEBUG)
    storage = TodoStorage(str(db), logger=logger)

    # Write invalid JSON to trigger JSONDecodeError
    db.write_text("{ invalid json", encoding="utf-8")

    with (
        caplog.at_level(logging.DEBUG, logger="test_storage_decode"),
        pytest.raises(ValueError, match="Invalid JSON"),
    ):
        storage.load()

    # Check that debug log was emitted
    assert any("JSON decode error" in record.message for record in caplog.records), (
        "Expected debug log for JSON decode error"
    )


def test_load_logs_on_file_read_error(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that load() logs at DEBUG level when file read error occurs."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_storage_read")
    logger.setLevel(logging.DEBUG)
    storage = TodoStorage(str(db), logger=logger)

    # Create a directory with the same name to cause read error
    db.mkdir()

    with (
        caplog.at_level(logging.DEBUG, logger="test_storage_read"),
        pytest.raises(OSError),
    ):
        storage.load()

    # Check that debug log was emitted
    assert any("File read error" in record.message for record in caplog.records), (
        "Expected debug log for file read error"
    )


def test_save_logs_on_oserror(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that save() logs at DEBUG level when OSError occurs."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_storage_save")
    logger.setLevel(logging.DEBUG)
    storage = TodoStorage(str(db), logger=logger)

    todos = [Todo(id=1, text="test")]

    # Make os.replace fail to trigger OSError in save (inside try/except)
    def failing_replace(*args, **kwargs):
        raise OSError("Simulated OS error during replace")

    import os as os_module

    with (
        caplog.at_level(logging.DEBUG, logger="test_storage_save"),
        patch.object(os_module, "replace", failing_replace),
        pytest.raises(OSError, match="Simulated OS error during replace"),
    ):
        storage.save(todos)

    # Check that debug log was emitted
    assert any("Save operation failed" in record.message for record in caplog.records), (
        "Expected debug log for save OSError"
    )


def test_no_logging_when_logger_is_none(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that no logs are emitted when logger is None."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))  # No logger

    # Write invalid JSON to trigger an error path
    db.write_text("{ invalid json", encoding="utf-8")

    with (
        caplog.at_level(logging.DEBUG),
        pytest.raises(ValueError),
    ):
        storage.load()

    # No logs should be emitted since logger is None
    assert len(caplog.records) == 0, "Expected no logs when logger is None"


def test_successful_operations_do_not_log(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that successful operations don't log (only error paths log)."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_storage_success")
    logger.setLevel(logging.DEBUG)
    storage = TodoStorage(str(db), logger=logger)

    todos = [Todo(id=1, text="test")]

    with caplog.at_level(logging.DEBUG, logger="test_storage_success"):
        storage.save(todos)
        loaded = storage.load()

    # No logs should be emitted for successful operations
    assert len(caplog.records) == 0, "Expected no logs for successful operations"
    assert len(loaded) == 1
