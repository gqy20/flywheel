"""Tests for debug logging in storage operations (Issue #5230).

This test suite verifies that storage operations emit debug logs when
TODO_DEBUG environment variable is set.
"""

from __future__ import annotations

import logging

import pytest

from flywheel.todo import Todo


@pytest.fixture
def debug_env(monkeypatch):
    """Enable debug logging via TODO_DEBUG=1 and clear cached logger."""
    import importlib

    monkeypatch.setenv("TODO_DEBUG", "1")
    # Clear cached logger handlers before module reload
    logging.getLogger("flywheel.storage").handlers.clear()
    # Force module reload to pick up new env var
    import flywheel.storage

    importlib.reload(flywheel.storage)
    yield
    # Cleanup: clear handlers and reload without debug
    logging.getLogger("flywheel.storage").handlers.clear()
    monkeypatch.delenv("TODO_DEBUG", raising=False)


@pytest.fixture
def no_debug_env(monkeypatch):
    """Ensure debug logging is disabled and clear cached logger."""
    import importlib

    monkeypatch.delenv("TODO_DEBUG", raising=False)
    # Clear cached logger handlers before module reload
    logging.getLogger("flywheel.storage").handlers.clear()
    # Force module reload to pick up new env var
    import flywheel.storage

    importlib.reload(flywheel.storage)
    yield


class TestStorageDebugLogging:
    """Tests for debug logging in storage operations."""

    def test_load_emits_debug_log_with_file_path(self, tmp_path, debug_env, capsys):
        """Test that load() emits DEBUG log with file path when TODO_DEBUG=1."""
        from flywheel.storage import TodoStorage

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create some test data
        todos = [Todo(id=1, text="test item")]
        storage.save(todos)

        # Clear any previous captured output
        capsys.readouterr()

        # Load should emit debug log
        loaded = storage.load()

        assert len(loaded) == 1

        # Check stderr for debug log output
        captured = capsys.readouterr()
        assert "flywheel.storage" in captured.err
        assert "DEBUG" in captured.err
        assert str(db) in captured.err

    def test_load_emits_debug_log_with_item_count(self, tmp_path, debug_env, capsys):
        """Test that load() emits DEBUG log with item count when TODO_DEBUG=1."""
        from flywheel.storage import TodoStorage

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create multiple items
        todos = [Todo(id=1, text="item 1"), Todo(id=2, text="item 2"), Todo(id=3, text="item 3")]
        storage.save(todos)

        capsys.readouterr()

        storage.load()

        # Check stderr for debug log with item count
        captured = capsys.readouterr()
        assert "flywheel.storage" in captured.err
        assert "DEBUG" in captured.err
        assert "3" in captured.err

    def test_save_emits_debug_log_with_file_path(self, tmp_path, debug_env, capsys):
        """Test that save() emits DEBUG log with file path when TODO_DEBUG=1."""
        from flywheel.storage import TodoStorage

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]

        capsys.readouterr()

        storage.save(todos)

        # Check stderr for debug log output
        captured = capsys.readouterr()
        assert "flywheel.storage" in captured.err
        assert "DEBUG" in captured.err
        assert str(db) in captured.err

    def test_save_emits_debug_log_with_item_count(self, tmp_path, debug_env, capsys):
        """Test that save() emits DEBUG log with item count when TODO_DEBUG=1."""
        from flywheel.storage import TodoStorage

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=i, text=f"item {i}") for i in range(1, 6)]

        capsys.readouterr()

        storage.save(todos)

        # Check stderr for debug log with item count
        captured = capsys.readouterr()
        assert "flywheel.storage" in captured.err
        assert "DEBUG" in captured.err
        assert "5" in captured.err

    def test_no_logging_when_debug_disabled(self, tmp_path, no_debug_env, capsys):
        """Test that no debug logs are output when TODO_DEBUG is not set.

        When TODO_DEBUG is not set, NullHandler is used and propagate=False,
        so logs are not output to stderr.
        """
        from flywheel.storage import TodoStorage

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        capsys.readouterr()

        storage.load()
        storage.save(todos)

        # When TODO_DEBUG is not set, NullHandler is used - no stderr output
        captured = capsys.readouterr()
        assert "flywheel.storage" not in captured.err
        assert "DEBUG" not in captured.err

    def test_load_file_not_found_emits_debug_log(self, tmp_path, debug_env, capsys):
        """Test that load() emits DEBUG log when file does not exist."""
        from flywheel.storage import TodoStorage

        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        capsys.readouterr()

        result = storage.load()

        # Returns empty list for missing file
        assert result == []

        # Check that debug log was emitted
        captured = capsys.readouterr()
        assert "flywheel.storage" in captured.err
        assert "DEBUG" in captured.err

    def test_load_malformed_json_emits_error_log(self, tmp_path, debug_env, capsys):
        """Test that load() emits ERROR log for malformed JSON."""
        from flywheel.storage import TodoStorage

        db = tmp_path / "todo.json"
        db.write_text("{ invalid json }", encoding="utf-8")
        storage = TodoStorage(str(db))

        capsys.readouterr()

        with pytest.raises(ValueError, match="Invalid JSON"):
            storage.load()

        # Check that error log was emitted
        captured = capsys.readouterr()
        assert "flywheel.storage" in captured.err
        assert "ERROR" in captured.err

    def test_save_permission_error_emits_error_log(self, tmp_path, debug_env, capsys):
        """Test that save() emits ERROR log when permission denied during write.

        Note: We test the error logging path by simulating a write failure.
        The try/except in save() catches OSError during write and logs it.
        """
        from unittest.mock import patch

        from flywheel.storage import TodoStorage

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a valid file first
        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        capsys.readouterr()

        # Mock os.fdopen to raise OSError during write
        with patch("flywheel.storage.os.fdopen") as mock_fdopen:
            mock_fdopen.side_effect = OSError("Permission denied")

            with pytest.raises(OSError):
                storage.save(todos)

        # Check that error log was emitted for the write failure
        captured = capsys.readouterr()
        # Debug log should be present
        assert "flywheel.storage" in captured.err
        assert "DEBUG" in captured.err
        # Error log should also be present
        assert "ERROR" in captured.err

    def test_get_logger_returns_null_handler_when_disabled(self, no_debug_env):
        """Test that _get_logger returns a logger with NullHandler when disabled."""
        from flywheel.storage import _get_logger

        logger = _get_logger()
        # When disabled, should not have any non-NullHandler handlers
        non_null_handlers = [
            h for h in logger.handlers
            if not isinstance(h, logging.NullHandler)
        ]
        assert len(non_null_handlers) == 0

    def test_get_logger_returns_configured_logger_when_enabled(self, debug_env):
        """Test that _get_logger returns a properly configured logger when enabled."""
        from flywheel.storage import _get_logger

        logger = _get_logger()
        assert logger.name == "flywheel.storage"
        assert logger.level == logging.DEBUG
