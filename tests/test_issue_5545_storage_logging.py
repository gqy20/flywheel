"""Tests for issue #5545: Add logging support to storage.py."""

from __future__ import annotations

import json
import logging

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestStorageLogging:
    """Test suite for storage.py logging feature."""

    def test_logger_name_is_module_name(self) -> None:
        """Verify logger is created with module name."""
        # The logger should be named 'flywheel.storage'
        from flywheel import storage

        assert hasattr(storage, "logger")
        assert storage.logger.name == "flywheel.storage"

    def test_load_success_logs_debug_with_todo_count(
        self, tmp_path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """load() success should log DEBUG with todo count."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a JSON file with 3 todos
        todos = [
            Todo(id=1, text="task1"),
            Todo(id=2, text="task2"),
            Todo(id=3, text="task3"),
        ]
        storage.save(todos)

        # Clear any logs from save()
        caplog.clear()

        # Load with DEBUG level
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        assert len(loaded) == 3

        # Should have a DEBUG log mentioning the count
        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("3" in msg and "load" in msg.lower() for msg in debug_messages), (
            f"Expected DEBUG log with '3' and 'load', got: {debug_messages}"
        )

    def test_save_success_logs_debug_with_file_size(
        self, tmp_path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """save() success should log DEBUG with file size."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test todo item")]
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # Should have a DEBUG log mentioning file size or saved
        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("save" in msg.lower() or "written" in msg.lower() for msg in debug_messages), (
            f"Expected DEBUG log with 'save' or 'written', got: {debug_messages}"
        )

    def test_load_json_decode_error_logs_warning(
        self, tmp_path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """load() JSON decode error should log WARNING/ERROR."""
        db = tmp_path / "invalid.json"
        db.write_text("{ invalid json", encoding="utf-8")

        storage = TodoStorage(str(db))

        with (
            caplog.at_level(logging.WARNING, logger="flywheel.storage"),
            pytest.raises(ValueError),
        ):
            storage.load()

        # Should have logged a warning or error
        warning_or_error = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_or_error) > 0, "Expected WARNING/ERROR log for JSON decode error"

    def test_load_oversized_file_logs_warning(
        self, tmp_path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """load() oversized file should log WARNING/ERROR."""
        db = tmp_path / "large.json"
        storage = TodoStorage(str(db))

        # Create a file definitely larger than 10MB (~11MB)
        large_payload = [{"id": i, "text": "x" * 200} for i in range(60000)]
        db.write_text(json.dumps(large_payload), encoding="utf-8")

        # Verify the file is actually larger than 10MB
        assert db.stat().st_size > 10 * 1024 * 1024

        with (
            caplog.at_level(logging.WARNING, logger="flywheel.storage"),
            pytest.raises(ValueError),
        ):
            storage.load()

        # Should have logged a warning or error
        warning_or_error = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_or_error) > 0, "Expected WARNING/ERROR log for oversized file"

    def test_load_missing_file_returns_empty_list(
        self, tmp_path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """load() on missing file returns empty list (no error log needed)."""
        db = tmp_path / "missing.json"
        storage = TodoStorage(str(db))

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        assert loaded == []
        # No specific log assertion - just verify no crash

    def test_save_creates_parent_directory(
        self, tmp_path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """save() creates parent directory if missing."""
        db = tmp_path / "subdir" / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # File should exist
        assert db.exists()
        # Not strictly required, but good to verify
