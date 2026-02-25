"""Tests for optional logging support in TodoStorage.

This test suite verifies that TodoStorage supports optional debug logging
for load/save operations, as requested in issue #5669.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestStorageLogging:
    """Tests for optional logging in TodoStorage."""

    def test_verbose_false_produces_no_logs(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that verbose=False produces no debug logs."""
        caplog.set_level(logging.DEBUG)

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), verbose=False)

        todos = [Todo(id=1, text="test task")]
        storage.save(todos)
        loaded = storage.load()

        # No debug logs should be produced when verbose=False
        assert len(caplog.records) == 0
        assert len(loaded) == 1

    def test_verbose_true_logs_load_operation(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that verbose=True logs load operations with file path and item count."""
        caplog.set_level(logging.DEBUG)

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), verbose=True)

        # Create some todos
        todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2")]
        storage.save(todos)

        # Clear previous logs to focus on load operation
        caplog.clear()

        # Load should produce debug log
        loaded = storage.load()

        assert len(loaded) == 2
        # Should have logged the load operation
        assert len(caplog.records) >= 1
        # Log should contain file path info
        log_messages = [r.getMessage() for r in caplog.records]
        assert any("load" in msg.lower() for msg in log_messages)

    def test_verbose_true_logs_save_operation(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that verbose=True logs save operations with file path."""
        caplog.set_level(logging.DEBUG)

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), verbose=True)

        todos = [Todo(id=1, text="test task")]
        storage.save(todos)

        # Should have logged the save operation
        assert len(caplog.records) >= 1
        log_messages = [r.getMessage() for r in caplog.records]
        assert any("save" in msg.lower() for msg in log_messages)

    def test_verbose_true_logs_file_path(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that logged messages include the file path."""
        caplog.set_level(logging.DEBUG)

        db_path = str(tmp_path / "my_todos.json")
        storage = TodoStorage(db_path, verbose=True)

        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        storage.load()

        log_messages = [r.getMessage() for r in caplog.records]
        # Path should appear in at least one log message
        all_logs = " ".join(log_messages).lower()
        assert "my_todos.json" in all_logs

    def test_verbose_true_logs_item_count_on_load(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that load logs include item count."""
        caplog.set_level(logging.DEBUG)

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), verbose=True)

        # Create 3 todos
        todos = [Todo(id=i, text=f"task {i}") for i in range(1, 4)]
        storage.save(todos)

        caplog.clear()

        loaded = storage.load()
        assert len(loaded) == 3

        # Log should mention the count
        log_messages = [r.getMessage() for r in caplog.records]
        all_logs = " ".join(log_messages)
        # Should include count (3) somewhere
        assert "3" in all_logs

    def test_verbose_defaults_to_false(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that verbose defaults to False (backward compatible)."""
        caplog.set_level(logging.DEBUG)

        db = tmp_path / "todo.json"
        # Create storage without verbose parameter
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        storage.load()

        # No logs should be produced by default
        assert len(caplog.records) == 0

    def test_custom_logger_can_be_injected(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test that a custom logger can be injected."""
        caplog.set_level(logging.DEBUG)

        db = tmp_path / "todo.json"
        custom_logger = logging.getLogger("my_custom_storage_logger")

        storage = TodoStorage(str(db), verbose=True, logger=custom_logger)

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        # Should have logs from the custom logger
        assert len(caplog.records) >= 1
