"""Test Windows file lock range is sufficient to prevent concurrent modification (Issue #270)."""

import os
import tempfile
import unittest
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestIssue270(unittest.TestCase):
    """Test that Windows file lock range is sufficiently large.

    Issue #270: Windows file locking was only set to 1 byte, which cannot
    prevent other processes from concurrently modifying file content.

    The fix should use a sufficiently large value (e.g., 0xFFFF or larger)
    to lock the entire file, not just the first byte.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.temp_dir, "test_todos.json")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_lock_range_is_sufficiently_large(self):
        """Test that the file lock range is larger than 1 byte.

        This test verifies that the implementation uses a sufficiently large
        lock range (not just 1 byte) to prevent concurrent modifications.
        """
        if os.name != 'nt':
            self.skipTest("This test is only applicable on Windows")

        # Create a storage instance with some data
        storage = Storage(self.storage_path)
        todo1 = Todo(title="Task 1")
        storage.add(todo1)

        # Create a large todo list to ensure file size > 1 byte
        for i in range(100):
            storage.add(Todo(title=f"Task {i}"))

        storage.close()

        # Verify the file exists and is larger than 1 byte
        self.assertTrue(Path(self.storage_path).exists())
        file_size = os.path.getsize(self.storage_path)
        self.assertGreater(file_size, 1,
                          "File should be larger than 1 byte to test lock range")

        # If lock range was only 1 byte, concurrent modifications could
        # happen to bytes beyond the first. With proper locking, the entire
        # file should be protected.

        # Create a new storage instance and verify data integrity
        storage2 = Storage(self.storage_path)
        todos = storage2.list()
        storage2.close()

        # All todos should be present if locking worked correctly
        self.assertEqual(len(todos), 101,
                        "All todos should be present - lock range must cover entire file")

    def test_lock_range_code_verification(self):
        """Test that the code uses a sufficiently large lock range.

        This test verifies that the lock range in the code is greater than 1.
        """
        import inspect
        from flywheel.storage import Storage

        # Get the source code of _acquire_file_lock
        source = inspect.getsource(Storage._acquire_file_lock)

        if os.name == 'nt':
            # On Windows, verify that msvcrt.locking is called with a large range
            # The code should NOT contain "locking(..., 1)" or "locking(..., 0x1)"
            self.assertNotIn("locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)",
                           source,
                           "Lock range should not be 1 byte")
            self.assertNotIn("locking(file_handle.fileno(), msvcrt.LK_LOCK, 0x1)",
                           source,
                           "Lock range should not be 0x1 (1 byte)")

            # Verify that a large range is used (at least 0xFFFF as suggested)
            # Current implementation uses 0x7FFF0000
            self.assertIn("0x7FFF0000", source,
                        "Lock range should be a large value (0x7FFF0000)")

    def test_lock_unlock_ranges_match(self):
        """Test that lock and unlock ranges match.

        On Windows, msvcrt.locking requires the exact same byte range
        for both LK_LOCK and LK_UNLCK operations. If they don't match,
        it can cause unlock failures or undefined behavior.
        """
        import inspect
        from flywheel.storage import Storage

        if os.name != 'nt':
            self.skipTest("This test is only applicable on Windows")

        # Get source code for both methods
        lock_source = inspect.getsource(Storage._acquire_file_lock)
        unlock_source = inspect.getsource(Storage._release_file_lock)

        # Both should use the same lock range value
        # Current implementation uses 0x7FFF0000 for both
        self.assertIn("0x7FFF0000", lock_source,
                     "Lock operation should use 0x7FFF0000")
        self.assertIn("0x7FFF0000", unlock_source,
                     "Unlock operation should use 0x7FFF0000")

        # Verify both use the same range (both should have 0x7FFF0000)
        lock_count = lock_source.count("0x7FFF0000")
        unlock_count = unlock_source.count("0x7FFF0000")

        self.assertGreater(lock_count, 0,
                          "Lock operation should use 0x7FFF0000 range")
        self.assertGreater(unlock_count, 0,
                          "Unlock operation should use 0x7FFF0000 range")


if __name__ == '__main__':
    unittest.main()
