"""Tests for optional debug logging in TodoStorage.

This test suite verifies that TodoStorage supports optional debug logging
for load/save operations, which is useful for troubleshooting file operations,
concurrency issues, and permission problems.

Issue: #4751
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestDebugLogging:
    """Tests for debug logging functionality."""

    def test_debug_false_no_logging(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that debug=False produces no log output."""
        caplog.set_level(logging.DEBUG, logger="flywheel.storage")

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), debug=False)

        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)
        loaded = storage.load()

        assert len(loaded) == 1
        # No debug logs should be emitted when debug=False
        assert len(caplog.records) == 0

    def test_debug_true_logs_save_operation(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that debug=True logs save operations with file path and size."""
        caplog.set_level(logging.DEBUG, logger="flywheel.storage")

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), debug=True)

        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        # Should have debug logs
        assert len(caplog.records) > 0

        # Check log contains key information
        log_messages = [r.getMessage() for r in caplog.records]
        save_logs = [m for m in log_messages if "save" in m.lower()]

        assert len(save_logs) > 0, "Expected save operation to be logged"

        # Log should include file path
        all_log_text = " ".join(log_messages)
        assert str(db) in all_log_text or "todo.json" in all_log_text

    def test_debug_true_logs_load_operation(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that debug=True logs load operations with file path and size."""
        caplog.set_level(logging.DEBUG, logger="flywheel.storage")

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), debug=True)

        # First save something to load
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        caplog.clear()

        # Now load
        loaded = storage.load()
        assert len(loaded) == 1

        # Should have debug logs for load
        log_messages = [r.getMessage() for r in caplog.records]
        load_logs = [m for m in log_messages if "load" in m.lower()]

        assert len(load_logs) > 0, "Expected load operation to be logged"

    def test_debug_true_logs_duration(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that debug=True logs operation duration."""
        caplog.set_level(logging.DEBUG, logger="flywheel.storage")

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), debug=True)

        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        # Check log contains duration information
        log_messages = [r.getMessage() for r in caplog.records]
        all_log_text = " ".join(log_messages)

        # Should contain timing information (ms, seconds, or duration keyword)
        has_timing = any(
            keyword in all_log_text.lower()
            for keyword in ["ms", "sec", "duration", "time", "took", "elapsed"]
        )
        assert has_timing, f"Expected timing info in logs: {log_messages}"

    def test_debug_true_logs_file_size(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that debug=True logs file size for load operations."""
        caplog.set_level(logging.DEBUG, logger="flywheel.storage")

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), debug=True)

        # Create a file with some content
        todos = [Todo(id=1, text="test todo with some content")]
        storage.save(todos)

        caplog.clear()

        # Load should log file size
        loaded = storage.load()
        assert len(loaded) == 1

        log_messages = [r.getMessage() for r in caplog.records]
        all_log_text = " ".join(log_messages)

        # Should contain size information
        has_size = any(
            keyword in all_log_text.lower()
            for keyword in ["bytes", "size", "b"]
        )
        assert has_size, f"Expected size info in logs: {log_messages}"

    def test_debug_default_is_false(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that debug defaults to False when not specified."""
        caplog.set_level(logging.DEBUG, logger="flywheel.storage")

        db = tmp_path / "todo.json"
        # Not passing debug parameter - should default to False
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)
        loaded = storage.load()

        assert len(loaded) == 1
        # No debug logs should be emitted by default
        assert len(caplog.records) == 0

    def test_debug_logs_temp_file_path(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that debug=True logs temp file path during save."""
        caplog.set_level(logging.DEBUG, logger="flywheel.storage")

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), debug=True)

        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        log_messages = [r.getMessage() for r in caplog.records]
        all_log_text = " ".join(log_messages)

        # Should mention temp file operations
        has_temp_info = any(
            keyword in all_log_text.lower()
            for keyword in ["temp", "tmp", "mkstemp", ".todo.json"]
        )
        assert has_temp_info, f"Expected temp file info in logs: {log_messages}"
