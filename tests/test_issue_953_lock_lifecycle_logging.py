"""Test structured logging for lock lifecycle (Issue #953).

This test verifies that:
1. Lock acquisition logs structured data with action, file, and mode
2. Lock release logs structured data with action and file
3. Stale lock cleanup logs structured data with action, reason, and file
4. All logs use JSON format via the extra parameter for production monitoring
"""

import json
import logging
import pathlib
import tempfile
from unittest.mock import patch, MagicMock
import pytest

from flywheel.storage import FileStorage
from flywheel.models import Todo


class TestLockLifecycleStructuredLogging:
    """Test suite for structured logging in lock lifecycle operations."""

    def test_lock_release_logs_structured_data(self):
        """Test that lock release logs structured data (action, file)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Trigger lock acquisition and release by adding a todo
            with patch('flywheel.storage.logger') as mock_logger:
                todo = Todo(title="Test", description="Test lock release logging")
                storage.add(todo)
                storage.close()

                # Check for lock release logs
                all_calls = (
                    mock_logger.debug.call_args_list +
                    mock_logger.info.call_args_list
                )

                # Look for lock release calls with structured data
                release_calls = [
                    call for call in all_calls
                    if 'release' in str(call).lower() and 'lock' in str(call).lower()
                ]

                assert len(release_calls) > 0, "Should log lock release"

                # Verify structured logging with extra parameter
                structured_calls = [
                    call for call in release_calls
                    if len(call) > 1 and hasattr(call[1], 'get') and call[1].get('extra')
                ]

                # This test will fail until we implement structured logging for lock release
                assert len(structured_calls) > 0, \
                    "Lock release should log with structured data (action, file)"

                # Verify the structured data contains required fields
                extra_data = structured_calls[0][1]['extra']
                assert 'structured' in extra_data, "Should mark as structured log"
                assert extra_data['structured'] is True, "structured flag should be True"
                assert 'event' in extra_data, "Should have event field"
                assert extra_data['event'] in ['lock_released', 'lock_release'], \
                    "Event should indicate lock release"

    def test_lock_acquisition_includes_degraded_mode(self):
        """Test that lock acquisition in degraded mode logs the mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Mock degraded mode to trigger fallback logging
            with patch('flywheel.storage._is_degraded_mode', return_value=True):
                with patch('flywheel.storage.logger') as mock_logger:
                    todo = Todo(title="Test", description="Test degraded mode logging")
                    storage.add(todo)

                    # Check for degraded mode logs
                    all_calls = mock_logger.info.call_args_list

                    degraded_mode_calls = [
                        call for call in all_calls
                        if 'degraded' in str(call).lower() or 'fallback' in str(call).lower()
                    ]

                    assert len(degraded_mode_calls) > 0, \
                        "Should log when using degraded mode"

                    # Verify structured logging includes mode information
                    structured_calls = [
                        call for call in degraded_mode_calls
                        if len(call) > 1 and hasattr(call[1], 'get') and call[1].get('extra')
                    ]

                    # This test will fail until we implement structured logging for degraded mode
                    assert len(structured_calls) > 0, \
                        "Degraded mode acquisition should log with structured data (mode)"

                    if len(structured_calls) > 0:
                        extra_data = structured_calls[0][1]['extra']
                        assert 'structured' in extra_data, "Should mark as structured log"
                        assert 'mode' in extra_data or 'lock_type' in extra_data, \
                            "Should include mode or lock_type field"

            storage.close()

    def test_stale_lock_cleanup_logs_structured_data(self):
        """Test that stale lock cleanup logs structured data (action, reason)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Create a stale lock file
            lock_file = pathlib.Path(str(storage_path) + ".lock")
            lock_file.write_text(f"pid=99999\nlocked_at=1234567890\n")

            # Trigger stale lock detection and cleanup
            with patch('flywheel.storage.logger') as mock_logger:
                todo = Todo(title="Test", description="Test stale lock logging")
                storage.add(todo)

                # Check for stale lock cleanup logs
                all_calls = (
                    mock_logger.warning.call_args_list +
                    mock_logger.debug.call_args_list
                )

                stale_calls = [
                    call for call in all_calls
                    if 'stale' in str(call).lower()
                ]

                assert len(stale_calls) > 0, "Should log stale lock detection/cleanup"

                # Verify structured logging includes reason
                structured_calls = [
                    call for call in stale_calls
                    if len(call) > 1 and hasattr(call[1], 'get') and call[1].get('extra')
                ]

                # This test will fail until we implement structured logging for stale locks
                assert len(structured_calls) > 0, \
                    "Stale lock cleanup should log with structured data (reason)"

                if len(structured_calls) > 0:
                    extra_data = structured_calls[0][1]['extra']
                    assert 'structured' in extra_data, "Should mark as structured log"
                    assert 'event' in extra_data, "Should have event field"
                    assert 'stale' in extra_data['event'] or 'lock' in extra_data['event'], \
                        "Event should relate to stale lock cleanup"

            storage.close()

    def test_lock_logs_include_file_path(self):
        """Test that all lock lifecycle logs include the file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            with patch('flywheel.storage.logger') as mock_logger:
                todo = Todo(title="Test", description="Test file path in logs")
                storage.add(todo)
                storage.close()

                # Check all lock-related logs
                all_calls = (
                    mock_logger.debug.call_args_list +
                    mock_logger.info.call_args_list +
                    mock_logger.warning.call_args_list
                )

                lock_calls = [
                    call for call in all_calls
                    if 'lock' in str(call).lower()
                ]

                assert len(lock_calls) > 0, "Should have lock-related logs"

                # Look for structured calls with file path
                calls_with_path = [
                    call for call in lock_calls
                    if len(call) > 1 and hasattr(call[1], 'get') and
                    call[1].get('extra') and
                    'file' in str(call[1].get('extra', {})).lower()
                ]

                # This test will fail until all lock logs include file path
                assert len(calls_with_path) > 0, \
                    "Lock lifecycle logs should include file path in structured data"

    def test_structured_logs_use_json_format(self):
        """Test that structured logs can be serialized as JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            with patch('flywheel.storage.logger') as mock_logger:
                todo = Todo(title="Test", description="Test JSON format")
                storage.add(todo)
                storage.close()

                # Check all log calls with extra parameter
                all_calls = (
                    mock_logger.debug.call_args_list +
                    mock_logger.info.call_args_list
                )

                structured_calls = [
                    call for call in all_calls
                    if len(call) > 1 and hasattr(call[1], 'get') and call[1].get('extra')
                ]

                # Verify that all structured data is JSON-serializable
                for call in structured_calls:
                    extra_data = call[1]['extra']
                    try:
                        # This should not raise an exception
                        json.dumps(extra_data)
                    except (TypeError, ValueError) as e:
                        pytest.fail(
                            f"Structured log data should be JSON-serializable: {e}\n"
                            f"Data: {extra_data}"
                        )

                # Should have at least some structured logs
                assert len(structured_calls) > 0, \
                    "Should have structured logs that are JSON-serializable"

    def test_lock_release_on_windows_logs_structured_data(self):
        """Test that Windows lock release logs structured data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Mock Windows platform
            with patch('flywheel.storage.os.name', 'nt'):
                with patch('flywheel.storage._is_degraded_mode', return_value=False):
                    # Mock win32file to simulate Windows environment
                    with patch('flywheel.storage.win32file') as mock_win32file:
                        with patch('flywheel.storage.win32con') as mock_win32con:
                            with patch('flywheel.storage.pywintypes') as mock_pywintypes:
                                # Setup mocks
                                mock_win32con.LOCKFILE_FAIL_IMMEDIATELY = 1
                                mock_win32con.LOCKFILE_EXCLUSIVE_LOCK = 2
                                mock_handle = MagicMock()
                                mock_win32file._get_osfhandle.return_value = mock_handle
                                mock_pywintypes.OVERLAPPED.return_value = MagicMock()

                                with patch('flywheel.storage.logger') as mock_logger:
                                    try:
                                        todo = Todo(title="Test", description="Test Windows logging")
                                        storage.add(todo)
                                        storage.close()
                                    except Exception:
                                        # May fail due to mocking, but we can check logs
                                        pass

                                    # Check for lock release logs
                                    all_calls = mock_logger.debug.call_args_list

                                    release_calls = [
                                        call for call in all_calls
                                        if 'release' in str(call).lower() and 'lock' in str(call).lower()
                                    ]

                                    if len(release_calls) > 0:
                                        # Verify structured logging
                                        structured_calls = [
                                            call for call in release_calls
                                            if len(call) > 1 and hasattr(call[1], 'get') and
                                            call[1].get('extra')
                                        ]

                                        # This test will fail until we implement structured logging
                                        assert len(structured_calls) > 0, \
                                            "Windows lock release should log with structured data"

                                        if len(structured_calls) > 0:
                                            extra_data = structured_calls[0][1]['extra']
                                            assert 'structured' in extra_data, \
                                                "Should mark as structured log"
                                            assert 'event' in extra_data, \
                                                "Should have event field"

    def test_lock_release_on_unix_logs_structured_data(self):
        """Test that Unix lock release logs structured data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = pathlib.Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Mock Unix platform
            with patch('flywheel.storage.os.name', 'posix'):
                with patch('flywheel.storage._is_degraded_mode', return_value=False):
                    # Mock fcntl to simulate Unix environment
                    with patch('flywheel.storage.fcntl') as mock_fcntl:
                        mock_fcntl.LOCK_EX = 2
                        mock_fcntl.LOCK_NB = 4
                        mock_fcntl.LOCK_UN = 8

                        with patch('flywheel.storage.logger') as mock_logger:
                            try:
                                todo = Todo(title="Test", description="Test Unix logging")
                                storage.add(todo)
                                storage.close()
                            except Exception:
                                # May fail due to mocking, but we can check logs
                                pass

                            # Check for lock release logs
                            all_calls = mock_logger.debug.call_args_list

                            release_calls = [
                                call for call in all_calls
                                if 'release' in str(call).lower() and 'lock' in str(call).lower()
                            ]

                            if len(release_calls) > 0:
                                # Verify structured logging
                                structured_calls = [
                                    call for call in release_calls
                                    if len(call) > 1 and hasattr(call[1], 'get') and
                                    call[1].get('extra')
                                ]

                                # This test will fail until we implement structured logging
                                assert len(structured_calls) > 0, \
                                    "Unix lock release should log with structured data"

                                if len(structured_calls) > 0:
                                    extra_data = structured_calls[0][1]['extra']
                                    assert 'structured' in extra_data, \
                                        "Should mark as structured log"
                                    assert 'event' in extra_data, \
                                        "Should have event field"
