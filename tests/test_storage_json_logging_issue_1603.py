"""Test JSON structured logging for lock contention (Issue #1603).

This test verifies that:
1. When DEBUG_STORAGE is enabled, lock contention events emit JSON logs
2. JSON logs contain proper structured fields (event, duration, caller, etc.)
3. JSON logs are machine-readable for monitoring tools (Datadog, ELK)
"""

import json
import os
import tempfile
import logging
from io import StringIO
from unittest.mock import patch
import pathlib

import pytest

from flywheel.storage import FileStorage, _AsyncCompatibleLock
from flywheel.models import Todo


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for testing."""

    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'message': record.getMessage(),
            'event': getattr(record, 'event', None),
            'wait_time': getattr(record, 'wait_time', None),
            'acquired': getattr(record, 'acquired', None),
            'thread': getattr(record, 'thread', None),
            'attempts': getattr(record, 'attempts', None),
            'caller': getattr(record, 'caller', None),
            'duration': getattr(record, 'duration', None),
        }
        # Remove None values
        log_data = {k: v for k, v in log_data.items() if v is not None}
        return json.dumps(log_data)


class TestJSONStructuredLogging:
    """Test JSON structured logging for lock contention (Issue #1603)."""

    def test_lock_contention_emits_json_when_debug_storage_enabled(self):
        """Test that lock contention emits JSON logs when DEBUG_STORAGE is enabled."""
        # Set DEBUG_STORAGE environment variable
        with patch.dict(os.environ, {'DEBUG_STORAGE': '1'}):
            lock = _AsyncCompatibleLock()

            # Create a string buffer to capture log output
            log_stream = StringIO()
            handler = logging.StreamHandler(log_stream)
            handler.setFormatter(JSONFormatter())

            # Get the flywheel.storage logger
            logger = logging.getLogger('flywheel.storage')
            original_level = logger.level
            logger.setLevel(logging.INFO)
            logger.addHandler(handler)

            try:
                # Acquire lock to trigger logging
                with lock:
                    pass

                # Get log output
                log_output = log_stream.getvalue()

                # Verify we got JSON output
                log_lines = [line for line in log_output.split('\n') if line.strip()]

                # Look for JSON log with event='lock_wait'
                json_logs = []
                for line in log_lines:
                    try:
                        log_data = json.loads(line)
                        if log_data.get('event') == 'lock_wait':
                            json_logs.append(log_data)
                    except json.JSONDecodeError:
                        pass

                # Should have at least one JSON log with event='lock_wait'
                assert len(json_logs) > 0, \
                    "Lock acquisition should emit JSON log with event='lock_wait' when DEBUG_STORAGE is enabled"

                # Verify the JSON log has required fields
                log_entry = json_logs[0]
                assert 'event' in log_entry, "JSON log should have 'event' field"
                assert 'wait_time' in log_entry, "JSON log should have 'wait_time' field"
                assert 'acquired' in log_entry, "JSON log should have 'acquired' field"
                assert log_entry['event'] == 'lock_wait', "Event should be 'lock_wait'"
                assert log_entry['acquired'] == True, "Acquired should be True for successful acquisition"
                assert isinstance(log_entry['wait_time'], (int, float)), "wait_time should be numeric"

            finally:
                logger.removeHandler(handler)
                logger.setLevel(original_level)

    def test_lock_contention_json_has_distinct_fields(self):
        """Test that JSON logs have distinct, non-nested fields."""
        with patch.dict(os.environ, {'DEBUG_STORAGE': '1'}):
            lock = _AsyncCompatibleLock()

            log_stream = StringIO()
            handler = logging.StreamHandler(log_stream)
            handler.setFormatter(JSONFormatter())

            logger = logging.getLogger('flywheel.storage')
            original_level = logger.level
            logger.setLevel(logging.INFO)
            logger.addHandler(handler)

            try:
                with lock:
                    pass

                log_output = log_stream.getvalue()

                # Parse JSON logs
                json_logs = []
                for line in log_output.split('\n'):
                    try:
                        log_data = json.loads(line)
                        if log_data.get('event') == 'lock_wait':
                            json_logs.append(log_data)
                    except json.JSONDecodeError:
                        pass

                assert len(json_logs) > 0, "Should have JSON logs"

                # Verify fields are distinct (not nested in a single 'extra' field)
                log_entry = json_logs[0]
                assert 'event' in log_entry, "Should have 'event' field at top level"
                assert 'wait_time' in log_entry, "Should have 'wait_time' field at top level"
                assert 'acquired' in log_entry, "Should have 'acquired' field at top level"
                assert 'thread' in log_entry, "Should have 'thread' field at top level"

                # Ensure fields are directly accessible (not nested)
                # This is crucial for monitoring tools like Datadog/ELK
                assert not any(isinstance(v, dict) for v in log_entry.values() if v is not None), \
                    "Fields should be primitive types, not nested objects"

            finally:
                logger.removeHandler(handler)
                logger.setLevel(original_level)

    def test_lock_timeout_emits_json_with_failure_status(self):
        """Test that lock timeout emits JSON log with acquired=False."""
        with patch.dict(os.environ, {'DEBUG_STORAGE': '1'}):
            # Create a lock with very short timeout to force timeout
            lock = _AsyncCompatibleLock(lock_timeout=0.001)

            # Acquire the lock in another thread to cause contention
            import threading
            import time

            acquired = threading.Event()
            lock_held = threading.Event()

            def hold_lock():
                with lock:
                    acquired.set()
                    lock_held.wait()

            thread = threading.Thread(target=hold_lock, daemon=True)
            thread.start()
            acquired.wait()

            log_stream = StringIO()
            handler = logging.StreamHandler(log_stream)
            handler.setFormatter(JSONFormatter())

            logger = logging.getLogger('flywheel.storage')
            original_level = logger.level
            logger.setLevel(logging.INFO)
            logger.addHandler(handler)

            try:
                # Try to acquire - should timeout
                with pytest.raises(Exception):  # StorageTimeoutError
                    with lock:
                        pass

                log_output = log_stream.getvalue()

                # Parse JSON logs
                json_logs = []
                for line in log_output.split('\n'):
                    try:
                        log_data = json.loads(line)
                        if log_data.get('event') == 'lock_wait':
                            json_logs.append(log_data)
                    except json.JSONDecodeError:
                        pass

                # Should have JSON logs with acquired=False for timeout
                timeout_logs = [log for log in json_logs if log.get('acquired') == False]
                assert len(timeout_logs) > 0, \
                    "Lock timeout should emit JSON log with acquired=False"

            finally:
                lock_held.set()
                thread.join(timeout=2)
                logger.removeHandler(handler)
                logger.setLevel(original_level)

    def test_json_logging_only_when_debug_storage_enabled(self):
        """Test that JSON logging only happens when DEBUG_STORAGE is enabled."""
        # Ensure DEBUG_STORAGE is NOT set
        with patch.dict(os.environ, {}, clear=False):
            # Remove DEBUG_STORAGE if it exists
            env = os.environ.copy()
            env.pop('DEBUG_STORAGE', None)
            with patch.dict(os.environ, env, clear=True):
                lock = _AsyncCompatibleLock()

                log_stream = StringIO()
                handler = logging.StreamHandler(log_stream)
                handler.setFormatter(JSONFormatter())

                logger = logging.getLogger('flywheel.storage')
                original_level = logger.level
                logger.setLevel(logging.INFO)
                logger.addHandler(handler)

                try:
                    with lock:
                        pass

                    log_output = log_stream.getvalue()

                    # Parse JSON logs
                    json_logs = []
                    for line in log_output.split('\n'):
                        try:
                            log_data = json.loads(line)
                            if log_data.get('event') == 'lock_wait':
                                json_logs.append(log_data)
                        except json.JSONDecodeError:
                            pass

                    # Should NOT have JSON logs with event='lock_wait' when DEBUG_STORAGE is disabled
                    assert len(json_logs) == 0, \
                        "JSON logs with event='lock_wait' should only be emitted when DEBUG_STORAGE is enabled"

                finally:
                    logger.removeHandler(handler)
                    logger.setLevel(original_level)
