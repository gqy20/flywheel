"""Test structured logging for lock acquisition and I/O operations (Issue #1502).

This test verifies that:
1. Lock acquisition uses structured logging with extra fields
2. I/O operations (_load_async) use structured logging with extra fields
3. Structured logs include 'component' and 'op' fields for monitoring
"""

import pathlib
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from flywheel.storage import FileStorage, _AsyncCompatibleLock
from flywheel.models import Todo


class TestStructuredLoggingLockAcquisition:
    """Test structured logging in lock acquisition (Issue #1502)."""

    def test_lock_enter_logs_with_extra_fields(self):
        """Test that __enter__ logs with extra={'component': 'storage', 'op': 'lock_acquire'}."""
        lock = _AsyncCompatibleLock()

        # Capture logs
        with patch('flywheel.storage.logger') as mock_logger:
            # Acquire lock using context manager
            with lock:
                pass

            # Check that debug was called with structured extra fields
            debug_calls = mock_logger.debug.call_args_list

            # Look for the specific structured logging call with extra fields
            structured_calls = [
                call for call in debug_calls
                if len(call) > 1 and hasattr(call[1], 'get') and call[1].get('extra', {}).get('component') == 'storage'
                and call[1].get('extra', {}).get('op') == 'lock_acquire'
            ]

            # This test will fail until we implement structured logging
            assert len(structured_calls) > 0, \
                "Lock acquisition should log with extra={'component': 'storage', 'op': 'lock_acquire'}"

    def test_lock_enter_extra_fields_structure(self):
        """Test that extra fields have the correct structure."""
        lock = _AsyncCompatibleLock()

        with patch('flywheel.storage.logger') as mock_logger:
            with lock:
                pass

            # Find any call with extra parameter
            calls_with_extra = [
                call for call in mock_logger.debug.call_args_list
                if len(call) > 1 and isinstance(call[1].get('extra'), dict)
            ]

            # Should have at least one call with extra fields
            assert len(calls_with_extra) > 0, "Should have log calls with extra fields"

            # Check structure of extra fields
            extra = calls_with_extra[0][1].get('extra', {})
            assert 'component' in extra, "Extra fields should include 'component'"
            assert 'op' in extra, "Extra fields should include 'op'"
            assert extra['component'] == 'storage', "Component should be 'storage'"
            assert extra['op'] == 'lock_acquire', "Operation should be 'lock_acquire'"


class TestStructuredLoggingIOOperations:
    """Test structured logging in I/O operations (Issue #1502)."""

    def test_load_async_logs_with_extra_fields(self):
        """Test that _load_async logs with extra={'component': 'storage', 'op': 'load_async'}."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Create a file to load
            todo = Todo(title="Test", description="Test I/O logging")
            storage.add(todo)
            storage.close()

            # Reopen to trigger _load_async
            storage = FileStorage(str(storage_path))

            # Capture logs
            with patch('flywheel.storage.logger') as mock_logger:
                # Trigger async load
                import asyncio
                asyncio.run(storage._load_async())

                # Check that debug was called with structured extra fields
                debug_calls = mock_logger.debug.call_args_list

                # Look for the specific structured logging call with extra fields
                structured_calls = [
                    call for call in debug_calls
                    if len(call) > 1 and hasattr(call[1], 'get') and
                    call[1].get('extra', {}).get('component') == 'storage' and
                    'load' in str(call[1].get('extra', {}).get('op', ''))
                ]

                # This test will fail until we implement structured logging
                assert len(structured_calls) > 0, \
                    "_load_async should log with extra={'component': 'storage', 'op': 'load_async'}"

            storage.close()

    def test_load_async_extra_fields_structure(self):
        """Test that extra fields in _load_async have the correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Create a file to load
            todo = Todo(title="Test", description="Test I/O logging structure")
            storage.add(todo)
            storage.close()

            # Reopen to trigger _load_async
            storage = FileStorage(str(storage_path))

            with patch('flywheel.storage.logger') as mock_logger:
                # Trigger async load
                import asyncio
                asyncio.run(storage._load_async())

                # Find any call with extra parameter
                calls_with_extra = [
                    call for call in mock_logger.debug.call_args_list
                    if len(call) > 1 and isinstance(call[1].get('extra'), dict)
                ]

                # Should have at least one call with extra fields
                assert len(calls_with_extra) > 0, "Should have log calls with extra fields in _load_async"

                # Check structure of extra fields
                extra = calls_with_extra[0][1].get('extra', {})
                assert 'component' in extra, "Extra fields should include 'component'"
                assert 'op' in extra, "Extra fields should include 'op'"
                assert extra['component'] == 'storage', "Component should be 'storage'"

            storage.close()
