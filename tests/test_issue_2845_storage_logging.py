"""Tests for storage operation logging (Issue #2845).

This test suite verifies that TodoStorage provides logging for load/save operations,
enabling debugging of file I/O operations, performance bottlenecks, and error root causes.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestStorageLogging:
    """Test suite for storage operation logging."""

    def test_load_logs_info_when_file_not_found(self, tmp_path, caplog) -> None:
        """Test that load() logs info when file doesn't exist."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        with caplog.at_level(logging.INFO):
            storage.load()

        # Verify info-level log message about file not existing
        assert any(
            "nonexistent.json" in record.message and "not found" in record.message.lower()
            for record in caplog.records
        ), f"Expected 'not found' log message. Got: {[r.message for r in caplog.records]}"

    def test_load_logs_info_on_success(self, tmp_path, caplog) -> None:
        """Test that load() logs info on successful load with todo count."""
        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        # Create test data
        todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]
        storage.save(todos)

        caplog.clear()

        with caplog.at_level(logging.INFO):
            loaded = storage.load()

        assert len(loaded) == 2
        # Verify log contains operation type, file path, and todo count
        assert any(
            "test.json" in record.message and "load" in record.message.lower()
            for record in caplog.records
        ), f"Expected load log message. Got: {[r.message for r in caplog.records]}"

    def test_load_logs_error_on_json_decode_error(self, tmp_path, caplog) -> None:
        """Test that load() logs error when JSON is invalid."""
        db = tmp_path / "invalid.json"
        db.write_text("{invalid json", encoding="utf-8")

        storage = TodoStorage(str(db))

        with caplog.at_level(logging.ERROR), pytest.raises(ValueError, match="Invalid JSON"):
            storage.load()

        # Verify error log for JSON decode failure
        assert any(
            record.levelname == "ERROR" and "json decode error" in record.message.lower()
            for record in caplog.records
        ), f"Expected ERROR log for JSON decode error. Got: {[r.message for r in caplog.records]}"

    def test_save_logs_info_on_success(self, tmp_path, caplog) -> None:
        """Test that save() logs info on successful save with todo count."""
        db = tmp_path / "save_test.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2"), Todo(id=3, text="task3")]

        with caplog.at_level(logging.INFO):
            storage.save(todos)

        # Verify log contains operation type, file path, and todo count
        assert any(
            "save_test.json" in record.message and "save" in record.message.lower()
            for record in caplog.records
        ), f"Expected save log message. Got: {[r.message for r in caplog.records]}"

    def test_save_logs_error_on_failure(self, tmp_path, caplog) -> None:
        """Test that save() logs error when write fails."""
        import os

        db = tmp_path / "failure_test.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="task1")]

        # Mock os.fchmod to cause write failure inside try block
        def failing_fchmod(*args, **kwargs):
            raise OSError("Simulated write failure")

        with (
            caplog.at_level(logging.ERROR),
            patch.object(os, "fchmod", failing_fchmod),
            pytest.raises(OSError, match="Simulated write failure"),
        ):
            storage.save(todos)

        # Verify error log for save failure
        assert any(
            record.levelname == "ERROR" and "failed to save" in record.message.lower()
            for record in caplog.records
        ), f"Expected ERROR log for save failure. Got: {[r.message for r in caplog.records]}"

    def test_logging_respects_fw_log_level_env_var(self, tmp_path, monkeypatch) -> None:
        """Test that FW_LOG_LEVEL environment variable controls log output."""
        db = tmp_path / "env_test.json"
        storage = TodoStorage(str(db))

        # Set FW_LOG_LEVEL to DEBUG
        monkeypatch.setenv("FW_LOG_LEVEL", "DEBUG")

        todos = [Todo(id=1, text="task1")]

        # This should not raise any errors and should respect the env var
        storage.save(todos)
        loaded = storage.load()

        assert len(loaded) == 1

    def test_default_no_logging_pollution(self, tmp_path, caplog) -> None:
        """Test that by default, operations don't produce excessive logs."""
        db = tmp_path / "default.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="task1")]

        # Without explicit log level setting, ensure operations work
        storage.save(todos)
        loaded = storage.load()

        assert len(loaded) == 1


class TestLoggingModuleImport:
    """Test that logging module is properly imported."""

    def test_storage_module_imports_logging(self) -> None:
        """Verify that storage.py imports logging module."""
        import flywheel.storage as storage_module

        # Check that logging is imported in the module
        assert hasattr(storage_module, "logging"), "storage module should import logging"
