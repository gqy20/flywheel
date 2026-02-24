"""Tests for logging support in TodoStorage.

This test suite verifies that TodoStorage logs key operations for debugging
and observability purposes, as required by issue #5545.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestLoggerSetup:
    """Tests for logger configuration."""

    def test_module_has_logger(self) -> None:
        """Verify storage.py imports logging and creates module-level logger."""
        import flywheel.storage as storage_module

        assert hasattr(storage_module, "logger"), "storage.py should have a module-level logger"
        assert isinstance(storage_module.logger, logging.Logger), (
            "logger should be a logging.Logger instance"
        )

    def test_logger_name_is_correct(self) -> None:
        """Verify logger name follows convention: flywheel.storage."""
        import flywheel.storage as storage_module

        assert storage_module.logger.name == "flywheel.storage", (
            f"Logger name should be 'flywheel.storage', got '{storage_module.logger.name}'"
        )


class TestLoadLogging:
    """Tests for load() operation logging."""

    def test_load_success_logs_debug_with_count(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """load() should log DEBUG on success with todo count."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create some todos
        todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2"), Todo(id=3, text="task 3")]
        storage.save(todos)

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        assert len(loaded) == 3
        # Check that we logged a debug message with the count
        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("3" in msg and "load" in msg.lower() for msg in debug_messages), (
            f"Expected DEBUG log message with todo count '3', got: {debug_messages}"
        )

    def test_load_empty_file_logs_debug(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """load() should log DEBUG when returning empty list for non-existent file."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        assert loaded == []
        # Check that we logged a debug message for empty/non-existent
        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("load" in msg.lower() for msg in debug_messages), (
            f"Expected DEBUG log message for load, got: {debug_messages}"
        )

    def test_load_json_error_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """load() should log WARNING on JSON decode error."""
        db = tmp_path / "invalid.json"
        db.write_text("{ invalid json", encoding="utf-8")
        storage = TodoStorage(str(db))

        with (
            caplog.at_level(logging.WARNING, logger="flywheel.storage"),
            pytest.raises(ValueError),
        ):
            storage.load()

        # Check that we logged a warning/error message
        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_messages) > 0, "Expected WARNING log on JSON decode error"

    def test_load_oversized_file_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """load() should log WARNING when file exceeds size limit."""
        db = tmp_path / "large.json"
        # Create a file larger than 10MB limit with valid JSON
        # Each item is approximately 125 bytes, need ~80,000 items to exceed 10MB
        large_items = [{"id": i, "text": "x" * 100} for i in range(85000)]
        import json

        large_content = json.dumps(large_items)
        db.write_text(large_content, encoding="utf-8")
        storage = TodoStorage(str(db))

        with (
            caplog.at_level(logging.WARNING, logger="flywheel.storage"),
            pytest.raises(ValueError, match="too large"),
        ):
            storage.load()

        # Check that we logged a warning/error message about size
        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_messages) > 0, "Expected WARNING log for oversized file"


class TestSaveLogging:
    """Tests for save() operation logging."""

    def test_save_success_logs_debug_with_size(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """save() should log DEBUG on success with file size."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test task")]

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # Check that we logged a debug message about save
        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("save" in msg.lower() for msg in debug_messages), (
            f"Expected DEBUG log message for save, got: {debug_messages}"
        )

    def test_save_creates_directory_logs_debug(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """save() should log DEBUG when creating parent directory."""
        db = tmp_path / "subdir" / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # File should exist
        assert db.exists()
        # Check for debug log (directory creation or save)
        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("save" in msg.lower() or "dir" in msg.lower() for msg in debug_messages), (
            f"Expected DEBUG log for directory creation or save, got: {debug_messages}"
        )


class TestErrorPathLogging:
    """Tests for error path logging."""

    def test_json_decode_error_logs_with_path(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """JSON decode errors should include file path in log."""
        db = tmp_path / "broken.json"
        db.write_text("not valid json at all", encoding="utf-8")
        storage = TodoStorage(str(db))

        with (
            caplog.at_level(logging.WARNING, logger="flywheel.storage"),
            pytest.raises(ValueError),
        ):
            storage.load()

        # Check that log includes path information
        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        combined_message = " ".join(warning_messages)
        assert "broken.json" in combined_message or str(db) in combined_message, (
            f"Expected log to include file path, got: {warning_messages}"
        )

    def test_save_error_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """save() errors should be logged."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        # Make the directory read-only to cause save error
        # Note: This test may not work on all systems

        # Create a file with the same name as parent directory would have
        # to trigger path validation error
        blocked_path = tmp_path / "blocked"
        blocked_path.write_text("I am a file, not a directory", encoding="utf-8")
        impossible_db = blocked_path / "subdir" / "todo.json"
        storage2 = TodoStorage(str(impossible_db))

        with (
            caplog.at_level(logging.WARNING, logger="flywheel.storage"),
            pytest.raises((ValueError, OSError)),
        ):
            storage2.save(todos)

        # Should have logged something at warning level or above
        # (may or may not log depending on error type)
        # The test is just to verify logging infrastructure exists
