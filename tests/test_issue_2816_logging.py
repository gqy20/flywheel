"""Regression tests for issue #2816: Add logging module for debugging file operations.

Issue: Storage operations have no logging, making it hard to debug file permissions,
directory creation, atomic writes, etc.

This test FAILS before the fix (no logger exists) and PASSES after the fix.
"""

from __future__ import annotations

import logging

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_storage_module_has_logger() -> None:
    """Issue #2816: storage module should have a logger defined."""
    import flywheel.storage as storage_module

    # Module should have a logger attribute
    assert hasattr(storage_module, "logger"), (
        "storage module should have a 'logger' attribute for debugging file operations"
    )

    # Logger should be a logging.Logger instance
    assert isinstance(storage_module.logger, logging.Logger), (
        "Module logger should be a logging.Logger instance"
    )

    # Logger name should match the module
    assert storage_module.logger.name == "flywheel.storage", (
        f"Logger name should be 'flywheel.storage', got '{storage_module.logger.name}'"
    )


def test_load_logs_debug_info(tmp_path, caplog) -> None:
    """Issue #2816: load() should log file path and size at DEBUG level."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a test file with known content
    todos = [Todo(id=1, text="test todo"), Todo(id=2, text="another todo")]
    storage.save(todos)

    # Load with logging enabled
    with caplog.at_level(logging.DEBUG):
        loaded = storage.load()

    # Should have loaded successfully
    assert len(loaded) == 2

    # Should have debug log entries
    debug_records = [r for r in caplog.records if r.levelname == "DEBUG"]
    assert len(debug_records) > 0, "load() should produce debug log entries"

    # Check for file path in logs
    log_messages = [r.message for r in debug_records]
    assert any(str(db) in msg for msg in log_messages), (
        f"load() should log file path. Messages: {log_messages}"
    )

    # Check for file size in logs (should mention bytes or size)
    assert any("byte" in msg.lower() or "size" in msg.lower() for msg in log_messages), (
        f"load() should log file size. Messages: {log_messages}"
    )


def test_load_logs_empty_file(tmp_path, caplog) -> None:
    """Issue #2816: load() should log when file doesn't exist (empty state)."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Load non-existent file with logging enabled
    with caplog.at_level(logging.DEBUG):
        loaded = storage.load()

    # Should return empty list
    assert loaded == []

    # Should have debug log about non-existent file or empty state
    debug_records = [r for r in caplog.records if r.levelname == "DEBUG"]
    log_messages = [r.message for r in debug_records]

    assert any(
        "not exist" in msg.lower() or "not found" in msg.lower() or "empty" in msg.lower()
        for msg in log_messages
    ), f"load() should log when file doesn't exist. Messages: {log_messages}"


def test_save_logs_atomic_write_steps(tmp_path, caplog) -> None:
    """Issue #2816: save() should log atomic write steps at DEBUG level."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="save test")]

    # Save with logging enabled
    with caplog.at_level(logging.DEBUG):
        storage.save(todos)

    # Should have debug log entries
    debug_records = [r for r in caplog.records if r.levelname == "DEBUG"]
    assert len(debug_records) > 0, "save() should produce debug log entries"

    log_messages = [r.message for r in debug_records]

    # Should log temp file creation
    assert any(
        "temp" in msg.lower() or ".tmp" in msg or "tmp" in msg.lower()
        for msg in log_messages
    ), f"save() should log temp file creation. Messages: {log_messages}"

    # Should log atomic rename operation
    assert any(
        "rename" in msg.lower() or "replace" in msg.lower() or "atomic" in msg.lower()
        for msg in log_messages
    ), f"save() should log atomic rename. Messages: {log_messages}"


def test_ensure_parent_directory_logs_creation(tmp_path, caplog) -> None:
    """Issue #2816: _ensure_parent_directory() should log directory creation."""
    # Create a path that needs parent directory creation
    new_dir = tmp_path / "newdir" / "subdir" / "todo.json"

    with caplog.at_level(logging.DEBUG):
        _ensure_parent_directory(new_dir)

    # Should have debug log entries
    debug_records = [r for r in caplog.records if r.levelname == "DEBUG"]
    assert len(debug_records) > 0, "_ensure_parent_directory() should produce debug log entries"

    log_messages = [r.message for r in debug_records]

    # Should log directory creation
    assert any(
        "creat" in msg.lower() or "mkdir" in msg.lower() or "directory" in msg.lower()
        for msg in log_messages
    ), f"_ensure_parent_directory() should log directory creation. Messages: {log_messages}"


def test_logging_does_not_break_existing_functionality(tmp_path) -> None:
    """Issue #2816: Adding logging should not break existing storage functionality."""
    storage = TodoStorage(str(tmp_path / "todo.json"))

    # Test load/save cycle
    todos = [
        Todo(id=1, text="task 1"),
        Todo(id=2, text="task 2", done=True),
        Todo(id=3, text="task with unicode: 你好"),
    ]

    # Save
    storage.save(todos)

    # Load
    loaded = storage.load()

    # Verify
    assert len(loaded) == 3
    assert loaded[0].text == "task 1"
    assert loaded[1].done is True
    assert loaded[2].text == "task with unicode: 你好"


def test_logging_uses_logger_not_print(tmp_path, caplog) -> None:
    """Issue #2816: Should use logger.debug(), not print() for logging."""
    storage = TodoStorage(str(tmp_path / "todo.json"))

    todos = [Todo(id=1, text="test")]

    # Capture logging output
    with caplog.at_level(logging.DEBUG):
        storage.save(todos)
        storage.load()

    # Verify logs go through logging system, not stdout
    debug_records = [r for r in caplog.records if r.levelname == "DEBUG"]
    assert len(debug_records) > 0, "Should have debug log entries through logger"

    # Logger name should be flywheel.storage
    for record in debug_records:
        assert record.name == "flywheel.storage", (
            f"Log should come from flywheel.storage logger, got {record.name}"
        )
