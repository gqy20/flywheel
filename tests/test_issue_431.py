"""Test for Issue #431 - Verify Windows file lock range is used correctly.

This test verifies that the _get_file_lock_range_from_handle method is called
and its return value is used in the Windows file locking implementation.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from flywheel.storage import Storage


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
def test_windows_lock_range_from_handle_is_called():
    """Test that _get_file_lock_range_from_handle is called and used for locking.

    This is a Windows-specific test that verifies the file lock range calculation
    method is properly invoked and its return value is used in the LockFileEx call.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Mock the Windows modules
        with patch('flywheel.storage.win32file') as mock_win32file, \
             patch('flywheel.storage.win32con') as mock_win32con, \
             patch('flywheel.storage.pywintypes') as mock_pywintypes:

            # Setup mock return values
            mock_win32file._get_osfhandle.return_value = 12345
            mock_pywintypes.OVERLAPPED.return_value = Mock()
            mock_win32con.LOCKFILE_FAIL_IMMEDIATELY = 1
            mock_win32con.LOCKFILE_EXCLUSIVE_LOCK = 2

            # Track if LockFileEx was called with the correct parameters
            lockfileex_calls = []
            original_lockfileex = mock_win32file.LockFileEx

            def capture_lockfileex(*args, **kwargs):
                lockfileex_calls.append((args, kwargs))
                return None  # Success

            mock_win32file.LockFileEx.side_effect = capture_lockfileex

            # Create storage (this will trigger file locking)
            storage = Storage(str(storage_path))

            # Add a todo to trigger save operation (which uses file locking)
            from flywheel.todo import Todo
            todo = Todo(title="Test todo")
            storage.add(todo)

            # Verify LockFileEx was called
            assert len(lockfileex_calls) > 0, "LockFileEx should have been called"

            # Get the first call to LockFileEx
            call_args, call_kwargs = lockfileex_calls[0]

            # Verify the parameters: LockFileEx(hFile, dwFlags, dwReserved,
            #                                NumberOfBytesToLockLow, NumberOfBytesToLockHigh,
            #                                overlapped)
            # The 4th and 5th positional args (index 3 and 4) should be the lock range
            # from _get_file_lock_range_from_handle, which returns (0, 1) on Windows
            assert len(call_args) >= 5, f"LockFileEx should be called with at least 5 args, got {len(call_args)}"

            lock_range_low = call_args[3]  # 4th arg (index 3)
            lock_range_high = call_args[4]  # 5th arg (index 4)

            # Verify the lock range matches what _get_file_lock_range_from_handle returns
            assert lock_range_low == 0, f"Lock range low should be 0, got {lock_range_low}"
            assert lock_range_high == 1, f"Lock range high should be 1, got {lock_range_high}"


@pytest.mark.skipif(os.name == 'nt', reason="Unix-specific test")
def test_unix_lock_range_placeholder():
    """Test that _get_file_lock_range_from_handle returns placeholder on Unix.

    This is a Unix-specific test that verifies the method returns a placeholder
    value since fcntl.flock doesn't use lock ranges.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage
        storage = Storage(str(storage_path))

        # Mock a file handle
        mock_file = Mock()

        # Call _get_file_lock_range_from_handle
        lock_range = storage._get_file_lock_range_from_handle(mock_file)

        # On Unix, it should return 0 (placeholder)
        assert lock_range == 0, f"Unix lock range should be 0 (placeholder), got {lock_range}"


def test_lock_range_method_returns_correct_values():
    """Test that _get_file_lock_range_from_handle returns correct values based on platform.

    This test verifies the method returns the correct lock range values:
    - On Windows: (0, 1) representing 4GB lock length
    - On Unix: 0 as a placeholder (fcntl.flock doesn't use ranges)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage
        storage = Storage(str(storage_path))

        # Mock a file handle
        mock_file = Mock()

        # Call _get_file_lock_range_from_handle
        lock_range = storage._get_file_lock_range_from_handle(mock_file)

        if os.name == 'nt':
            # On Windows, should return (0, 1) representing 4GB
            assert isinstance(lock_range, tuple), f"Windows lock range should be a tuple, got {type(lock_range)}"
            assert len(lock_range) == 2, f"Windows lock range tuple should have 2 elements, got {len(lock_range)}"
            assert lock_range == (0, 1), f"Windows lock range should be (0, 1), got {lock_range}"
        else:
            # On Unix, should return 0 as placeholder
            assert lock_range == 0, f"Unix lock range should be 0 (placeholder), got {lock_range}"
