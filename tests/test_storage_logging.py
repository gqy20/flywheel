"""Tests for operation logging in TodoStorage.

This test suite verifies that TodoStorage properly logs load() and save()
operations at DEBUG level for debugging and auditing purposes.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestStorageLogging:
    """Test logging behavior in TodoStorage."""

    def test_load_logs_debug_on_success(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that load() logs DEBUG message on successful load."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a valid todo file
        todos = [Todo(id=1, text="test todo"), Todo(id=2, text="another todo")]
        storage.save(todos)

        # Clear any previous logs
        caplog.clear()

        # Load should produce a DEBUG log
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        assert len(loaded) == 2

        # Check that a DEBUG log was produced
        debug_logs = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_logs) >= 1, "Expected at least one DEBUG log from load()"

        # Log should contain relevant information
        log_message = debug_logs[0].message
        assert str(db) in log_message or "todo.json" in log_message, \
            f"Log should contain file path, got: {log_message}"
        assert "2" in log_message, f"Log should contain todo count, got: {log_message}"

    def test_save_logs_debug_on_success(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that save() logs DEBUG message on successful save."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test todo"), Todo(id=2, text="another todo")]

        # Save should produce a DEBUG log
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # Check that a DEBUG log was produced
        debug_logs = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_logs) >= 1, "Expected at least one DEBUG log from save()"

        # Log should contain relevant information
        log_message = debug_logs[0].message
        assert str(db) in log_message or "todo.json" in log_message, \
            f"Log should contain file path, got: {log_message}"
        assert "2" in log_message, f"Log should contain todo count, got: {log_message}"

    def test_load_logs_warning_on_invalid_json(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that load() logs WARNING/ERROR on JSON parse failure."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create an invalid JSON file
        db.write_text("{ invalid json }", encoding="utf-8")

        # Load should raise ValueError but also log the error
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"), pytest.raises(ValueError):
            storage.load()

        # Check that an error/warning log was produced
        error_logs = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(error_logs) >= 1, "Expected at least one WARNING/ERROR log on JSON parse failure"

        # Log should mention the error
        log_message = error_logs[0].message
        assert "json" in log_message.lower() or "invalid" in log_message.lower() or "parse" in log_message.lower(), \
            f"Log should mention JSON error, got: {log_message}"

    def test_load_empty_file_returns_empty_list_with_log(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that load() returns empty list when file doesn't exist, with appropriate log."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # File doesn't exist - should return empty list
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        assert loaded == []

        # Should produce a DEBUG log about missing file
        debug_logs = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_logs) >= 1, "Expected DEBUG log when file doesn't exist"

        log_message = debug_logs[0].message
        assert "not exist" in log_message.lower() or "missing" in log_message.lower() or "empty" in log_message.lower() or "no file" in log_message.lower(), \
            f"Log should mention file status, got: {log_message}"
