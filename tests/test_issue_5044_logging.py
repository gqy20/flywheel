"""Tests for issue #5044: Logging functionality for storage operations.

This test suite verifies that TodoStorage supports optional logging
to help diagnose issues when storage operations fail.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestStorageLogging:
    """Tests for logging functionality in TodoStorage."""

    def test_storage_accepts_optional_logger_parameter(self, tmp_path: Path) -> None:
        """Test that TodoStorage constructor accepts an optional logger parameter."""
        db = tmp_path / "todo.json"
        logger = logging.getLogger("test_logger")

        # Should not raise - logger parameter should be accepted
        storage = TodoStorage(str(db), logger=logger)
        assert storage.logger is logger

    def test_storage_without_logger_works_as_before(self, tmp_path: Path) -> None:
        """Test that not passing logger maintains backward compatibility."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Should work without logger
        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"

    def test_load_logs_debug_on_json_decode_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that load() logs DEBUG when JSON decoding fails."""
        db = tmp_path / "todo.json"
        logger = logging.getLogger("test_storage")
        logger.setLevel(logging.DEBUG)

        storage = TodoStorage(str(db), logger=logger)

        # Create invalid JSON file
        db.write_text("{ invalid json", encoding="utf-8")

        with caplog.at_level(logging.DEBUG, logger="test_storage"):
            with pytest.raises(ValueError, match="Invalid JSON"):
                storage.load()

        # Should have logged a debug message about the error
        assert any(
            "JSON" in record.message and record.levelno == logging.DEBUG
            for record in caplog.records
        )

    def test_save_logs_debug_on_os_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that save() logs DEBUG when OS error occurs."""
        db = tmp_path / "todo.json"
        logger = logging.getLogger("test_storage")
        logger.setLevel(logging.DEBUG)

        storage = TodoStorage(str(db), logger=logger)
        todos = [Todo(id=1, text="test")]

        # Mock os.replace to fail
        with (
            patch("flywheel.storage.os.replace", side_effect=OSError("disk full")),
            caplog.at_level(logging.DEBUG, logger="test_storage"),
            pytest.raises(OSError, match="disk full"),
        ):
            storage.save(todos)

        # Should have logged a debug message about the error
        assert any(
            "save" in record.message.lower() and record.levelno == logging.DEBUG
            for record in caplog.records
        )

    def test_no_logging_when_logger_is_none(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that no logging occurs when logger is None."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))  # No logger

        # Create invalid JSON file
        db.write_text("{ invalid json", encoding="utf-8")

        with caplog.at_level(logging.DEBUG):
            with pytest.raises(ValueError, match="Invalid JSON"):
                storage.load()

        # Should not have logged anything
        assert len(caplog.records) == 0

    def test_load_logs_debug_on_file_size_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that load() logs DEBUG when file is too large."""
        db = tmp_path / "todo.json"
        logger = logging.getLogger("test_storage")
        logger.setLevel(logging.DEBUG)

        storage = TodoStorage(str(db), logger=logger)

        # Mock file size to be too large
        with (
            patch.object(
                Path,
                "stat",
                return_value=type("", (), {"st_size": 20 * 1024 * 1024})(),  # 20MB
            ),
            caplog.at_level(logging.DEBUG, logger="test_storage"),
            pytest.raises(ValueError, match="too large"),
        ):
            storage.load()

        # Should have logged a debug message about the error
        assert any(
            ("size" in record.message.lower() or "limit" in record.message.lower())
            and record.levelno == logging.DEBUG
            for record in caplog.records
        )
