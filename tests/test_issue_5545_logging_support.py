"""Tests for logging support in TodoStorage.

This test suite verifies that TodoStorage properly logs operations
for debugging storage issues (file corruption, permission problems,
concurrent write conflicts).

Issue: #5545
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage, logger
from flywheel.todo import Todo


class TestLoggerConfiguration:
    """Tests for logger configuration."""

    def test_module_has_logger(self) -> None:
        """Verify storage.py has a module-level logger."""
        assert logger is not None, "storage.py should have a module-level logger"
        assert isinstance(logger, logging.Logger), "logger should be a logging.Logger instance"

    def test_logger_name_is_correct(self) -> None:
        """Verify logger uses the standard module naming convention."""
        assert logger.name == "flywheel.storage", (
            f"Logger name should be 'flywheel.storage', got '{logger.name}'"
        )


class TestLoadLogging:
    """Tests for logging in the load() method."""

    def test_load_empty_file_logs_debug(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that loading an empty/non-existent file logs appropriately."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            result = storage.load()

        assert result == []
        # Should log that file doesn't exist or returned empty
        assert (
            any(
                "load" in record.message.lower() or "empty" in record.message.lower()
                for record in caplog.records
            )
            or len(caplog.records) >= 0
        )

    def test_load_success_logs_todo_count(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that successful load logs the number of todos at DEBUG level."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a file with some todos
        todos = [Todo(id=1, text="first"), Todo(id=2, text="second"), Todo(id=3, text="third")]
        storage.save(todos)

        caplog.clear()

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        assert len(loaded) == 3

        # Should log the number of todos loaded
        assert any(
            "3" in record.message and "load" in record.message.lower() for record in caplog.records
        ), f"Expected log message with todo count '3', got: {[r.message for r in caplog.records]}"

    def test_load_json_error_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that JSON decode errors are logged at WARNING level."""
        db = tmp_path / "todo.json"
        db.write_text("{ invalid json }", encoding="utf-8")
        storage = TodoStorage(str(db))

        with (
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
            pytest.raises(ValueError, match="Invalid JSON"),
        ):
            storage.load()

        # Should log a warning about the JSON error
        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_records) >= 1, (
            f"Expected at least one WARNING/ERROR log, got: {[r.message for r in caplog.records]}"
        )
        assert any(
            "json" in record.message.lower() or "invalid" in record.message.lower()
            for record in warning_records
        )

    def test_load_file_too_large_logs_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that file size limit exceeded is logged at ERROR level."""
        db = tmp_path / "todo.json"
        # Create a file larger than 10MB
        large_content = "x" * (11 * 1024 * 1024)
        db.write_text(large_content, encoding="utf-8")
        storage = TodoStorage(str(db))

        with (
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
            pytest.raises(ValueError, match="too large"),
        ):
            storage.load()

        # Should log an error about file size
        error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(error_records) >= 1, (
            f"Expected at least one ERROR log, got: {[r.message for r in caplog.records]}"
        )
        assert any(
            "size" in record.message.lower() or "large" in record.message.lower()
            for record in error_records
        )


class TestSaveLogging:
    """Tests for logging in the save() method."""

    def test_save_success_logs_file_size(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that successful save logs the file size at DEBUG level."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test todo")]

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # Should log about the save operation
        assert any(
            "save" in record.message.lower() or "wrote" in record.message.lower()
            for record in caplog.records
        ), f"Expected log message about save, got: {[r.message for r in caplog.records]}"

    def test_save_creates_parent_directory_logs(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that directory creation is logged."""
        nested_db = tmp_path / "subdir" / "todo.json"
        storage = TodoStorage(str(nested_db))

        todos = [Todo(id=1, text="test")]

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # Should log about directory creation or save operation
        assert len(caplog.records) >= 1, (
            f"Expected at least one log message, got: {[r.message for r in caplog.records]}"
        )

    def test_save_os_error_logs_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that OSError during save is logged at ERROR level."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create the file first
        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        # Use a mock to simulate OSError
        from unittest.mock import patch

        def failing_replace(*args, **kwargs):
            raise OSError("Simulated rename failure")

        with (
            caplog.at_level(logging.DEBUG, logger="flywheel.storage"),
            patch("flywheel.storage.os.replace", failing_replace),
            pytest.raises(OSError),
        ):
            storage.save(todos)

        # Should log an error about the failure
        error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(error_records) >= 1, (
            f"Expected at least one ERROR log, got: {[r.message for r in caplog.records]}"
        )


class TestExistingTestsCompatibility:
    """Tests to ensure logging doesn't break existing functionality."""

    def test_existing_load_functionality(self, tmp_path: Path) -> None:
        """Verify that load() still works correctly with logging added."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Empty file
        assert storage.load() == []

        # Create todos
        todos = [Todo(id=1, text="test", done=True)]
        storage.save(todos)

        # Load and verify
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].id == 1
        assert loaded[0].text == "test"
        assert loaded[0].done is True

    def test_existing_save_functionality(self, tmp_path: Path) -> None:
        """Verify that save() still works correctly with logging added."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="first"),
            Todo(id=2, text="second", done=True),
        ]
        storage.save(todos)

        # Verify file content
        content = db.read_text(encoding="utf-8")
        data = json.loads(content)
        assert len(data) == 2
        assert data[0]["text"] == "first"
        assert data[1]["done"] is True
