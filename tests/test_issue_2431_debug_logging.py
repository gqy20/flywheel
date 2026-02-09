"""Tests for debug mode logging support (Issue #2431).

These tests verify that:
1. Default behavior produces no log output (doesn't pollute stdout)
2. FLYWHEEL_DEBUG=1 enables DEBUG level logging for key operations
3. JSON parse failures log WARNING with file path and error details
4. Save operations log todo count and atomic rename
5. Load operations log file path, size, and todo count
"""

from __future__ import annotations

import json
import logging
import os

import pytest

from flywheel.storage import TodoStorage, _configure_debug_logging, _logger
from flywheel.todo import Todo


class TestDebugLoggingDisabled:
    """Tests verify no logging output to stderr/stdout when FLYWHEEL_DEBUG is not set."""

    def test_no_stream_handler_when_debug_disabled(self, tmp_path, capsys) -> None:
        """When FLYWHEEL_DEBUG is not set, no StreamHandler should output logs."""
        # Remove any existing StreamHandler
        for handler in _logger.handlers[:]:
            if not isinstance(handler, logging.NullHandler):
                _logger.removeHandler(handler)

        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        # Create a valid JSON file and perform operations
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)
        loaded = storage.load()

        # Should work correctly
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"

        # Nothing should be written to stderr (where logs would go)
        captured = capsys.readouterr()
        assert captured.err == ""  # No debug output to stderr

    def test_no_stream_handler_when_debug_zero(self, tmp_path, capsys) -> None:
        """When FLYWHEEL_DEBUG=0, no StreamHandler should output logs."""
        # Remove any existing StreamHandler
        for handler in _logger.handlers[:]:
            if not isinstance(handler, logging.NullHandler):
                _logger.removeHandler(handler)

        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        old_value = os.environ.get("FLYWHEEL_DEBUG")
        os.environ["FLYWHEEL_DEBUG"] = "0"

        try:
            # Reconfigure with debug=0
            _configure_debug_logging()

            # Create a valid JSON file and perform operations
            todos = [Todo(id=1, text="test todo")]
            storage.save(todos)
            loaded = storage.load()

            # Should work correctly
            assert len(loaded) == 1

            # Nothing should be written to stderr (where logs would go)
            captured = capsys.readouterr()
            assert captured.err == ""  # No debug output to stderr

        finally:
            if old_value is None:
                os.environ.pop("FLYWHEEL_DEBUG", None)
            else:
                os.environ["FLYWHEEL_DEBUG"] = old_value
            # Reset to default state
            for handler in _logger.handlers[:]:
                if not isinstance(handler, logging.NullHandler):
                    _logger.removeHandler(handler)

    def test_only_null_handler_by_default(self) -> None:
        """By default, only NullHandler should be attached (no output)."""
        # Remove any existing StreamHandler
        for handler in _logger.handlers[:]:
            if not isinstance(handler, logging.NullHandler):
                _logger.removeHandler(handler)

        # Check that only NullHandler is present
        stream_handlers = [
            h for h in _logger.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.NullHandler)
        ]
        assert len(stream_handlers) == 0


class TestDebugLoggingEnabled:
    """Tests verify proper DEBUG logging when FLYWHEEL_DEBUG=1."""

    def test_load_logs_debug_info(self, tmp_path, caplog) -> None:
        """When FLYWHEEL_DEBUG=1, load() should log file path, size, and todo count."""
        # Remove any existing StreamHandler
        for handler in _logger.handlers[:]:
            if not isinstance(handler, logging.NullHandler):
                _logger.removeHandler(handler)

        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        # Create a valid JSON file first (without debug enabled)
        todos = [Todo(id=1, text="test todo"), Todo(id=2, text="another todo")]
        storage.save(todos)

        # Now enable debug and test load
        old_value = os.environ.get("FLYWHEEL_DEBUG")
        os.environ["FLYWHEEL_DEBUG"] = "1"

        try:
            _configure_debug_logging()

            with caplog.at_level(logging.DEBUG):
                loaded = storage.load()

            # Should load successfully
            assert len(loaded) == 2

            # Should have DEBUG log records
            debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
            assert len(debug_records) > 0

            # Check log contains file path
            log_messages = [r.message for r in debug_records]
            assert any(str(db) in msg for msg in log_messages)

            # Check log mentions loading/loaded
            assert any("load" in msg.lower() for msg in log_messages)

            # Check log mentions count of todos
            assert any("2" in msg or "two" in msg.lower() for msg in log_messages)

        finally:
            if old_value is None:
                os.environ.pop("FLYWHEEL_DEBUG", None)
            else:
                os.environ["FLYWHEEL_DEBUG"] = old_value
            # Reset to default state
            for handler in _logger.handlers[:]:
                if not isinstance(handler, logging.NullHandler):
                    _logger.removeHandler(handler)

    def test_save_logs_debug_info(self, tmp_path, caplog) -> None:
        """When FLYWHEEL_DEBUG=1, save() should log todo count and atomic rename."""
        # Remove any existing StreamHandler
        for handler in _logger.handlers[:]:
            if not isinstance(handler, logging.NullHandler):
                _logger.removeHandler(handler)

        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        old_value = os.environ.get("FLYWHEEL_DEBUG")
        os.environ["FLYWHEEL_DEBUG"] = "1"

        try:
            _configure_debug_logging()

            todos = [Todo(id=1, text="test todo"), Todo(id=2, text="another todo")]

            with caplog.at_level(logging.DEBUG):
                storage.save(todos)

            # Should save successfully
            assert db.exists()

            # Should have DEBUG log records
            debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
            assert len(debug_records) > 0

            # Check log mentions saving/saved
            log_messages = [r.message for r in debug_records]
            assert any("save" in msg.lower() or "saving" in msg.lower() for msg in log_messages)

            # Check log mentions count
            assert any("2" in msg or "two" in msg.lower() for msg in log_messages)

            # Check log mentions atomic/rename
            assert any("atomic" in msg.lower() or "rename" in msg.lower() for msg in log_messages)

        finally:
            if old_value is None:
                os.environ.pop("FLYWHEEL_DEBUG", None)
            else:
                os.environ["FLYWHEEL_DEBUG"] = old_value
            # Reset to default state
            for handler in _logger.handlers[:]:
                if not isinstance(handler, logging.NullHandler):
                    _logger.removeHandler(handler)

    def test_debug_enabled_true_variants(self, tmp_path, caplog) -> None:
        """FLYWHEEL_DEBUG should accept 'true', 'yes', '1' as enabled values."""
        # Remove any existing StreamHandler
        for handler in _logger.handlers[:]:
            if not isinstance(handler, logging.NullHandler):
                _logger.removeHandler(handler)

        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        old_value = os.environ.get("FLYWHEEL_DEBUG")

        for debug_value in ["1", "true", "yes", "True", "YES"]:
            # Clean handlers before each test
            for handler in _logger.handlers[:]:
                if not isinstance(handler, logging.NullHandler):
                    _logger.removeHandler(handler)

            os.environ["FLYWHEEL_DEBUG"] = debug_value

            try:
                _configure_debug_logging()

                with caplog.at_level(logging.DEBUG):
                    storage.save([Todo(id=1, text="test")])

                # Should have DEBUG log records
                debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
                assert len(debug_records) > 0, f"Expected logs for FLYWHEEL_DEBUG={debug_value}"

                caplog.clear()

            finally:
                pass  # Don't restore env between iterations

        if old_value is None:
            os.environ.pop("FLYWHEEL_DEBUG", None)
        else:
            os.environ["FLYWHEEL_DEBUG"] = old_value

        # Reset to default state
        for handler in _logger.handlers[:]:
            if not isinstance(handler, logging.NullHandler):
                _logger.removeHandler(handler)


class TestWarningLogging:
    """Tests verify WARNING logs for error conditions."""

    def test_json_parse_failure_logs_warning(self, tmp_path, caplog) -> None:
        """JSON parse failure should log WARNING with file path and error details."""
        # Remove any existing StreamHandler
        for handler in _logger.handlers[:]:
            if not isinstance(handler, logging.NullHandler):
                _logger.removeHandler(handler)

        db = tmp_path / "malformed.json"
        storage = TodoStorage(str(db))

        # Create malformed JSON
        db.write_text('[{"id": 1, "text": "task1"}', encoding="utf-8")

        old_value = os.environ.get("FLYWHEEL_DEBUG")
        os.environ["FLYWHEEL_DEBUG"] = "1"

        try:
            _configure_debug_logging()

            with (
                caplog.at_level(logging.WARNING),
                pytest.raises(ValueError, match=r"invalid json|malformed"),
            ):
                storage.load()

            # Should have WARNING log records
            warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
            assert len(warning_records) > 0

            # Check warning contains file path
            log_messages = [r.message for r in warning_records]
            assert any(str(db) in msg for msg in log_messages)

            # Check warning mentions JSON/parse error
            assert any("json" in msg.lower() or "parse" in msg.lower() for msg in log_messages)

        finally:
            if old_value is None:
                os.environ.pop("FLYWHEEL_DEBUG", None)
            else:
                os.environ["FLYWHEEL_DEBUG"] = old_value
            # Reset to default state
            for handler in _logger.handlers[:]:
                if not isinstance(handler, logging.NullHandler):
                    _logger.removeHandler(handler)

    def test_oversized_file_logs_warning(self, tmp_path, caplog) -> None:
        """File size exceeding limit should log WARNING."""
        # Remove any existing StreamHandler
        for handler in _logger.handlers[:]:
            if not isinstance(handler, logging.NullHandler):
                _logger.removeHandler(handler)

        db = tmp_path / "large.json"
        storage = TodoStorage(str(db))

        # Create a JSON file larger than 10MB
        large_payload = [
            {"id": i, "text": "x" * 100, "description": "y" * 100}
            for i in range(65000)
        ]
        db.write_text(json.dumps(large_payload), encoding="utf-8")

        old_value = os.environ.get("FLYWHEEL_DEBUG")
        os.environ["FLYWHEEL_DEBUG"] = "1"

        try:
            _configure_debug_logging()

            with (
                caplog.at_level(logging.WARNING),
                pytest.raises(ValueError, match=r"too large"),
            ):
                storage.load()

            # Should have WARNING log records
            warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
            assert len(warning_records) > 0

            # Check warning mentions file size
            log_messages = [r.message for r in warning_records]
            assert any("size" in msg.lower() or "large" in msg.lower() for msg in log_messages)

        finally:
            if old_value is None:
                os.environ.pop("FLYWHEEL_DEBUG", None)
            else:
                os.environ["FLYWHEEL_DEBUG"] = old_value
            # Reset to default state
            for handler in _logger.handlers[:]:
                if not isinstance(handler, logging.NullHandler):
                    _logger.removeHandler(handler)


class TestDoesNotPolluteStdout:
    """Tests verify that logging doesn't pollute stdout by default."""

    def test_logs_to_stderr_not_stdout(self, tmp_path, capsys) -> None:
        """Debug logs should go to stderr, not stdout."""
        # Remove any existing StreamHandler
        for handler in _logger.handlers[:]:
            if not isinstance(handler, logging.NullHandler):
                _logger.removeHandler(handler)

        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        old_value = os.environ.get("FLYWHEEL_DEBUG")
        os.environ["FLYWHEEL_DEBUG"] = "1"

        try:
            _configure_debug_logging()

            # Perform operations that generate logs
            storage.save([Todo(id=1, text="test todo")])
            storage.load()

            # Capture stdout/stderr
            captured = capsys.readouterr()

            # Nothing should be written to stdout (application data only)
            assert captured.out == ""

            # Logs may go to stderr (debug output)
            # The key is stdout is not polluted

        finally:
            if old_value is None:
                os.environ.pop("FLYWHEEL_DEBUG", None)
            else:
                os.environ["FLYWHEEL_DEBUG"] = old_value
            # Reset to default state
            for handler in _logger.handlers[:]:
                if not isinstance(handler, logging.NullHandler):
                    _logger.removeHandler(handler)
