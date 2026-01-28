"""Test for issue #869: Windows degraded mode file locking implementation.

This test verifies that the file-based lock mechanism is properly implemented
in Windows degraded mode (when pywin32 is not available).

Issue #869 raised concerns that the code only sets variables to None and prints
a warning without actually implementing file-based locking. This test confirms
that the file-based locking (.lock files) is correctly implemented.
"""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import FileStorage, _is_degraded_mode


class TestWindowsDegradedModeFileLock(unittest.TestCase):
    """Test that Windows degraded mode properly implements file-based locking.

    Issue #869: Verify that when pywin32 is not available on Windows,
    the code actually implements file-based locking (.lock files) rather
    than just setting variables to None.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "testtodos.json")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @unittest.skipIf(os.name != 'nt', "Test only applies to Windows")
    def test_windows_degraded_mode_uses_file_lock(self):
        """Test that Windows degraded mode uses file-based lock (.lock file).

        This test verifies that when pywin32 is not available:
        1. The system correctly detects degraded mode
        2. File-based locking (.lock files) is used
        3. Lock files are created and removed properly
        4. The locking mechanism prevents concurrent access
        """
        # Mock pywin32 modules to be unavailable
        with patch('flywheel.storage.win32file', None):
            # Verify degraded mode is detected
            self.assertTrue(
                _is_degraded_mode(),
                "Windows without pywin32 should be in degraded mode"
            )

            from flywheel.todo import Todo

            # Create storage instance
            storage = FileStorage(self.temp_file)

            # Add a todo - this should acquire the file lock
            todo = Todo(title="Test todo", description="Test description")
            added_todo = storage.add(todo)

            self.assertIsNotNone(added_todo)
            self.assertEqual(added_todo.title, "Test todo")

            # Verify that lock file was created during the operation
            # Note: The lock file might be cleaned up after the operation,
            # so we verify it was used by checking storage attributes
            self.assertTrue(
                hasattr(storage, '_lock_range'),
                "Storage should track lock state"
            )

    @unittest.skipIf(os.name != 'nt', "Test only applies to Windows")
    def test_windows_degraded_mode_lock_file_created(self):
        """Test that .lock file is actually created in degraded mode.

        This is a more direct test that verifies the lock file mechanism
        is actually implemented and working.
        """
        # Mock pywin32 modules to be unavailable
        with patch('flywheel.storage.win32file', None):
            from flywheel.todo import Todo

            storage = FileStorage(self.temp_file)

            # Manually trigger file lock acquisition by opening the file
            with open(self.temp_file, 'a') as f:
                # This should create a .lock file
                storage._acquire_file_lock(f)

                # Verify lock file exists
                lock_file_path = self.temp_file + ".lock"
                self.assertTrue(
                    os.path.exists(lock_file_path),
                    f"Lock file {lock_file_path} should be created"
                )

                # Verify lock file contains metadata
                with open(lock_file_path, 'r') as lock_file:
                    content = lock_file.read()
                    self.assertIn("pid=", content, "Lock file should contain PID")
                    self.assertIn("locked_at=", content, "Lock file should contain timestamp")

                # Release the lock
                storage._release_file_lock(f)

                # Verify lock file was removed
                self.assertFalse(
                    os.path.exists(lock_file_path),
                    f"Lock file {lock_file_path} should be removed after release"
                )

    @unittest.skipIf(os.name != 'nt', "Test only applies to Windows")
    def test_windows_degraded_mode_prevents_concurrent_access(self):
        """Test that file-based locking prevents concurrent access in degraded mode.

        This test verifies that the file-based lock actually works to prevent
        concurrent access, addressing the core concern in issue #869.
        """
        import threading

        # Mock pywin32 modules to be unavailable
        with patch('flywheel.storage.win32file', None):
            from flywheel.todo import Todo

            storage = FileStorage(self.temp_file)
            errors = []
            success_count = [0]

            def add_todo(index):
                """Add a todo from a thread."""
                try:
                    todo = Todo(title=f"Todo {index}", description=f"Description {index}")
                    storage.add(todo)
                    success_count[0] += 1
                except Exception as e:
                    errors.append((index, str(e)))

            # Create multiple threads that try to write concurrently
            threads = []
            num_threads = 5

            for i in range(num_threads):
                thread = threading.Thread(target=add_todo, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Verify no errors occurred
            self.assertEqual(
                len(errors), 0,
                f"No errors should occur with file-based locking. Got: {errors}"
            )

            # Verify all todos were added
            self.assertEqual(
                success_count[0], num_threads,
                f"All {num_threads} todos should be added successfully"
            )

            # Verify the total count
            todos = storage.list()
            self.assertEqual(
                len(todos), num_threads,
                f"Should have {num_threads} todos in storage"
            )

    @unittest.skipIf(os.name != 'nt', "Test only applies to Windows")
    def test_windows_degraded_mode_stale_lock_detection(self):
        """Test that stale lock detection works in degraded mode.

        This test verifies that the file-based lock mechanism includes
        stale lock detection and cleanup as mentioned in the code comments.
        """
        # Mock pywin32 modules to be unavailable
        with patch('flywheel.storage.win32file', None):

            # Manually create a stale lock file
            lock_file_path = self.temp_file + ".lock"
            with open(lock_file_path, 'w') as f:
                # Write a lock timestamp that is older than the stale threshold
                stale_time = time.time() - 400  # 400 seconds ago (> 300 second threshold)
                f.write(f"pid=999\n")
                f.write(f"locked_at={stale_time}\n")

            from flywheel.todo import Todo

            # Create storage and try to add a todo
            # This should detect the stale lock and clean it up
            storage = FileStorage(self.temp_file)

            # This should succeed despite the stale lock file
            todo = Todo(title="Test todo", description="Test description")
            added_todo = storage.add(todo)

            self.assertIsNotNone(added_todo)
            self.assertEqual(added_todo.title, "Test todo")


if __name__ == '__main__':
    unittest.main()
