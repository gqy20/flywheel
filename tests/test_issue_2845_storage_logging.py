"""Tests for storage operation logging (Issue #2845).

This test suite verifies that TodoStorage provides configurable logging
for load()/save() operations to aid debugging in production environments.
"""

from __future__ import annotations

import logging

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_default_no_logging_output_on_load(tmp_path, caplog) -> None:
    """Test that by default (no FW_LOG_LEVEL set), load() produces no log output."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Load without FW_LOG_LEVEL set - should not log
    with caplog.at_level(logging.DEBUG):
        loaded = storage.load()

    assert len(loaded) == 1
    # No storage-related logs should be present
    storage_logs = [r for r in caplog.records if "flywheel.storage" in r.name]
    assert len(storage_logs) == 0


def test_default_no_logging_output_on_save(tmp_path, caplog) -> None:
    """Test that by default (no FW_LOG_LEVEL set), save() produces no log output."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Save without FW_LOG_LEVEL set - should not log
    with caplog.at_level(logging.DEBUG):
        storage.save(todos)

    # No storage-related logs should be present
    storage_logs = [r for r in caplog.records if "flywheel.storage" in r.name]
    assert len(storage_logs) == 0


def test_load_logs_info_when_file_not_found_with_fw_log_level_debug(tmp_path, monkeypatch, caplog) -> None:
    """Test that load() logs info when file doesn't exist and FW_LOG_LEVEL=DEBUG."""
    monkeypatch.setenv("FW_LOG_LEVEL", "DEBUG")

    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Load non-existent file with FW_LOG_LEVEL=DEBUG
    with caplog.at_level(logging.DEBUG):
        loaded = storage.load()

    assert loaded == []
    # Should log info about file not existing
    storage_logs = [r for r in caplog.records if "flywheel.storage" in r.name]
    assert len(storage_logs) >= 1
    log_messages = [r.message for r in storage_logs]
    assert any("not found" in msg.lower() or "does not exist" in msg.lower() for msg in log_messages)


def test_save_logs_info_with_fw_log_level_debug(tmp_path, monkeypatch, caplog) -> None:
    """Test that save() logs info when FW_LOG_LEVEL=DEBUG."""
    monkeypatch.setenv("FW_LOG_LEVEL", "DEBUG")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo"), Todo(id=2, text="another todo")]

    # Save with FW_LOG_LEVEL=DEBUG
    with caplog.at_level(logging.DEBUG):
        storage.save(todos)

    # Should log info about save operation
    storage_logs = [r for r in caplog.records if "flywheel.storage" in r.name]
    assert len(storage_logs) >= 1
    log_messages = [r.message for r in storage_logs]
    # Should include file path and todo count
    assert any("save" in msg.lower() for msg in log_messages)
    assert any("2" in msg or "todo" in msg.lower() for msg in log_messages)


def test_load_logs_info_with_fw_log_level_debug(tmp_path, monkeypatch, caplog) -> None:
    """Test that load() logs info when FW_LOG_LEVEL=DEBUG."""
    monkeypatch.setenv("FW_LOG_LEVEL", "DEBUG")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="test todo"), Todo(id=2, text="another todo")]
    storage.save(todos)

    # Clear caplog
    caplog.clear()

    # Load with FW_LOG_LEVEL=DEBUG
    with caplog.at_level(logging.DEBUG):
        loaded = storage.load()

    assert len(loaded) == 2
    # Should log info about load operation
    storage_logs = [r for r in caplog.records if "flywheel.storage" in r.name]
    assert len(storage_logs) >= 1
    log_messages = [r.message for r in storage_logs]
    # Should include file path and todo count
    assert any("load" in msg.lower() for msg in log_messages)
    assert any("2" in msg or "todo" in msg.lower() for msg in log_messages)


def test_save_logs_error_on_failure(tmp_path, monkeypatch, caplog) -> None:
    """Test that save() logs error when operation fails."""
    monkeypatch.setenv("FW_LOG_LEVEL", "DEBUG")

    # Create a file instead of directory to trigger error
    db = tmp_path / "file_as_dir" / "todo.json"
    db.parent.write_text("I am a file, not a directory")

    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Should log error on failure (ValueError is raised for file-as-directory)
    with caplog.at_level(logging.ERROR), pytest.raises(ValueError, match="exists as a file"):
        storage.save(todos)

    # Should log error
    error_logs = [r for r in caplog.records if r.levelno >= logging.ERROR and "flywheel.storage" in r.name]
    assert len(error_logs) >= 1


def test_load_logs_error_on_json_decode_error(tmp_path, monkeypatch, caplog) -> None:
    """Test that load() logs error when JSON is invalid."""
    monkeypatch.setenv("FW_LOG_LEVEL", "DEBUG")

    db = tmp_path / "invalid.json"
    db.write_text("{invalid json}", encoding="utf-8")

    storage = TodoStorage(str(db))

    # Should log error on JSON decode failure
    with caplog.at_level(logging.ERROR), pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()

    # Should log error
    error_logs = [r for r in caplog.records if r.levelno >= logging.ERROR and "flywheel.storage" in r.name]
    assert len(error_logs) >= 1


def test_load_logs_includes_timing_with_fw_log_level_debug(tmp_path, monkeypatch, caplog) -> None:
    """Test that load() logs timing information when FW_LOG_LEVEL=DEBUG."""
    monkeypatch.setenv("FW_LOG_LEVEL", "DEBUG")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Clear caplog
    caplog.clear()

    # Load with FW_LOG_LEVEL=DEBUG
    with caplog.at_level(logging.DEBUG):
        storage.load()

    # Should log timing info
    storage_logs = [r for r in caplog.records if "flywheel.storage" in r.name]
    assert len(storage_logs) >= 1
    # Timing info should be present (ms or seconds)
    log_messages = [r.message for r in storage_logs]
    assert any("ms" in msg or "second" in msg.lower() or "took" in msg.lower() for msg in log_messages)


def test_save_logs_includes_timing_with_fw_log_level_debug(tmp_path, monkeypatch, caplog) -> None:
    """Test that save() logs timing information when FW_LOG_LEVEL=DEBUG."""
    monkeypatch.setenv("FW_LOG_LEVEL", "DEBUG")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Save with FW_LOG_LEVEL=DEBUG
    with caplog.at_level(logging.DEBUG):
        storage.save(todos)

    # Should log timing info
    storage_logs = [r for r in caplog.records if "flywheel.storage" in r.name]
    assert len(storage_logs) >= 1
    # Timing info should be present (ms or seconds)
    log_messages = [r.message for r in storage_logs]
    assert any("ms" in msg or "second" in msg.lower() or "took" in msg.lower() for msg in log_messages)
