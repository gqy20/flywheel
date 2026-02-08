"""Tests for optional debug logging in storage operations (Issue #2266).

These tests verify that:
1. Default behavior has NO debug log output
2. With FW_LOG=debug, load operation logs file path and count
3. With FW_LOG=debug, save operation logs file path and count
4. Logs include timing information
"""

from __future__ import annotations

import logging
import os
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_default_no_logging_output(tmp_path, caplog) -> None:
    """Default behavior should NOT produce any log output."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Ensure FW_LOG is not set
    env = os.environ.copy()
    env.pop("FW_LOG", None)

    with patch.dict(os.environ, env, clear=True):
        # Reset logging configuration
        logging.getLogger("flywheel.storage").handlers.clear()

        todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]
        storage.save(todos)

        # Should not produce any log records
        assert len(caplog.records) == 0

        loaded = storage.load()
        assert len(loaded) == 2

        # Should not produce any log records
        assert len(caplog.records) == 0


def test_fw_log_debug_enables_logging_on_load(tmp_path, caplog) -> None:
    """With FW_LOG=debug, load operation should log file path and count."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create test data first
    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2"), Todo(id=3, text="task3")]
    storage.save(todos)

    # Set FW_LOG=debug
    env = os.environ.copy()
    env["FW_LOG"] = "debug"

    with patch.dict(os.environ, env, clear=True):
        # Reset and configure logging
        logger = logging.getLogger("flywheel.storage")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.load()

        # Should have produced log records
        assert len(caplog.records) > 0

        # Check that log contains expected information
        log_messages = [record.message for record in caplog.records]
        log_text = " ".join(log_messages)

        # Should mention the operation (load)
        assert any("load" in msg.lower() for msg in log_messages)

        # Should mention the file path
        assert str(db) in log_text or db.name in log_text

        # Should mention the count
        assert "3" in log_text or "three" in log_text.lower()


def test_fw_log_debug_enables_logging_on_save(tmp_path, caplog) -> None:
    """With FW_LOG=debug, save operation should log file path and count."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]

    # Set FW_LOG=debug
    env = os.environ.copy()
    env["FW_LOG"] = "debug"

    with patch.dict(os.environ, env, clear=True):
        # Reset and configure logging
        logger = logging.getLogger("flywheel.storage")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # Should have produced log records
        assert len(caplog.records) > 0

        # Check that log contains expected information
        log_messages = [record.message for record in caplog.records]
        log_text = " ".join(log_messages)

        # Should mention the operation (save)
        assert any("save" in msg.lower() for msg in log_messages)

        # Should mention the file path
        assert str(db) in log_text or db.name in log_text

        # Should mention the count
        assert "2" in log_text or "two" in log_text.lower()


def test_logging_includes_timing_info(tmp_path, caplog) -> None:
    """With FW_LOG=debug, logs should include timing information."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="task1")]

    # Set FW_LOG=debug
    env = os.environ.copy()
    env["FW_LOG"] = "debug"

    with patch.dict(os.environ, env, clear=True):
        # Reset and configure logging
        logger = logging.getLogger("flywheel.storage")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)

        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # Check that log includes timing information
        log_messages = [record.message for record in caplog.records]
        log_text = " ".join(log_messages)

        # Should mention time/ms/timing
        assert any(
            word in log_text.lower()
            for word in ["ms", "millisecond", "second", "time", "took", "elapsed"]
        )


def test_load_empty_file_no_logging_by_default(tmp_path) -> None:
    """Loading non-existent file should not produce visible output by default."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Ensure FW_LOG is not set
    env = os.environ.copy()
    env.pop("FW_LOG", None)

    with patch.dict(os.environ, env, clear=True):
        # Reset logging configuration
        logging.getLogger("flywheel.storage").handlers.clear()

        # Should return empty list without error
        loaded = storage.load()
        assert loaded == []


def test_fw_log_info_level_also_logs(tmp_path, caplog) -> None:
    """With FW_LOG=info, should also produce log output (capturing DEBUG logs)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="task1")]

    # Set FW_LOG=info
    env = os.environ.copy()
    env["FW_LOG"] = "info"

    with patch.dict(os.environ, env, clear=True):
        # Reset and configure logging
        logger = logging.getLogger("flywheel.storage")
        logger.handlers.clear()
        logger.setLevel(logging.INFO)

        # Capture at DEBUG level to see our debug logs
        with caplog.at_level(logging.DEBUG, logger="flywheel.storage"):
            storage.save(todos)

        # Should have produced log records (we log at DEBUG but INFO level handler sees them)
        assert len(caplog.records) > 0
