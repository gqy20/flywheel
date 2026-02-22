"""Tests for debug logging in storage operations (Issue #5230).

This test suite verifies that storage operations emit debug logs when enabled
via the TODO_DEBUG environment variable.
"""

from __future__ import annotations

import json
import logging
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestStorageDebugLogging:
    """Test debug logging for storage operations."""

    def test_load_emits_debug_log_with_file_path_and_count(self, tmp_path, caplog):
        """When TODO_DEBUG=1, load() should emit DEBUG log with file path and item count."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create and save some todos
        todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2")]
        storage.save(todos)

        # Load with debug logging enabled
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        # Verify the todos were loaded
        assert len(loaded) == 2

        # Verify debug log was emitted
        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        load_logs = [msg for msg in debug_messages if "load" in msg.lower() and str(db) in msg]

        assert len(load_logs) >= 1, f"Expected load log with path {db}. Got logs: {debug_messages}"
        # Should include item count
        assert any("2" in msg or "count" in msg.lower() for msg in load_logs), (
            f"Expected load log to include item count. Got: {load_logs}"
        )

    def test_save_emits_debug_log_with_file_path_and_count(self, tmp_path, caplog):
        """When TODO_DEBUG=1, save() should emit DEBUG log with file path and item count."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2"), Todo(id=3, text="task 3")]

        # Save with debug logging enabled
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # Verify debug log was emitted
        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        save_logs = [msg for msg in debug_messages if "save" in msg.lower() and str(db) in msg]

        assert len(save_logs) >= 1, f"Expected save log with path {db}. Got logs: {debug_messages}"
        # Should include item count
        assert any("3" in msg or "count" in msg.lower() for msg in save_logs), (
            f"Expected save log to include item count. Got: {save_logs}"
        )

    def test_load_emits_error_log_on_json_decode_error(self, tmp_path, caplog):
        """When JSON decoding fails, load() should emit ERROR log with context."""
        db = tmp_path / "malformed.json"
        db.write_text("{ invalid json", encoding="utf-8")
        storage = TodoStorage(str(db))

        with (
            caplog.at_level(logging.ERROR, logger="flywheel.storage"),
            pytest.raises(ValueError, match="Invalid JSON"),
        ):
            storage.load()

        # Verify error log was emitted
        error_messages = [r.message for r in caplog.records if r.levelno == logging.ERROR]
        error_logs = [
            msg for msg in error_messages if "load" in msg.lower() or "json" in msg.lower()
        ]

        assert len(error_logs) >= 1, (
            f"Expected error log for JSON decode failure. Got: {error_messages}"
        )

    def test_load_emits_error_log_on_file_too_large(self, tmp_path, caplog):
        """When file is too large, load() should emit ERROR log with context."""
        db = tmp_path / "large.json"
        # Create a file larger than 10MB (need ~100k items with small objects)
        large_payload = [{"id": i, "text": "x" * 100} for i in range(105000)]
        db.write_text(json.dumps(large_payload), encoding="utf-8")

        # Verify file is actually larger than 10MB
        assert db.stat().st_size > 10 * 1024 * 1024, "Test file should be larger than 10MB"

        storage = TodoStorage(str(db))

        with (
            caplog.at_level(logging.ERROR, logger="flywheel.storage"),
            pytest.raises(ValueError, match="too large"),
        ):
            storage.load()

        # Verify error log was emitted
        error_messages = [r.message for r in caplog.records if r.levelno == logging.ERROR]
        error_logs = [
            msg for msg in error_messages if "large" in msg.lower() or "size" in msg.lower()
        ]

        assert len(error_logs) >= 1, f"Expected error log for oversized file. Got: {error_messages}"

    def test_save_emits_error_log_on_write_failure(self, tmp_path, caplog):
        """When save fails due to OSError, ERROR log should be emitted."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        # Mock os.replace to fail
        import os as os_module

        with (
            caplog.at_level(logging.ERROR, logger="flywheel.storage"),
            patch.object(os_module, "replace", side_effect=OSError("Disk full")),
            pytest.raises(OSError, match="Disk full"),
        ):
            storage.save([Todo(id=2, text="new")])

        # Verify error log was emitted
        error_messages = [r.message for r in caplog.records if r.levelno == logging.ERROR]
        error_logs = [
            msg for msg in error_messages if "save" in msg.lower() or "write" in msg.lower()
        ]

        assert len(error_logs) >= 1, f"Expected error log for save failure. Got: {error_messages}"

    def test_load_empty_file_returns_empty_list_with_debug_log(self, tmp_path, caplog):
        """Loading from non-existent file should emit debug log and return empty list."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        assert loaded == []

        # Verify debug log was emitted for non-existent file
        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        load_logs = [
            msg
            for msg in debug_messages
            if "load" in msg.lower() or "not found" in msg.lower() or "empty" in msg.lower()
        ]

        assert len(load_logs) >= 1, (
            f"Expected debug log for non-existent file. Got: {debug_messages}"
        )
