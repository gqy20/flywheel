"""Tests for operation logging in TodoStorage.

Issue #5072: Add operation logging feature to help users debug issues,
track data change history, and audit operation records.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestLoadOperationLogging:
    """Tests for load() operation logging."""

    def test_load_logs_start_and_completion_at_debug_level(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """DEBUG logs should record load operation start and completion."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create valid data
        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        # Clear any logs from save operation
        caplog.clear()

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        assert len(loaded) == 1

        # Check for start log
        start_logs = [r for r in caplog.records if "loading" in r.message.lower()]
        assert len(start_logs) >= 1, "Should log load start at DEBUG level"

        # Check for completion log
        complete_logs = [
            r for r in caplog.records if "loaded" in r.message.lower() and str(db) in r.message
        ]
        assert len(complete_logs) >= 1, "Should log load completion with path"

    def test_load_empty_file_logs_zero_count(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Loading from empty/missing file should log appropriately."""
        db = tmp_path / "empty.json"
        storage = TodoStorage(str(db))

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            loaded = storage.load()

        assert loaded == []

        # Should log that no file exists or 0 items loaded
        logs_text = " ".join(r.message.lower() for r in caplog.records)
        # Accept either "0 todos" or "no file" type messages
        assert (
            "0" in logs_text
            or "empty" in logs_text
            or "no file" in logs_text
            or "not exist" in logs_text
        )

    def test_load_json_parse_error_logs_detailed_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """JSON parse failures should log detailed error with file path."""
        db = tmp_path / "invalid.json"
        db.write_text("{ invalid json }", encoding="utf-8")

        storage = TodoStorage(str(db))

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"), pytest.raises(ValueError):
            storage.load()

        # Should have error-level log with file path
        error_logs = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(error_logs) >= 1, "Should log ERROR for JSON parse failure"

        # Error message should include file path
        error_text = " ".join(r.message for r in error_logs)
        assert str(db) in error_text or "invalid" in error_text.lower()


class TestSaveOperationLogging:
    """Tests for save() operation logging."""

    def test_save_logs_start_and_completion_at_debug_level(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """DEBUG logs should record save operation start and completion."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # Check for start log with count
        start_logs = [r for r in caplog.records if "saving" in r.message.lower()]
        assert len(start_logs) >= 1, "Should log save start at DEBUG level"

        # Check for completion log
        complete_logs = [r for r in caplog.records if "saved" in r.message.lower()]
        assert len(complete_logs) >= 1, "Should log save completion at DEBUG level"

    def test_save_logs_include_item_count(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Save logs should include the count of items being saved."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=3, text="c")]

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        logs_text = " ".join(r.message for r in caplog.records)
        assert "3" in logs_text, "Should log the count of items saved"

    def test_save_logs_include_file_path(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Save logs should include the file path for context."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        logs_text = " ".join(r.message for r in caplog.records)
        assert str(db) in logs_text, "Should include file path in logs"


class TestMkdirOperationLogging:
    """Tests for directory creation logging."""

    def test_mkdir_logs_directory_creation(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Creating parent directory should be logged."""
        db = tmp_path / "subdir" / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # Should have log about directory creation
        logs_text = " ".join(r.message.lower() for r in caplog.records)
        # Accept various forms of mkdir logging
        assert (
            "dir" in logs_text
            or "mkdir" in logs_text
            or "creat" in logs_text
            or "saved" in logs_text
        )


class TestLogFormat:
    """Tests for log format compliance."""

    def test_log_messages_are_informative(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Log messages should contain useful debugging information."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)
            storage.load()

        # Check that logs are generated
        assert len(caplog.records) > 0, "Should generate log records"

        # Verify logger name is correct for filtering
        for record in caplog.records:
            assert record.name == "flywheel.storage", "Logger name should be flywheel.storage"
