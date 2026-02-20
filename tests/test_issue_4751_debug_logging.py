"""Tests for optional debug logging feature in TodoStorage.

Issue #4751: Add optional debug logging functionality.

This test suite verifies that:
- TodoStorage supports debug=True parameter
- debug=True logs load/save operations with file path, operation type, duration
- debug=False produces no log output
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestDebugLoggingFeature:
    """Test suite for debug logging feature (issue #4751)."""

    def test_storage_accepts_debug_parameter(self, tmp_path: Path) -> None:
        """Test that TodoStorage accepts debug parameter in __init__."""
        db = tmp_path / "todo.json"
        # Should not raise - debug parameter should be accepted
        storage = TodoStorage(str(db), debug=True)
        assert storage.debug is True

        storage_debug_false = TodoStorage(str(db), debug=False)
        assert storage_debug_false.debug is False

        # Default should be False
        storage_default = TodoStorage(str(db))
        assert storage_default.debug is False

    def test_debug_false_produces_no_log_output(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that debug=False produces no log output."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), debug=False)

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            todos = [Todo(id=1, text="test todo")]
            storage.save(todos)
            storage.load()

        # No debug logs should be produced when debug=False
        assert len(caplog.records) == 0

    def test_debug_true_logs_save_operation(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that debug=True logs save operations with path and duration."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), debug=True)

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            todos = [Todo(id=1, text="test todo")]
            storage.save(todos)

        # Should have logged the save operation
        assert len(caplog.records) >= 1

        # Log should contain operation type and file path
        log_messages = [r.getMessage() for r in caplog.records]
        assert any("save" in msg.lower() for msg in log_messages), \
            f"Expected 'save' in log messages, got: {log_messages}"
        assert any(str(db) in msg for msg in log_messages), \
            f"Expected file path in log messages, got: {log_messages}"

    def test_debug_true_logs_load_operation(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that debug=True logs load operations with path and duration."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), debug=True)

        # First save some data
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        caplog.clear()

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        # Should have logged the load operation
        assert len(caplog.records) >= 1

        # Log should contain operation type and file path
        log_messages = [r.getMessage() for r in caplog.records]
        assert any("load" in msg.lower() for msg in log_messages), \
            f"Expected 'load' in log messages, got: {log_messages}"
        assert any(str(db) in msg for msg in log_messages), \
            f"Expected file path in log messages, got: {log_messages}"

        # Verify data integrity
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"

    def test_debug_log_includes_duration(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that debug logs include operation duration."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), debug=True)

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            todos = [Todo(id=1, text="test todo")]
            storage.save(todos)

        # Log should include duration (e.g., "0.123ms" or "123μs" or similar)
        log_messages = [r.getMessage() for r in caplog.records]
        has_duration = any(
            any(unit in msg for unit in ["ms", "μs", "us", "s", "sec", "elapsed", "duration", "took"])
            for msg in log_messages
        )
        assert has_duration, f"Expected duration info in log messages, got: {log_messages}"

    def test_debug_log_includes_file_size_on_load(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that debug logs include file size on load operation."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), debug=True)

        # Save some data
        todos = [Todo(id=1, text="test todo with some content")]
        storage.save(todos)

        caplog.clear()

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.load()

        # Log should include file size info
        log_messages = [r.getMessage() for r in caplog.records]
        has_size = any(
            any(keyword in msg.lower() for keyword in ["size", "bytes", "b"])
            for msg in log_messages
        )
        assert has_size, f"Expected file size info in log messages, got: {log_messages}"
