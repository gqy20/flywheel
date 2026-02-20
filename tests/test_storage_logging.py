"""Tests for debug logging support in TodoStorage.

This test suite verifies that TodoStorage emits DEBUG level logs for
load/save operations, including file path, operation type, and data count.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class LogCapture(logging.Handler):
    """Custom log handler to capture log records for testing."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def get_messages(self) -> list[str]:
        return [self.format(record) for record in self.records]

    def get_debug_messages(self) -> list[str]:
        return [
            self.format(record)
            for record in self.records
            if record.levelno == logging.DEBUG
        ]


@pytest.fixture
def log_capture() -> LogCapture:
    """Fixture to capture log messages from flywheel.storage logger."""
    handler = LogCapture()
    logger = logging.getLogger("flywheel.storage")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield handler
    logger.removeHandler(handler)


class TestStorageLogging:
    """Test debug logging in storage operations."""

    def test_load_emits_debug_log_with_path_and_count(
        self, tmp_path: Path, log_capture: LogCapture
    ) -> None:
        """Test that load operation emits DEBUG log with file path and data count."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a todo file with 3 items
        todos = [
            Todo(id=1, text="task 1"),
            Todo(id=2, text="task 2"),
            Todo(id=3, text="task 3"),
        ]
        storage.save(todos)

        # Clear any previous logs from save
        log_capture.records.clear()

        # Load the todos
        loaded = storage.load()

        # Verify load worked
        assert len(loaded) == 3

        # Verify debug log was emitted
        debug_messages = log_capture.get_debug_messages()
        assert len(debug_messages) >= 1, "Expected at least one DEBUG log from load"

        # Verify log contains key information
        log_message = debug_messages[0]
        assert "load" in log_message.lower(), f"Log should mention 'load': {log_message}"
        assert str(db) in log_message or "todo.json" in log_message, \
            f"Log should contain file path: {log_message}"
        assert "3" in log_message, f"Log should contain data count '3': {log_message}"

    def test_save_emits_debug_log_with_path_and_count(
        self, tmp_path: Path, log_capture: LogCapture
    ) -> None:
        """Test that save operation emits DEBUG log with file path and data count."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="task 1"),
            Todo(id=2, text="task 2"),
        ]
        storage.save(todos)

        # Verify debug log was emitted
        debug_messages = log_capture.get_debug_messages()
        assert len(debug_messages) >= 1, "Expected at least one DEBUG log from save"

        # Verify log contains key information
        log_message = debug_messages[0]
        assert "save" in log_message.lower(), f"Log should mention 'save': {log_message}"
        assert str(db) in log_message or "todo.json" in log_message, \
            f"Log should contain file path: {log_message}"
        assert "2" in log_message, f"Log should contain data count '2': {log_message}"

    def test_default_no_debug_output_without_configuration(
        self, tmp_path: Path
    ) -> None:
        """Test that by default (WARNING level), no debug logs are emitted."""
        # Use a fresh handler without setting DEBUG level
        handler = LogCapture()
        logger = logging.getLogger("flywheel.storage")
        logger.addHandler(handler)
        # Do NOT set level to DEBUG - use default WARNING level
        original_level = logger.level
        logger.setLevel(logging.WARNING)  # Explicitly set to WARNING (default)

        try:
            db = tmp_path / "todo.json"
            storage = TodoStorage(str(db))

            todos = [Todo(id=1, text="task 1")]
            storage.save(todos)
            loaded = storage.load()

            # Verify operations worked
            assert len(loaded) == 1

            # Verify no debug messages were emitted
            debug_messages = handler.get_debug_messages()
            assert len(debug_messages) == 0, \
                f"Expected no DEBUG logs at WARNING level, got: {debug_messages}"
        finally:
            logger.removeHandler(handler)
            logger.setLevel(original_level)

    def test_load_empty_file_emits_debug_log_with_zero_count(
        self, tmp_path: Path, log_capture: LogCapture
    ) -> None:
        """Test that loading an empty (non-existent) file logs with count 0."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Load from non-existent file
        loaded = storage.load()

        # Should return empty list
        assert len(loaded) == 0

        # Verify debug log was emitted
        debug_messages = log_capture.get_debug_messages()
        assert len(debug_messages) >= 1, "Expected at least one DEBUG log from load"

        # Verify log contains path and count 0
        log_message = debug_messages[0]
        assert "load" in log_message.lower(), f"Log should mention 'load': {log_message}"
        assert "0" in log_message, f"Log should contain count '0': {log_message}"
