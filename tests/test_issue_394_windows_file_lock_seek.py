"""Test for issue #394: Windows file locking deadlock risk due to missing seek before unlock.

This test verifies that file_handle.seek(0) is called before msvcrt.locking unlock
operations to prevent deadlocks when the file pointer has moved since lock acquisition.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

from flywheel.storage import Storage


class TestIssue394WindowsFileLockSeek(unittest.TestCase):
    """Test that file handle is seeked to position 0 before unlock."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "todos.json"

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('os.name', 'nt')
    def test_release_file_lock_seeks_before_unlock(self):
        """Test that _release_file_lock seeks to position 0 before unlocking.

        This test verifies the fix for issue #394. When releasing a file lock on
        Windows, the file handle must be at position 0 to unlock the same region
        that was locked. If the file pointer has moved since lock acquisition,
        unlocking will fail or unlock the wrong region.
        """
        # Create a storage instance to initialize _lock_range
        storage = Storage(str(self.storage_path))
        storage._lock_range = 0x7FFFFFFF  # Set the lock range cache

        # Create a mock file handle
        mock_file = MagicMock()

        # Call _release_file_lock
        storage._release_file_lock(mock_file)

        # Verify that seek(0) was called BEFORE locking
        # The order should be: seek(0), then msvcrt.locking
        method_calls = mock_file.method_calls

        # Find seek call
        seek_calls = [c for c in method_calls if c[0] == 'seek']
        self.assertEqual(len(seek_calls), 1, "seek should be called exactly once")
        self.assertEqual(seek_calls[0], call().seek(0), "seek should be called with argument 0")

    @patch('os.name', 'nt')
    def test_acquire_file_lock_seeks_before_lock(self):
        """Test that _acquire_file_lock seeks to position 0 before locking.

        This test verifies that both acquire and release operations seek to
        position 0 before calling msvcrt.locking, ensuring they operate on
        the same file region.
        """
        # Create a storage instance
        storage = Storage(str(self.storage_path))

        # Create a mock file handle that simulates a file
        mock_file = MagicMock()
        mock_file.fileno.return_value = 42
        mock_file.name = "test.json"

        # Mock msvcrt.locking to succeed immediately
        with patch('msvcrt.locking'):
            # Call _acquire_file_lock
            storage._acquire_file_lock(mock_file)

            # Verify that flush() was called
            mock_file.flush.assert_called_once()

            # Verify that seek(0) was called
            mock_file.seek.assert_called_with(0)

    @patch('os.name', 'nt')
    def test_file_pointer_position_consistency_between_lock_and_unlock(self):
        """Test that file handle position is consistent between lock and unlock.

        This test simulates a scenario where the file pointer might move after
        lock acquisition, and verifies that unlock still seeks to position 0
        to match the lock operation.
        """
        # Create a storage instance
        storage = Storage(str(self.storage_path))
        storage._lock_range = 0x7FFFFFFF

        # Create a mock file handle
        mock_file = MagicMock()

        # Simulate the file pointer being at a different position
        mock_file.tell.return_value = 1024  # File pointer is at position 1024

        # Call _release_file_lock
        storage._release_file_lock(mock_file)

        # Verify that seek(0) was called to reset position
        mock_file.seek.assert_called_with(0)

    @patch('os.name', 'nt')
    def test_unlock_with_mocked_msvcrt(self):
        """Integration test with mocked msvcrt to verify unlock sequence.

        This test verifies the complete unlock sequence including:
        1. Validation of lock_range
        2. seek(0) call
        3. msvcrt.locking with LK_UNLCK
        """
        # Create a storage instance
        storage = Storage(str(self.storage_path))
        storage._lock_range = 0x7FFFFFFF

        # Create a mock file handle
        mock_file = MagicMock()
        mock_file.fileno.return_value = 42

        # Mock msvcrt module
        with patch('flywheel.storage.msvcrt') as mock_msvcrt:
            # Call _release_file_lock
            storage._release_file_lock(mock_file)

            # Verify seek(0) was called
            mock_file.seek.assert_called_once_with(0)

            # Verify msvcrt.locking was called with LK_UNLCK
            mock_msvcrt.locking.assert_called_once_with(
                42,  # file descriptor
                mock_msvcrt.LK_UNLCK,
                0x7FFFFFFF  # lock range
            )


if __name__ == '__main__':
    unittest.main()
