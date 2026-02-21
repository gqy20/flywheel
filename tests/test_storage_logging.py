"""Tests for logging functionality in TodoStorage.

This test suite verifies that TodoStorage can optionally log operations
for debugging purposes when storage operations fail.
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
    logger = logging.getLogger("test_logger")
    storage = TodoStorage(str(db), logger=logger)
    assert storage.logger is logger


def test_storage_without_logger_works_as_before(tmp_path: Path) -> None:
    """Test that TodoStorage works without logger (backward compatibility)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    assert storage.logger is None

    # Should work normally
    todos = [Todo(id=1, text="test")]
    storage.save(todos)
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_load_logs_debug_on_json_decode_error(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that load logs DEBUG when JSON decode error occurs."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_storage_logger")
    logger.setLevel(logging.DEBUG)
    storage = TodoStorage(str(db), logger=logger)

    # Create invalid JSON file
    db.write_text("{invalid json", encoding="utf-8")

    with caplog.at_level(logging.DEBUG, logger="test_storage_logger"):
        with pytest.raises(ValueError, match="Invalid JSON"):
            storage.load()

    # Check that DEBUG log was recorded
    assert any("json decode error" in record.message.lower() for record in caplog.records), \
        f"Expected JSON decode error log, got: {[r.message for r in caplog.records]}"


def test_save_logs_debug_on_oserror(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that save logs DEBUG when OSError occurs during write."""
    db = tmp_path / "todo.json"
    logger = logging.getLogger("test_storage_logger_save")
    logger.setLevel(logging.DEBUG)
    storage = TodoStorage(str(db), logger=logger)

    todos = [Todo(id=1, text="test")]

    # Simulate OSError during os.replace (atomic rename)
    def failing_replace(*args, **kwargs):
        raise OSError("Simulated rename failure")

    import os as os_module

    with caplog.at_level(logging.DEBUG, logger="test_storage_logger_save"):
        with patch.object(os_module, "replace", failing_replace):
            with pytest.raises(OSError, match="Simulated rename failure"):
                storage.save(todos)

    # Check that DEBUG log was recorded
    assert any("oserror" in record.message.lower() for record in caplog.records), \
        f"Expected OSError log, got: {[r.message for r in caplog.records]}"


def test_load_without_logger_no_error_on_invalid_json(tmp_path: Path) -> None:
    """Test that load still raises proper error even without logger."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))  # No logger

    # Create invalid JSON file
    db.write_text("{invalid json", encoding="utf-8")

    # Should still raise the proper error
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()


def test_save_without_logger_raises_proper_error(tmp_path: Path) -> None:
    """Test that save still raises proper error even without logger."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))  # No logger

    todos = [Todo(id=1, text="test")]

    # Simulate OSError during temp file creation
    def failing_mkstemp(*args, **kwargs):
        raise OSError("Simulated write failure")

    import tempfile

    with patch.object(tempfile, "mkstemp", failing_mkstemp):
        with pytest.raises(OSError, match="Simulated write failure"):
            storage.save(todos)
