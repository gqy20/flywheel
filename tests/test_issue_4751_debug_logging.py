"""Tests for optional debug logging in TodoStorage.

Issue #4751: Add optional debug logging functionality.
When debug=True, TodoStorage should log load/save operations including:
- File path
- Operation type
- Operation duration
- Error information if applicable
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_accepts_debug_parameter(tmp_path: Path) -> None:
    """TodoStorage should accept debug parameter."""
    db = tmp_path / "todo.json"

    # Should not raise - debug parameter should be accepted
    storage = TodoStorage(str(db), debug=True)
    assert storage.debug is True

    # Default should be False
    storage_default = TodoStorage(str(db))
    assert storage_default.debug is False


def test_debug_false_produces_no_debug_logs(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """When debug=False, no debug logs should be produced."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), debug=False)

    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        storage.load()

    # No debug logs should be captured
    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug_records) == 0


def test_debug_true_logs_save_operation(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """When debug=True, save operation should be logged."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), debug=True)

    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

    # Should have debug logs for save
    assert len(caplog.records) > 0
    log_messages = [r.message for r in caplog.records]

    # Check that save operation is logged
    save_logs = [m for m in log_messages if "save" in m.lower()]
    assert len(save_logs) > 0, "Save operation should be logged when debug=True"

    # Check that file path is mentioned
    any_log_with_path = any(str(db) in m for m in log_messages)
    assert any_log_with_path, "File path should be in debug logs"


def test_debug_true_logs_load_operation(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """When debug=True, load operation should be logged."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), debug=True)

    # First save some data
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    caplog.clear()

    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        storage.load()

    # Should have debug logs for load
    assert len(caplog.records) > 0
    log_messages = [r.message for r in caplog.records]

    # Check that load operation is logged
    load_logs = [m for m in log_messages if "load" in m.lower()]
    assert len(load_logs) > 0, "Load operation should be logged when debug=True"


def test_debug_log_includes_file_size_on_load(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """When debug=True, load operation log should include file size."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), debug=True)

    # Save some data
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    caplog.clear()

    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        storage.load()

    # Check that file size or bytes is mentioned in logs
    log_messages = [r.message for r in caplog.records]
    any_log_with_size = any(
        "size" in m.lower() or "bytes" in m.lower() or "byte" in m.lower() for m in log_messages
    )
    assert any_log_with_size, "File size should be mentioned in debug logs"


def test_debug_log_includes_duration(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """When debug=True, operation logs should include duration."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), debug=True)

    with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
        todos = [Todo(id=1, text="test")]
        storage.save(todos)

    # Check that duration or time is mentioned in logs
    log_messages = [r.message for r in caplog.records]
    any_log_with_duration = any(
        "duration" in m.lower() or "ms" in m.lower() or "time" in m.lower() for m in log_messages
    )
    assert any_log_with_duration, "Duration should be mentioned in debug logs"


def test_debug_log_on_error(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """When debug=True and an error occurs, error should be logged."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), debug=True)

    # Create invalid JSON file
    db.write_text("invalid json {", encoding="utf-8")

    with (
        caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
        pytest.raises(ValueError),
    ):
        storage.load()

    # Check that error is logged
    log_messages = [r.message for r in caplog.records]
    any_log_with_error = any(
        "error" in m.lower() or "invalid" in m.lower() or "failed" in m.lower()
        for m in log_messages
    )
    assert any_log_with_error, "Error information should be in debug logs"
