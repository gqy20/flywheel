"""Tests for Issue #2431: Debug mode logging support in TodoStorage.

This test suite verifies that TodoStorage provides optional logging
for tracking file operations, performance issues, and error diagnosis.
"""

from __future__ import annotations

import json
import logging
import os

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_flywheel_debug_0_no_log_output(tmp_path, caplog) -> None:
    """Test that FLYWHEEL_DEBUG=0 produces no log output (default behavior)."""
    # Ensure debug mode is OFF
    if "FLYWHEEL_DEBUG" in os.environ:
        del os.environ["FLYWHEEL_DEBUG"]

    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Perform operations
    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]
    storage.save(todos)
    loaded = storage.load()
    next_id = storage.next_id(loaded)

    # Verify operations succeeded
    assert len(loaded) == 2
    assert next_id == 3

    # Verify NO logging output by default
    # (caplog captures all log records during test)
    assert len(caplog.records) == 0, "Expected no log output when FLYWHEEL_DEBUG is not set"


def test_flywheel_debug_1_load_logs_debug_info(tmp_path, caplog) -> None:
    """Test that FLYWHEEL_DEBUG=1 enables DEBUG logs for load operations."""
    # Enable debug mode
    os.environ["FLYWHEEL_DEBUG"] = "1"

    try:
        # Setup: create a file with known content
        db = tmp_path / "test.json"
        todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2", done=True)]
        db.write_text(json.dumps([t.to_dict() for t in todos]), encoding="utf-8")

        # Configure capture for flywheel.storage module at DEBUG level
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage = TodoStorage(str(db))
            loaded = storage.load()

        # Verify load succeeded
        assert len(loaded) == 2

        # Verify DEBUG logs were emitted
        storage_logs = [r for r in caplog.records if r.name == "flywheel.storage"]
        assert len(storage_logs) > 0, "Expected DEBUG logs when FLYWHEEL_DEBUG=1"

        # Verify key information is in logs
        log_messages = [r.message for r in storage_logs]
        assert any("load" in msg.lower() for msg in log_messages), "Expected 'load' in log message"

        # Verify file path is logged
        assert any(str(db) in r.message for r in storage_logs), "Expected file path in logs"

        # Verify count is logged
        assert any("2" in r.message for r in storage_logs), "Expected count in logs"
    finally:
        # Clean up
        if "FLYWHEEL_DEBUG" in os.environ:
            del os.environ["FLYWHEEL_DEBUG"]


def test_flywheel_debug_1_save_logs_debug_info(tmp_path, caplog) -> None:
    """Test that FLYWHEEL_DEBUG=1 enables DEBUG logs for save operations."""
    # Enable debug mode
    os.environ["FLYWHEEL_DEBUG"] = "1"

    try:
        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]

        # Configure capture for flywheel.storage module at DEBUG level
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # Verify save succeeded
        assert db.exists()

        # Verify DEBUG logs were emitted
        storage_logs = [r for r in caplog.records if r.name == "flywheel.storage"]
        assert len(storage_logs) > 0, "Expected DEBUG logs when FLYWHEEL_DEBUG=1"

        # Verify save operation is logged
        log_messages = [r.message for r in storage_logs]
        assert any("save" in msg.lower() for msg in log_messages), "Expected 'save' in log message"

        # Verify count is logged
        assert any("2" in r.message for r in storage_logs), "Expected count in logs"
    finally:
        # Clean up
        if "FLYWHEEL_DEBUG" in os.environ:
            del os.environ["FLYWHEEL_DEBUG"]


def test_flywheel_debug_1_next_id_logs_debug_info(tmp_path, caplog) -> None:
    """Test that FLYWHEEL_DEBUG=1 enables DEBUG logs for next_id operations."""
    # Enable debug mode
    os.environ["FLYWHEEL_DEBUG"] = "1"

    try:
        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="task1"), Todo(id=5, text="task5")]

        # Configure capture for flywheel.storage module at DEBUG level
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            next_id = storage.next_id(todos)

        # Verify next_id calculation
        assert next_id == 6

        # Verify DEBUG logs were emitted
        storage_logs = [r for r in caplog.records if r.name == "flywheel.storage"]
        assert len(storage_logs) > 0, "Expected DEBUG logs when FLYWHEEL_DEBUG=1"

        # Verify next_id is logged
        log_messages = [r.message for r in storage_logs]
        assert any("next_id" in msg.lower() or "6" in msg for msg in log_messages), \
            "Expected next_id or calculated value in log message"
    finally:
        # Clean up
        if "FLYWHEEL_DEBUG" in os.environ:
            del os.environ["FLYWHEEL_DEBUG"]


def test_json_decode_failure_logs_warning(tmp_path, caplog) -> None:
    """Test that JSON decode failure logs WARNING with file path and error info."""
    # Enable debug mode to ensure all logs are captured
    os.environ["FLYWHEEL_DEBUG"] = "1"

    try:
        db = tmp_path / "invalid.json"
        # Write invalid JSON
        db.write_text('{"invalid": json}', encoding="utf-8")

        storage = TodoStorage(str(db))

        # Configure capture at WARNING level
        with (
            caplog.at_level(logging.WARNING, logger="flywheel.storage"),
            pytest.raises(ValueError, match="Invalid JSON"),
        ):
            storage.load()

        # Verify WARNING log was emitted
        warning_logs = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_logs) > 0, "Expected WARNING log on JSON decode failure"

        # Verify file path is in warning
        assert any(str(db) in r.message for r in warning_logs), \
            "Expected file path in WARNING log"

        # Verify error info is in warning
        assert any("json" in r.message.lower() or "decode" in r.message.lower()
                   for r in warning_logs), \
            "Expected error info in WARNING log"
    finally:
        # Clean up
        if "FLYWHEEL_DEBUG" in os.environ:
            del os.environ["FLYWHEEL_DEBUG"]


def test_file_too_large_logs_warning(tmp_path, caplog) -> None:
    """Test that file size check failure logs WARNING."""
    # Enable debug mode
    os.environ["FLYWHEEL_DEBUG"] = "1"

    try:
        db = tmp_path / "large.json"
        storage = TodoStorage(str(db))

        # Create a file larger than 10MB
        large_payload = [
            {"id": i, "text": "x" * 100}
            for i in range(150000)  # ~15MB
        ]
        db.write_text(json.dumps(large_payload), encoding="utf-8")

        # Verify file is actually too large
        assert db.stat().st_size > 10 * 1024 * 1024

        # Configure capture at WARNING level
        with (
            caplog.at_level(logging.WARNING, logger="flywheel.storage"),
            pytest.raises(ValueError, match="too large"),
        ):
            storage.load()

        # Verify WARNING log was emitted
        warning_logs = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_logs) > 0, "Expected WARNING log on file size check failure"

        # Verify size info is in warning
        assert any("size" in r.message.lower() or "mb" in r.message.lower()
                   for r in warning_logs), \
            "Expected size info in WARNING log"
    finally:
        # Clean up
        if "FLYWHEEL_DEBUG" in os.environ:
            del os.environ["FLYWHEEL_DEBUG"]


def test_atomic_rename_logged_in_debug_mode(tmp_path, caplog) -> None:
    """Test that atomic rename operation is logged in debug mode."""
    # Enable debug mode
    os.environ["FLYWHEEL_DEBUG"] = "1"

    try:
        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="task")]

        # Configure capture at DEBUG level
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # Verify save succeeded
        assert db.exists()

        # Verify atomic rename operation is logged
        debug_logs = [r for r in caplog.records if r.levelno == logging.DEBUG
                      and r.name == "flywheel.storage"]
        assert len(debug_logs) > 0, "Expected DEBUG logs for save operation"

        # Verify rename/temp file info is logged
        log_messages = [r.message for r in debug_logs]
        # Should mention atomic operation or temp file
        assert any("atomic" in msg.lower() or "rename" in msg.lower() or "temp" in msg.lower()
                   for msg in log_messages), \
            "Expected atomic/rename/temp info in DEBUG logs"
    finally:
        # Clean up
        if "FLYWHEEL_DEBUG" in os.environ:
            del os.environ["FLYWHEEL_DEBUG"]


def test_load_empty_file_returns_empty_list_with_logs(tmp_path, caplog) -> None:
    """Test that loading from non-existent file returns empty list and logs appropriately."""
    # Enable debug mode
    os.environ["FLYWHEEL_DEBUG"] = "1"

    try:
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        # Configure capture at DEBUG level
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        # Verify empty list is returned
        assert loaded == []

        # Verify file not found is logged (debug level)
        debug_logs = [r for r in caplog.records if r.levelno == logging.DEBUG
                      and r.name == "flywheel.storage"]
        assert len(debug_logs) > 0, "Expected DEBUG log for non-existent file"

        # Verify file path is in log
        assert any(str(db) in r.message for r in debug_logs), \
            "Expected file path in DEBUG log"
    finally:
        # Clean up
        if "FLYWHEEL_DEBUG" in os.environ:
            del os.environ["FLYWHEEL_DEBUG"]
