"""Tests for storage logging support (Issue #5641).

This test suite verifies that TodoStorage provides optional logging support
for debugging and monitoring storage operations when FLYWHEEL_DEBUG=1 is set.
"""

from __future__ import annotations

import logging
import os
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestStorageLogging:
    """Test logging support in TodoStorage."""

    def test_load_logs_debug_when_flywheel_debug_enabled(self, tmp_path, caplog):
        """Test that load() logs DEBUG messages when FLYWHEEL_DEBUG=1."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create some todos
        todos = [Todo(id=1, text="test task")]
        storage.save(todos)

        # Enable debug logging
        with (
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
            patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}),
        ):
            loaded = storage.load()

        assert len(loaded) == 1
        # Should have logged at least one debug message about loading
        debug_messages = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_messages) >= 1
        # Log should mention load operation
        log_messages = [r.message for r in debug_messages]
        assert any("load" in msg.lower() for msg in log_messages)

    def test_save_logs_debug_when_flywheel_debug_enabled(self, tmp_path, caplog):
        """Test that save() logs DEBUG messages when FLYWHEEL_DEBUG=1."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test task"), Todo(id=2, text="another")]

        # Enable debug logging
        with (
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
            patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}),
        ):
            storage.save(todos)

        # Should have logged at least one debug message about saving
        debug_messages = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_messages) >= 1
        # Log should mention save operation
        log_messages = [r.message for r in debug_messages]
        assert any("save" in msg.lower() for msg in log_messages)

    def test_load_logs_file_path_in_debug_message(self, tmp_path, caplog):
        """Test that debug log includes the file path."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        with (
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
            patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}),
        ):
            storage.load()

        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        # Log should include the file path
        assert any(str(db) in msg for msg in debug_messages)

    def test_load_logs_error_on_json_decode_error(self, tmp_path, caplog):
        """Test that load() logs ERROR when JSON is malformed."""
        db = tmp_path / "todo.json"
        db.write_text("{invalid json}", encoding="utf-8")

        storage = TodoStorage(str(db))

        with (
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
            patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}),
            pytest.raises(ValueError, match="Invalid JSON"),
        ):
            storage.load()

        # Should have logged an error
        error_messages = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(error_messages) >= 1

    def test_save_logs_error_on_write_failure(self, tmp_path, caplog):
        """Test that save() logs ERROR when write fails."""
        # Create a directory where we can't write
        unwritable_dir = tmp_path / "unwritable"
        unwritable_dir.mkdir()
        db = unwritable_dir / "todo.json"

        storage = TodoStorage(str(db))
        todos = [Todo(id=1, text="test")]

        # Make directory read-only after creating storage
        unwritable_dir.chmod(0o500)

        try:
            with (
                caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
                patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}),
                pytest.raises(OSError),
            ):
                storage.save(todos)

            # Should have logged an error
            error_messages = [r for r in caplog.records if r.levelno == logging.ERROR]
            assert len(error_messages) >= 1
        finally:
            # Restore permissions for cleanup
            unwritable_dir.chmod(0o755)

    def test_no_logging_when_flywheel_debug_not_set(self, tmp_path, caplog):
        """Test that no debug logs are emitted when FLYWHEEL_DEBUG is not set."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        # Clear any previous logs
        caplog.clear()

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            # Ensure FLYWHEEL_DEBUG is not set
            env = os.environ.copy()
            env.pop("FLYWHEEL_DEBUG", None)
            with patch.dict(os.environ, env, clear=True):
                storage.load()

        # Should NOT have any debug messages
        debug_messages = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_messages) == 0

    def test_load_includes_todos_count_in_debug_log(self, tmp_path, caplog):
        """Test that debug log includes the count of loaded todos."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=i, text=f"task {i}") for i in range(1, 6)]
        storage.save(todos)

        with (
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
            patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}),
        ):
            storage.load()

        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        # Log should mention the count
        assert any("5" in msg for msg in debug_messages)

    def test_save_includes_todos_count_in_debug_log(self, tmp_path, caplog):
        """Test that debug log includes the count of saved todos."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=i, text=f"task {i}") for i in range(1, 4)]

        with (
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
            patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}),
        ):
            storage.save(todos)

        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        # Log should mention the count
        assert any("3" in msg for msg in debug_messages)
