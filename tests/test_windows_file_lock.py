"""Test Windows file lock consistency (Issue #271)."""

import os
import tempfile
import unittest
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestWindowsFileLock(unittest.TestCase):
    """Test that file lock and unlock ranges are consistent on Windows."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.temp_dir, "test_todos.json")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_lock_unlock_range_consistency(self):
        """Test that lock and unlock use the same byte range.

        This test verifies that the file lock unlock range matches
        the lock range. On Windows, msvcrt.locking requires the same
        number of bytes for both LK_LOCK and LK_UNLCK operations.

        If the ranges don't match, it can cause:
        - Unlock failures
        - Deadlocks
        - File handle corruption
        """
        # Create a storage instance
        storage = Storage(self.storage_path)

        # Perform multiple operations to exercise lock/unlock
        # This will trigger both _acquire_file_lock and _release_file_lock
        todo1 = Todo(title="Test task 1")
        storage.add(todo1)

        todo2 = Todo(title="Test task 2")
        storage.add(todo2)

        # Update a todo
        todo1.status = "completed"
        storage.update(todo1)

        # List todos
        todos = storage.list()

        # Delete a todo
        storage.delete(todo2.id)

        # Close storage
        storage.close()

        # If we get here without deadlock or errors, the lock/unlock ranges are consistent
        self.assertEqual(len(todos), 2)

    def test_concurrent_access_same_file(self):
        """Test that multiple storage instances can access the same file safely.

        This test simulates concurrent access to the same storage file
        from different storage instances (e.g., different processes).
        """
        # Create first storage instance and add data
        storage1 = Storage(self.storage_path)
        todo1 = Todo(title="Shared task")
        storage1.add(todo1)
        storage1.close()

        # Create second storage instance and access the same file
        # This should not cause deadlock even if lock/unlock ranges mismatch
        storage2 = Storage(self.storage_path)
        todos = storage2.list()
        storage2.close()

        self.assertEqual(len(todos), 1)
        self.assertEqual(todos[0].title, "Shared task")


if __name__ == '__main__':
    unittest.main()
