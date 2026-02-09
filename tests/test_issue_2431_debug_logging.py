"""Tests for debug mode logging support (Issue #2431).

These tests verify that:
1. Debug logs are emitted when FLYWHEEL_DEBUG environment variable is set
2. Warning logs are emitted for error conditions (JSON decode, file size exceeded)
3. No logs are emitted when FLYWHEEL_DEBUG is not set
4. Log messages contain useful information about key operations
"""

from __future__ import annotations

import logging
import os
from unittest.mock import patch

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage
from flywheel.todo import Todo


class TestDebugLogging:
    """Tests for debug logging functionality."""

    def test_no_log_output_when_flywheel_debug_unset(self, tmp_path, caplog) -> None:
        """When FLYWHEEL_DEBUG is not set, no debug logs should be emitted."""
        # Ensure FLYWHEEL_DEBUG is not set
        with patch.dict("os.environ", {}, clear=False):
            # Remove FLYWHEEL_DEBUG if it exists
            os.environ.pop("FLYWHEEL_DEBUG", None)

            db = tmp_path / "todo.json"
            storage = TodoStorage(str(db))

            # Perform operations that would log in debug mode
            with caplog.at_level(logging.DEBUG):
                storage.load()  # File doesn't exist, but shouldn't log
                todos = [Todo(id=1, text="test")]
                storage.save(todos)
                storage.next_id(todos)

            # Should have no log records
            assert len(caplog.records) == 0, "Expected no log output when FLYWHEEL_DEBUG is unset"

    def test_debug_log_output_when_flywheel_debug_set(self, tmp_path, caplog) -> None:
        """When FLYWHEEL_DEBUG is set, debug logs should be emitted."""
        with patch.dict("os.environ", {"FLYWHEEL_DEBUG": "1"}):
            db = tmp_path / "todo.json"
            storage = TodoStorage(str(db))

            # Load from non-existent file
            with caplog.at_level(logging.DEBUG):
                storage.load()

            # Should have debug log about file not existing
            debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
            assert len(debug_records) > 0, "Expected debug log output when FLYWHEEL_DEBUG is set"

            # Check log message contains useful information
            assert any("todo.json" in r.message.lower() for r in debug_records), \
                "Debug log should contain file path"

    def test_debug_log_on_successful_load(self, tmp_path, caplog) -> None:
        """Debug logs should include file size and todo count on successful load."""
        with patch.dict("os.environ", {"FLYWHEEL_DEBUG": "1"}):
            db = tmp_path / "todo.json"
            storage = TodoStorage(str(db))

            # Create initial data
            todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]
            storage.save(todos)

            caplog.clear()

            # Load the data
            with caplog.at_level(logging.DEBUG):
                loaded = storage.load()

            # Should have debug log about successful load
            debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
            assert len(debug_records) > 0, "Expected debug log on successful load"

            # Check log message contains todo count
            assert any(str(len(loaded)) in r.message or "2" in r.message for r in debug_records), \
                "Debug log should contain number of todos loaded"

    def test_debug_log_on_save_operations(self, tmp_path, caplog) -> None:
        """Debug logs should include todo count and atomic rename info on save."""
        with patch.dict("os.environ", {"FLYWHEEL_DEBUG": "1"}):
            db = tmp_path / "todo.json"
            storage = TodoStorage(str(db))

            todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]

            with caplog.at_level(logging.DEBUG):
                storage.save(todos)

            # Should have debug log about save operation
            debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
            assert len(debug_records) > 0, "Expected debug log on save operation"

            # Check log message mentions save/write/atomic operation
            assert any(
                any(word in r.message.lower() for word in ["save", "write", "atomic", "rename"])
                for r in debug_records
            ), "Debug log should mention save operation"

    def test_warning_log_on_json_decode_error(self, tmp_path, caplog) -> None:
        """Warning log should be emitted when JSON decode fails."""
        with patch.dict("os.environ", {"FLYWHEEL_DEBUG": "1"}):
            db = tmp_path / "malformed.json"
            storage = TodoStorage(str(db))

            # Write malformed JSON
            db.write_text('[{"id": 1, "text": "task1"}', encoding="utf-8")

            with (
                caplog.at_level(logging.WARNING),
                pytest.raises(ValueError, match="Invalid JSON"),
            ):
                storage.load()

            # Should have warning log about decode error
            warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
            assert len(warning_records) > 0, "Expected warning log on JSON decode error"

            # Check log message contains file path
            assert any("malformed.json" in r.message or "json" in r.message.lower()
                      for r in warning_records), \
                "Warning log should contain file path or mention JSON"

    def test_warning_log_on_file_size_exceeded(self, tmp_path, caplog) -> None:
        """Warning log should be emitted when file size exceeds limit."""
        with patch.dict("os.environ", {"FLYWHEEL_DEBUG": "1"}):
            db = tmp_path / "large.json"
            storage = TodoStorage(str(db))

            # Write a file larger than limit (use actual bytes)
            large_content = "x" * (_MAX_JSON_SIZE_BYTES + 1)
            db.write_bytes(large_content.encode("utf-8"))

            with (
                caplog.at_level(logging.WARNING),
                pytest.raises(ValueError, match="too large"),
            ):
                storage.load()

            # Should have warning log about file size
            warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
            assert len(warning_records) > 0, "Expected warning log on file size exceeded"

            # Check log message mentions size or limit
            assert any(
                any(word in r.message.lower() for word in ["size", "large", "limit", "mb"])
                for r in warning_records
            ), "Warning log should mention file size issue"

    def test_debug_log_on_next_id(self, tmp_path, caplog) -> None:
        """Debug logs should include computed next ID."""
        with patch.dict("os.environ", {"FLYWHEEL_DEBUG": "1"}):
            db = tmp_path / "todo.json"
            storage = TodoStorage(str(db))

            todos = [Todo(id=1, text="task1"), Todo(id=5, text="task5")]

            with caplog.at_level(logging.DEBUG):
                next_id = storage.next_id(todos)

            # Should have debug log about next ID computation
            debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
            assert len(debug_records) > 0, "Expected debug log on next_id computation"

            # Check log message contains the computed ID (6)
            assert any(str(next_id) in r.message or "6" in r.message
                      for r in debug_records), \
                f"Debug log should contain computed next ID ({next_id})"

    def test_debug_log_on_empty_todo_list_next_id(self, tmp_path, caplog) -> None:
        """Debug logs should show next_id is 1 for empty todo list."""
        with patch.dict("os.environ", {"FLYWHEEL_DEBUG": "1"}):
            db = tmp_path / "todo.json"
            storage = TodoStorage(str(db))

            with caplog.at_level(logging.DEBUG):
                next_id = storage.next_id([])

            assert next_id == 1, "next_id should be 1 for empty list"

            # Should have debug log
            debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
            assert len(debug_records) > 0, "Expected debug log on next_id for empty list"
