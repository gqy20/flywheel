"""Test structured logging for lock acquisition and retry attempts (Issue #922).

This test verifies that:
1. Retry attempts log structured data (attempt number, backoff time, errno)
2. Lock acquisition attempts log structured data
3. Logs are in JSON format with proper context
4. Structured logs help debug concurrency issues in production
"""

import errno
import json
import logging
import pathlib
import tempfile
import time
from unittest.mock import patch

import pytest

from flywheel.storage import FileStorage, retry_transient_errors
from flywheel.models import Todo


class TestStructuredLoggingRetries:
    """Test suite for structured logging in retry logic."""

    def test_retry_logs_attempt_number(self):
        """Test that retry attempts log the attempt number."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Mock the save method to fail then succeed
            original_save = storage._save_with_todos_sync
            attempt_count = [0]

            def flaky_save(todos):
                attempt_count[0] += 1
                if attempt_count[0] == 1:
                    raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
                else:
                    return original_save(todos)

            storage._save_with_todos_sync = flaky_save

            # Capture logs
            with patch('flywheel.storage.logger') as mock_logger:
                todo = Todo(title="Test", description="Test retry logging")
                storage.add(todo)

                # Check that structured logging was called
                assert mock_logger.debug.called, "Debug logger should be called for retry"

                # Find the retry log call
                retry_calls = [
                    call for call in mock_logger.debug.call_args_list
                    if 'attempt' in str(call).lower()
                ]

                assert len(retry_calls) > 0, "Should log retry attempt information"

                # Verify the log contains attempt number
                log_message = str(retry_calls[0])
                assert 'attempt' in log_message.lower(), "Log should contain attempt number"

            storage.close()

    def test_retry_logs_backoff_time(self):
        """Test that retry attempts log the backoff time."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Mock the save method to fail then succeed
            original_save = storage._save_with_todos_sync
            attempt_count = [0]

            def flaky_save(todos):
                attempt_count[0] += 1
                if attempt_count[0] == 1:
                    raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
                else:
                    return original_save(todos)

            storage._save_with_todos_sync = flaky_save

            # Capture logs
            with patch('flywheel.storage.logger') as mock_logger:
                todo = Todo(title="Test", description="Test backoff logging")
                storage.add(todo)

                # Find the retry log call
                retry_calls = [
                    call for call in mock_logger.debug.call_args_list
                    if 'retrying' in str(call).lower() or 'backoff' in str(call).lower()
                ]

                assert len(retry_calls) > 0, "Should log backoff time"

                # Verify the log mentions the timing/backoff
                log_message = str(retry_calls[0])
                assert any(word in log_message.lower() for word in ['s', 'sec', 'time', 'backoff']), \
                    "Log should contain backoff time information"

            storage.close()

    def test_retry_logs_errno(self):
        """Test that retry attempts log the specific errno captured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Mock the save method to fail with specific errno
            original_save = storage._save_with_todos_sync
            attempt_count = [0]
            test_errno = errno.EAGAIN

            def flaky_save(todos):
                attempt_count[0] += 1
                if attempt_count[0] == 1:
                    raise IOError(test_errno, "Resource temporarily unavailable")
                else:
                    return original_save(todos)

            storage._save_with_todos_sync = flaky_save

            # Capture logs
            with patch('flywheel.storage.logger') as mock_logger:
                todo = Todo(title="Test", description="Test errno logging")
                storage.add(todo)

                # Find the retry log call
                retry_calls = [
                    call for call in mock_logger.debug.call_args_list
                    if 'transient' in str(call).lower() or 'error' in str(call).lower()
                ]

                assert len(retry_calls) > 0, "Should log error information"

                # Verify the log contains error information
                log_message = str(retry_calls[0])
                # Should contain errno or error description
                assert any(word in log_message.lower() for word in ['errno', 'eagain', 'error', str(test_errno)]), \
                    "Log should contain errno information"

            storage.close()

    def test_retry_logs_structured_data(self):
        """Test that retry attempts log structured data (dict-like format)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Mock the save method to fail then succeed
            original_save = storage._save_with_todos_sync
            attempt_count = [0]

            def flaky_save(todos):
                attempt_count[0] += 1
                if attempt_count[0] == 1:
                    raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
                else:
                    return original_save(todos)

            storage._save_with_todos_sync = flaky_save

            # Capture logs
            with patch('flywheel.storage.logger') as mock_logger:
                todo = Todo(title="Test", description="Test structured logging")
                storage.add(todo)

                # Check that extra context is passed to logger
                debug_calls = mock_logger.debug.call_args_list

                # Look for calls with extra parameter (structured logging)
                structured_calls = [
                    call for call in debug_calls
                    if len(call) > 1 and 'extra' in str(call)
                ]

                # This test will fail until we implement structured logging
                assert len(structured_calls) > 0, \
                    "Should log with structured data (extra parameter for context)"

            storage.close()

    def test_retry_decorator_logs_with_json_context(self):
        """Test that the retry decorator logs with JSON-formatted context."""
        @retry_transient_errors(max_attempts=2, initial_backoff=0.01)
        def test_function():
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
            return "success"

        attempt_count = [0]

        # Capture logs
        with patch('flywheel.storage.logger') as mock_logger:
            result = test_function()

            assert result == "success"

            # Check for structured logging with context
            debug_calls = mock_logger.debug.call_args_list

            # Should have logged retry information
            assert len(debug_calls) > 0, "Should log retry information"

            # Look for JSON-like structured data in logs
            has_structured_data = any(
                'extra' in str(call) or 'dict' in str(call).lower()
                for call in debug_calls
            )

            # This will fail until we implement structured logging
            assert has_structured_data, \
                "Retry decorator should log with structured data context"


class TestStructuredLoggingLockAcquisition:
    """Test suite for structured logging in lock acquisition."""

    def test_lock_acquisition_logs_attempt(self):
        """Test that lock acquisition logs the attempt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Trigger lock acquisition by adding a todo
            with patch('flywheel.storage.logger') as mock_logger:
                todo = Todo(title="Test", description="Test lock logging")
                storage.add(todo)

                # Check that lock acquisition was logged
                all_calls = mock_logger.debug.call_args_list + mock_logger.info.call_args_list

                # Should have logs about lock operations
                lock_calls = [
                    call for call in all_calls
                    if 'lock' in str(call).lower()
                ]

                assert len(lock_calls) > 0, "Should log lock acquisition"

            storage.close()

    def test_lock_acquisition_logs_structured_data(self):
        """Test that lock acquisition logs structured data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Trigger lock acquisition by adding a todo
            with patch('flywheel.storage.logger') as mock_logger:
                todo = Todo(title="Test", description="Test lock structured logging")
                storage.add(todo)

                # Check for structured logging with extra context
                all_calls = (
                    mock_logger.debug.call_args_list +
                    mock_logger.info.call_args_list +
                    mock_logger.warning.call_args_list
                )

                # Look for calls with extra parameter (structured logging)
                structured_calls = [
                    call for call in all_calls
                    if len(call) > 1 and 'extra' in str(call)
                ]

                # This test will fail until we implement structured logging
                assert len(structured_calls) > 0, \
                    "Lock acquisition should log with structured data (extra parameter)"

            storage.close()

    def test_lock_retry_logs_backoff(self):
        """Test that lock retry attempts log backoff time."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Trigger lock acquisition
            with patch('flywheel.storage.logger') as mock_logger:
                todo = Todo(title="Test", description="Test lock backoff logging")
                storage.add(todo)

                # Check for logs about timing/backoff
                all_calls = (
                    mock_logger.debug.call_args_list +
                    mock_logger.info.call_args_list
                )

                timing_calls = [
                    call for call in all_calls
                    if any(word in str(call).lower() for word in ['time', 'elapsed', 's', 'sec'])
                ]

                # This test will fail until we implement structured logging with timing
                assert len(timing_calls) > 0, \
                    "Lock retry should log timing information"

            storage.close()
