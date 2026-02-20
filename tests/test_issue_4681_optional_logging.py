"""Tests for optional logging in storage operations (issue #4681).

This test suite verifies that when FLYWHEEL_DEBUG=1 is set, storage operations
log debug information including file path, operation type, record count, and timing.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestOptionalLogging:
    """Test optional logging for storage operations."""

    def test_no_logging_by_default(self, tmp_path, caplog):
        """Test that no debug logging occurs by default (FLYWHEEL_DEBUG not set)."""
        # Ensure FLYWHEEL_DEBUG is not set
        env_backup = os.environ.pop("FLYWHEEL_DEBUG", None)

        try:
            db = tmp_path / "todo.json"
            storage = TodoStorage(str(db))

            with caplog.at_level(logging.DEBUG):
                todos = [Todo(id=1, text="test")]
                storage.save(todos)
                loaded = storage.load()

            # Should have no debug log messages from storage
            debug_logs = [r for r in caplog.records if r.levelno == logging.DEBUG]
            storage_logs = [r for r in debug_logs if "storage" in r.getMessage().lower() or r.name == "flywheel.storage"]
            assert len(storage_logs) == 0
        finally:
            if env_backup is not None:
                os.environ["FLYWHEEL_DEBUG"] = env_backup

    def test_logging_enabled_with_flywheel_debug(self, tmp_path, caplog):
        """Test that debug logging is enabled when FLYWHEEL_DEBUG=1."""
        original = os.environ.get("FLYWHEEL_DEBUG")

        try:
            os.environ["FLYWHEEL_DEBUG"] = "1"

            db = tmp_path / "todo.json"
            storage = TodoStorage(str(db))

            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                todos = [Todo(id=1, text="test todo"), Todo(id=2, text="another")]
                storage.save(todos)
                loaded = storage.load()

            # Should have debug log messages
            assert len(caplog.records) > 0

            # Check that save was logged with path, record count
            save_logs = [r for r in caplog.records if "save" in r.getMessage().lower()]
            assert len(save_logs) > 0, "Expected save operation to be logged"

            # Check that load was logged
            load_logs = [r for r in caplog.records if "load" in r.getMessage().lower()]
            assert len(load_logs) > 0, "Expected load operation to be logged"

        finally:
            if original is None:
                os.environ.pop("FLYWHEEL_DEBUG", None)
            else:
                os.environ["FLYWHEEL_DEBUG"] = original

    def test_save_log_includes_path_and_count(self, tmp_path, caplog):
        """Test that save log includes file path and record count."""
        original = os.environ.get("FLYWHEEL_DEBUG")

        try:
            os.environ["FLYWHEEL_DEBUG"] = "1"

            db = tmp_path / "todo.json"
            storage = TodoStorage(str(db))

            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=3, text="c")]
                storage.save(todos)

            # Find save log
            save_logs = [r for r in caplog.records if "save" in r.getMessage().lower()]
            assert len(save_logs) > 0

            msg = save_logs[0].getMessage()
            # Should contain path info
            assert str(db) in msg or "path" in msg.lower()
            # Should contain count
            assert "3" in msg or "count" in msg.lower()

        finally:
            if original is None:
                os.environ.pop("FLYWHEEL_DEBUG", None)
            else:
                os.environ["FLYWHEEL_DEBUG"] = original

    def test_load_log_includes_path_and_count(self, tmp_path, caplog):
        """Test that load log includes file path and record count."""
        original = os.environ.get("FLYWHEEL_DEBUG")

        try:
            os.environ["FLYWHEEL_DEBUG"] = "1"

            db = tmp_path / "todo.json"
            storage = TodoStorage(str(db))

            # First save some data
            todos = [Todo(id=1, text="test1"), Todo(id=2, text="test2")]
            storage.save(todos)

            caplog.clear()

            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                loaded = storage.load()

            # Find load log
            load_logs = [r for r in caplog.records if "load" in r.getMessage().lower()]
            assert len(load_logs) > 0

            msg = load_logs[0].getMessage()
            # Should contain path info
            assert str(db) in msg or "path" in msg.lower()
            # Should contain count
            assert "2" in msg or "count" in msg.lower()

        finally:
            if original is None:
                os.environ.pop("FLYWHEEL_DEBUG", None)
            else:
                os.environ["FLYWHEEL_DEBUG"] = original

    def test_load_empty_file_logs_zero_records(self, tmp_path, caplog):
        """Test that loading from non-existent file logs 0 records."""
        original = os.environ.get("FLYWHEEL_DEBUG")

        try:
            os.environ["FLYWHEEL_DEBUG"] = "1"

            db = tmp_path / "nonexistent.json"
            storage = TodoStorage(str(db))

            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                loaded = storage.load()

            assert loaded == []

            # Find load log
            load_logs = [r for r in caplog.records if "load" in r.getMessage().lower()]
            assert len(load_logs) > 0

            msg = load_logs[0].getMessage()
            # Should indicate 0 records
            assert "0" in msg or "empty" in msg.lower() or "not exist" in msg.lower()

        finally:
            if original is None:
                os.environ.pop("FLYWHEEL_DEBUG", None)
            else:
                os.environ["FLYWHEEL_DEBUG"] = original

    def test_timing_info_included_in_logs(self, tmp_path, caplog):
        """Test that operation timing is logged when debug is enabled."""
        original = os.environ.get("FLYWHEEL_DEBUG")

        try:
            os.environ["FLYWHEEL_DEBUG"] = "1"

            db = tmp_path / "todo.json"
            storage = TodoStorage(str(db))

            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                todos = [Todo(id=1, text="test")]
                storage.save(todos)
                storage.load()

            # Check for timing info in logs (ms or elapsed time)
            all_logs = [r.getMessage() for r in caplog.records]
            combined = " ".join(all_logs).lower()

            # Should have some timing-related keywords
            has_timing = any(
                kw in combined for kw in ["ms", "elapsed", "time", "duration", "took", "seconds"]
            )
            assert has_timing, f"Expected timing info in logs: {all_logs}"

        finally:
            if original is None:
                os.environ.pop("FLYWHEEL_DEBUG", None)
            else:
                os.environ["FLYWHEEL_DEBUG"] = original

    def test_logging_disabled_when_flywheel_debug_is_zero(self, tmp_path, caplog):
        """Test that logging is disabled when FLYWHEEL_DEBUG=0."""
        original = os.environ.get("FLYWHEEL_DEBUG")

        try:
            os.environ["FLYWHEEL_DEBUG"] = "0"

            db = tmp_path / "todo.json"
            storage = TodoStorage(str(db))

            with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
                todos = [Todo(id=1, text="test")]
                storage.save(todos)
                storage.load()

            # Should have no debug logs from storage
            debug_logs = [r for r in caplog.records if r.levelno == logging.DEBUG]
            assert len(debug_logs) == 0

        finally:
            if original is None:
                os.environ.pop("FLYWHEEL_DEBUG", None)
            else:
                os.environ["FLYWHEEL_DEBUG"] = original
