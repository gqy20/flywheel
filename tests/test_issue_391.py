"""Test Windows file pointer reset before unlocking (Issue #391).

This test verifies that the file pointer is reset to position 0
before calling msvcrt.locking with LK_UNLOCK on Windows.

The unlock operation must act on the exact same byte range [0, 0x7FFFFFFF)
that was locked. If the file pointer is not at 0, the unlock will fail
or throw an exception.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_windows_file_pointer_reset_before_unlock():
    """Test that file pointer is reset to 0 before unlocking on Windows.

    This test verifies that _release_file_lock properly seeks to position 0
    before calling msvcrt.locking with LK_UNLOCK.

    The test uses mocking to simulate Windows behavior and verify that:
    1. The file handle is at some position (not 0) before unlock
    2. seek(0) is called to reset the file pointer
    3. msvcrt.locking is called with the correct parameters
    """
    # Only test on Windows or when explicitly testing Windows behavior
    if os.name != 'nt':
        # On non-Windows systems, we mock the Windows-specific code
        with patch('flywheel.storage.os.name', 'nt'):
            with patch('flywheel.storage.msvcrt') as mock_msvcrt:
                # Create a temporary storage
                with tempfile.TemporaryDirectory() as tmpdir:
                    storage_path = str(Path(tmpdir) / "test_unlock.json")
                    storage = Storage(path=storage_path)

                    # Add a todo to trigger file operations
                    storage.add(Todo(title="Test Todo", status="pending"))

                    # Create a mock file handle
                    mock_file = MagicMock()
                    mock_file.fileno.return_value = 1
                    mock_file.tell.return_value = 100  # File pointer is at position 100

                    # Set the lock range cache (normally set by _acquire_file_lock)
                    storage._lock_range = 0x7FFFFFFF

                    # Call _release_file_lock
                    storage._release_file_lock(mock_file)

                    # Verify seek(0) was called BEFORE msvcrt.locking
                    # The sequence should be: seek(0), then locking(fileno, LK_UNLCK, range)
                    assert mock_file.seek.called, "seek(0) was not called before unlock"
                    mock_file.seek.assert_called_with(0)

                    # Verify msvcrt.locking was called with LK_UNLOCK
                    assert mock_msvcrt.locking.called, "msvcrt.locking was not called"
                    args = mock_msvcrt.locking.call_args
                    assert args[0][0] == 1, "File descriptor mismatch"
                    assert args[0][1] == mock_msvcrt.LK_UNLCK, "Lock mode should be LK_UNLCK"
                    assert args[0][2] == 0x7FFFFFFF, "Lock range mismatch"
    else:
        # On actual Windows systems, test with real file operations
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = str(Path(tmpdir) / "test_unlock_windows.json")
            storage = Storage(path=storage_path)

            # Add a todo to trigger file operations
            storage.add(Todo(title="Test Todo", status="pending"))

            # Open the file and simulate a non-zero file pointer
            with storage.path.open('r') as f:
                # Read some data to move the file pointer
                f.read(10)

                # The file pointer should now be at position > 0
                initial_position = f.tell()
                assert initial_position > 0, "File pointer should be at non-zero position"

                # Now test that _release_file_lock properly resets the pointer
                # This should NOT raise an exception even though pointer was non-zero
                storage._acquire_file_lock(f)

                # Move the file pointer away from 0 (simulating a read operation)
                f.read(5)
                assert f.tell() > 0, "File pointer should be at non-zero position"

                # Release the lock - this should work because seek(0) is called internally
                storage._release_file_lock(f)

                # If we got here without exception, the test passes
                assert True


def test_windows_lock_unlock_symmetry():
    """Test that lock and unlock operations are symmetric on Windows.

    This verifies that both _acquire_file_lock and _release_file_lock
    seek to position 0 before their respective msvcrt.locking calls.
    """
    if os.name != 'nt':
        # Mock Windows behavior on non-Windows systems
        with patch('flywheel.storage.os.name', 'nt'):
            with patch('flywheel.storage.msvcrt') as mock_msvcrt:
                with tempfile.TemporaryDirectory() as tmpdir:
                    storage_path = str(Path(tmpdir) / "test_symmetry.json")
                    storage = Storage(path=storage_path)

                    # Create a mock file handle
                    mock_file = MagicMock()
                    mock_file.fileno.return_value = 1

                    # Test acquire
                    storage._acquire_file_lock(mock_file)

                    # Verify seek(0) was called during acquire
                    assert mock_file.seek.called, "seek(0) was not called during acquire"
                    mock_file.seek.assert_called_with(0)

                    # Verify msvcrt.locking was called with LK_LOCK
                    args = mock_msvcrt.locking.call_args
                    assert args[0][1] == mock_msvcrt.LK_LOCK, "Lock mode should be LK_LOCK"

                    # Reset mock for unlock test
                    mock_file.reset_mock()

                    # Test release
                    storage._release_file_lock(mock_file)

                    # Verify seek(0) was called during unlock
                    assert mock_file.seek.called, "seek(0) was not called during unlock"
                    mock_file.seek.assert_called_with(0)

                    # Verify msvcrt.locking was called with LK_UNLOCK
                    args = mock_msvcrt.locking.call_args
                    assert args[0][1] == mock_msvcrt.LK_UNLCK, "Lock mode should be LK_UNLCK"
    else:
        # On actual Windows systems, test with real file operations
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = str(Path(tmpdir) / "test_symmetry_windows.json")
            storage = Storage(path=storage_path)

            # Open the file
            with storage.path.open('r') as f:
                # Move file pointer away from 0
                f.read(10)
                assert f.tell() > 0

                # Acquire lock (should seek to 0 internally)
                storage._acquire_file_lock(f)

                # Move file pointer away from 0 again
                f.read(5)
                assert f.tell() > 0

                # Release lock (should seek to 0 internally)
                storage._release_file_lock(f)

                # If we got here without exception, both operations worked correctly
                assert True


def test_windows_lock_range_consistency():
    """Test that lock and unlock use the same range on Windows.

    This verifies that the lock range cached during acquire
    is used correctly during release.
    """
    if os.name != 'nt':
        # Mock Windows behavior on non-Windows systems
        with patch('flywheel.storage.os.name', 'nt'):
            with patch('flywheel.storage.msvcrt') as mock_msvcrt:
                with tempfile.TemporaryDirectory() as tmpdir:
                    storage_path = str(Path(tmpdir) / "test_range.json")
                    storage = Storage(path=storage_path)

                    # Create a mock file handle
                    mock_file = MagicMock()
                    mock_file.fileno.return_value = 1

                    # Acquire lock
                    storage._acquire_file_lock(mock_file)

                    # Get the lock range that was used
                    acquire_args = mock_msvcrt.locking.call_args
                    lock_range_acquire = acquire_args[0][2]

                    # Verify it's the expected fixed range
                    assert lock_range_acquire == 0x7FFFFFFF, \
                        f"Lock range should be 0x7FFFFFFF, got {lock_range_acquire}"

                    # Release lock
                    storage._release_file_lock(mock_file)

                    # Get the lock range used for unlock
                    release_args = mock_msvcrt.locking.call_args
                    lock_range_release = release_args[0][2]

                    # Verify both use the same range
                    assert lock_range_acquire == lock_range_release, \
                        f"Lock range mismatch: acquire={lock_range_acquire}, release={lock_range_release}"
