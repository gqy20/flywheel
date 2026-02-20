"""Tests for optional logging in storage operations (Issue #4681).

This test suite verifies that TodoStorage can optionally log debug information
when FLYWHEEL_DEBUG=1 is set, helping diagnose data issues in production.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestOptionalLogging:
    """Test optional debug logging for storage operations."""

    def test_no_logging_by_default(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that no debug logs are emitted when FLYWHEEL_DEBUG is not set."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Ensure FLYWHEEL_DEBUG is not set
        with patch.dict(os.environ, {}, clear=True), caplog.at_level(logging.DEBUG):
            # Remove FLYWHEEL_DEBUG if present
            os.environ.pop("FLYWHEEL_DEBUG", None)

            # Perform load (file doesn't exist, returns empty list)
            todos = storage.load()
            assert todos == []

            # Perform save
            storage.save([Todo(id=1, text="test")])

        # No debug logs should have been emitted
        assert len([r for r in caplog.records if r.levelname == "DEBUG"]) == 0

    def test_logging_enabled_with_flywheel_debug_1(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that debug logs are emitted when FLYWHEEL_DEBUG=1."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        with patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}), caplog.at_level(logging.DEBUG):
            # Perform save
            storage.save([Todo(id=1, text="test todo")])

        # Should have debug logs
        debug_logs = [r for r in caplog.records if r.levelname == "DEBUG"]
        assert len(debug_logs) > 0

        # Log should contain file path
        log_messages = [r.message for r in debug_logs]
        assert any(str(db) in msg for msg in log_messages), "Log should contain file path"

    def test_logging_includes_operation_type(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that debug logs include operation type (save/load)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        with patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}), caplog.at_level(logging.DEBUG):
            # Perform save
            storage.save([Todo(id=1, text="test")])

        debug_logs = [r for r in caplog.records if r.levelname == "DEBUG"]
        log_messages = [r.message.lower() for r in debug_logs]
        assert any("save" in msg for msg in log_messages), "Log should mention save operation"

    def test_logging_includes_record_count(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that debug logs include the number of records."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        with patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}), caplog.at_level(logging.DEBUG):
            # Save 3 records
            storage.save([
                Todo(id=1, text="first"),
                Todo(id=2, text="second"),
                Todo(id=3, text="third"),
            ])

        debug_logs = [r for r in caplog.records if r.levelname == "DEBUG"]
        log_messages = [r.message for r in debug_logs]
        # Should mention count (3)
        assert any("3" in msg for msg in log_messages), "Log should mention record count"

    def test_logging_includes_duration(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that debug logs include operation duration."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        with patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}), caplog.at_level(logging.DEBUG):
            storage.save([Todo(id=1, text="test")])

        debug_logs = [r for r in caplog.records if r.levelname == "DEBUG"]
        log_messages = [r.message for r in debug_logs]
        # Should mention duration/elapsed/time in some form
        assert any("ms" in msg.lower() or "sec" in msg.lower() or "duration" in msg.lower()
                   for msg in log_messages), "Log should mention duration"

    def test_load_logging_includes_record_count(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that load operation logs include record count."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save some data
        storage.save([
            Todo(id=1, text="first"),
            Todo(id=2, text="second"),
        ])

        with patch.dict(os.environ, {"FLYWHEEL_DEBUG": "1"}), caplog.at_level(logging.DEBUG):
            # Load the data
            todos = storage.load()

        assert len(todos) == 2

        debug_logs = [r for r in caplog.records if r.levelname == "DEBUG"]
        log_messages = [r.message for r in debug_logs]
        # Should mention count (2)
        assert any("2" in msg for msg in log_messages), "Load log should mention record count"

    def test_flywheel_debug_0_disables_logging(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that FLYWHEEL_DEBUG=0 disables logging (same as not set)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        with patch.dict(os.environ, {"FLYWHEEL_DEBUG": "0"}), caplog.at_level(logging.DEBUG):
            storage.save([Todo(id=1, text="test")])
            storage.load()

        # No debug logs should have been emitted
        assert len([r for r in caplog.records if r.levelname == "DEBUG"]) == 0
