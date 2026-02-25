"""Tests for optional logging support in storage operations.

This test suite verifies that TodoStorage supports optional logging for debugging
load/save operations, as requested in issue #5669.

Acceptance criteria:
- TodoStorage initialization with optional verbose parameter
- load() operation records debug level logs with file path and item count
- save() operation records debug level logs with file path and atomic write completion
- verbose=False (default) produces no logs
- verbose=True produces expected logs
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestOptionalLogging:
    """Test optional logging support for storage operations."""

    def test_default_verbose_is_false(self, tmp_path: Path) -> None:
        """Test that verbose defaults to False (no logging)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))
        assert storage.verbose is False

    def test_verbose_can_be_set_to_true(self, tmp_path: Path) -> None:
        """Test that verbose can be set to True during initialization."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), verbose=True)
        assert storage.verbose is True

    def test_load_produces_no_logs_when_verbose_false(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that load() produces no logs when verbose=False (default)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        storage.save([Todo(id=1, text="test")])

        # Load with verbose=False (default)
        with caplog.at_level(logging.DEBUG):
            storage.load()

        # Should have no debug logs from flywheel.storage
        storage_logs = [r for r in caplog.records if r.name == "flywheel.storage"]
        assert len(storage_logs) == 0

    def test_save_produces_no_logs_when_verbose_false(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that save() produces no logs when verbose=False (default)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save with verbose=False (default)
        with caplog.at_level(logging.DEBUG):
            storage.save([Todo(id=1, text="test")])

        # Should have no debug logs from flywheel.storage
        storage_logs = [r for r in caplog.records if r.name == "flywheel.storage"]
        assert len(storage_logs) == 0

    def test_load_produces_debug_logs_when_verbose_true(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that load() produces debug logs when verbose=True."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), verbose=True)

        # Create initial data
        storage.save([Todo(id=1, text="test"), Todo(id=2, text="another")])

        # Load with verbose=True
        with caplog.at_level(logging.DEBUG):
            loaded = storage.load()

        # Should have debug log from flywheel.storage
        storage_logs = [r for r in caplog.records if r.name == "flywheel.storage"]
        assert len(storage_logs) >= 1

        # Log should contain file path and item count
        load_logs = [r for r in storage_logs if "load" in r.message.lower()]
        assert len(load_logs) >= 1
        assert str(db) in load_logs[0].message or "todo.json" in load_logs[0].message
        assert "2" in load_logs[0].message  # Item count

    def test_save_produces_debug_logs_when_verbose_true(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that save() produces debug logs when verbose=True."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), verbose=True)

        # Save with verbose=True
        with caplog.at_level(logging.DEBUG):
            storage.save([Todo(id=1, text="test"), Todo(id=2, text="another")])

        # Should have debug log from flywheel.storage
        storage_logs = [r for r in caplog.records if r.name == "flywheel.storage"]
        assert len(storage_logs) >= 1

        # Log should contain file path and mention of save/write
        save_logs = [r for r in storage_logs if "save" in r.message.lower()]
        assert len(save_logs) >= 1
        assert str(db) in save_logs[0].message or "todo.json" in save_logs[0].message

    def test_load_empty_file_logs_zero_items(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that loading an empty/non-existent file logs 0 items."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), verbose=True)

        # Load from non-existent file
        with caplog.at_level(logging.DEBUG):
            loaded = storage.load()

        assert loaded == []

        # Should have debug log with 0 items
        storage_logs = [r for r in caplog.records if r.name == "flywheel.storage"]
        load_logs = [r for r in storage_logs if "load" in r.message.lower()]
        assert len(load_logs) >= 1
        assert "0" in load_logs[0].message  # Item count should be 0

    def test_log_level_is_debug(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that logs are at DEBUG level (not INFO or WARNING)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), verbose=True)

        # Create and load data
        with caplog.at_level(logging.DEBUG):
            storage.save([Todo(id=1, text="test")])
            storage.load()

        # All flywheel.storage logs should be at DEBUG level
        storage_logs = [r for r in caplog.records if r.name == "flywheel.storage"]
        for log_record in storage_logs:
            assert log_record.levelno == logging.DEBUG
