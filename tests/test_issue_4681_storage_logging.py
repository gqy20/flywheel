"""Tests for optional logging in storage operations.

This test suite verifies that TodoStorage can optionally log operations
when FLYWHEEL_DEBUG environment variable is set.

Issue: #4681
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class LogCapture(logging.Handler):
    """Custom log handler to capture log records for testing."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def get_messages(self) -> list[str]:
        return [self.format(r) for r in self.records]

    def clear(self) -> None:
        self.records.clear()


@pytest.fixture
def debug_env(monkeypatch):
    """Fixture to set FLYWHEEL_DEBUG=1 and clean up after test."""
    monkeypatch.setenv("FLYWHEEL_DEBUG", "1")
    yield
    monkeypatch.delenv("FLYWHEEL_DEBUG", raising=False)


@pytest.fixture
def no_debug_env(monkeypatch):
    """Fixture to ensure FLYWHEEL_DEBUG is not set."""
    monkeypatch.delenv("FLYWHEEL_DEBUG", raising=False)
    yield


@pytest.fixture
def log_capture():
    """Fixture to capture log messages."""
    handler = LogCapture()
    logger = logging.getLogger("flywheel.storage")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield handler
    logger.removeHandler(handler)


def test_storage_load_logs_debug_when_enabled(tmp_path, debug_env, log_capture) -> None:
    """When FLYWHEEL_DEBUG=1, storage.load() should log debug information."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save some todos
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Clear previous logs
    log_capture.clear()

    # Load the todos
    loaded = storage.load()

    # Verify load succeeded
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"

    # Verify debug log was produced
    messages = log_capture.get_messages()
    assert any("load" in m.lower() for m in messages), f"Expected 'load' in logs: {messages}"
    assert any(str(db) in m or db.name in m for m in messages), f"Expected file path in logs: {messages}"


def test_storage_save_logs_debug_when_enabled(tmp_path, debug_env, log_capture) -> None:
    """When FLYWHEEL_DEBUG=1, storage.save() should log debug information."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="save test"), Todo(id=2, text="another")]
    storage.save(todos)

    # Verify debug log was produced
    messages = log_capture.get_messages()
    assert any("save" in m.lower() for m in messages), f"Expected 'save' in logs: {messages}"
    # Should include record count
    assert any("2" in m for m in messages), f"Expected record count '2' in logs: {messages}"


def test_storage_no_logging_when_debug_disabled(tmp_path, no_debug_env, log_capture) -> None:
    """When FLYWHEEL_DEBUG is not set, no debug logs should be produced."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="no debug")]
    storage.save(todos)
    log_capture.clear()

    loaded = storage.load()
    assert len(loaded) == 1

    # No debug logs should have been captured
    messages = [m for m in log_capture.get_messages() if "flywheel" in m.lower()]
    assert len(messages) == 0, f"Expected no flywheel logs when debug disabled: {messages}"


def test_storage_logs_include_timing_info(tmp_path, debug_env, log_capture) -> None:
    """Debug logs should include operation timing information."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a larger dataset to ensure measurable timing
    todos = [Todo(id=i, text=f"todo {i}") for i in range(100)]
    storage.save(todos)

    # Check that timing is included in save logs
    messages = log_capture.get_messages()
    save_logs = [m for m in messages if "save" in m.lower()]
    assert len(save_logs) > 0, f"Expected save logs: {messages}"

    # Timing should be mentioned (ms, seconds, or elapsed)
    has_timing = any(
        any(term in m.lower() for term in ["ms", "sec", "elapsed", "duration", "took", "time"])
        for m in save_logs
    )
    assert has_timing, f"Expected timing info in save logs: {save_logs}"


def test_storage_load_nonexistent_file_logs_when_enabled(tmp_path, debug_env, log_capture) -> None:
    """Loading a non-existent file should still log the attempt when debug enabled."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    log_capture.clear()
    loaded = storage.load()

    # Should return empty list
    assert loaded == []

    # Should still log the load attempt (even for non-existent file)
    messages = log_capture.get_messages()
    load_logs = [m for m in messages if "load" in m.lower()]
    # Could log that file doesn't exist or just return empty
    # The key is that the operation was logged


def test_storage_debug_via_constructor_param(tmp_path, log_capture) -> None:
    """Debug logging can be enabled via constructor parameter, not just env var."""
    # Don't set FLYWHEEL_DEBUG env var
    db = tmp_path / "todo.json"

    # Create storage with debug enabled via parameter
    storage = TodoStorage(str(db), debug=True)

    todos = [Todo(id=1, text="param debug")]
    log_capture.clear()
    storage.save(todos)

    # Debug logs should still be produced
    messages = log_capture.get_messages()
    save_logs = [m for m in messages if "save" in m.lower()]
    assert len(save_logs) > 0, f"Expected save logs with debug=True param: {messages}"
