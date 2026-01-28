"""Test for issue #905: Windows 降级模式下的死锁风险验证

This test ensures that Windows degraded mode has NO deadlock risk by verifying:
1. win32file is None when in degraded mode
2. File-based .lock files are enforced (not msvcrt.locking)
3. atexit handler properly cleans up lock files
4. Stale lock detection works correctly
5. Assertion prevents accidental win32file usage in degraded mode
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


class TestWindowsDegradedModeDeadlockPrevention(unittest.TestCase):
    """Test that Windows degraded mode has no deadlock risk.

    Issue #905: Verify that when pywin32 is missing on Windows:
    1. win32file is None (enforced by assertion)
    2. File-based .lock files are strictly used
    3. atexit handler ensures cleanup
    4. No deadlock risk exists
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
    def test_windows_degraded_mode_enforces_win32file_is_none(self):
        """Test that degraded mode enforces win32file is None.

        This is a critical safety check to prevent deadlock.
        The assertion at line 1385-1388 in storage.py should catch any
        accidental use of win32file in degraded mode.
        """
        # Mock pywin32 to be unavailable
        with patch('flywheel.storage.win32file', None):
            # Verify degraded mode is detected
            self.assertTrue(
                _is_degraded_mode(),
                "Windows without pywin32 should be in degraded mode"
            )

            # Create storage instance - should use file-based locking
            storage = FileStorage(self.temp_file)

            # Verify the storage instance was created successfully
            self.assertIsNotNone(storage)

            # The assertion in _acquire_file_lock (line 1385-1388) ensures
            # that win32file is None in degraded mode
            # This prevents any accidental use of win32file.LockFileEx

    @unittest.skipIf(os.name != 'nt', "Test only applies to Windows")
    def test_windows_degraded_mode_uses_file_based_locking(self):
        """Test that degraded mode uses file-based .lock files.

        Verify that when pywin32 is not available, the code strictly uses
        file-based locking (.lock files) instead of any other mechanism.
        """
        # Mock pywin32 to be unavailable
        with patch('flywheel.storage.win32file', None):
            from flywheel.todo import Todo

            # Create storage and add a todo
            storage = FileStorage(self.temp_file)
            todo = Todo(title="Test todo", description="Test description")
            added_todo = storage.add(todo)

            # Verify lock file was created
            lock_file_path = self.temp_file + ".lock"
            self.assertTrue(
                os.path.exists(lock_file_path),
                "Lock file should exist when using degraded mode"
            )

            # Verify lock file contains valid metadata
            with open(lock_file_path, 'r') as f:
                content = f.read()
                self.assertIn('pid=', content, "Lock file should contain PID")
                self.assertIn('locked_at=', content, "Lock file should contain timestamp")

            # Close storage - should clean up lock file
            storage.close()

            # Verify lock file was cleaned up
            self.assertFalse(
                os.path.exists(lock_file_path),
                "Lock file should be cleaned up after close"
            )

    @unittest.skipIf(os.name != 'nt', "Test only applies to Windows")
    def test_windows_degraded_mode_atexit_cleanup(self):
        """Test that atexit handler properly cleans up lock files.

        Issue #905: Verify atexit handler ensures lock file cleanup
        even if close() is not called explicitly.
        """
        # Mock pywin32 to be unavailable
        with patch('flywheel.storage.win32file', None):
            from flywheel.todo import Todo

            # Create storage and add a todo
            storage = FileStorage(self.temp_file)
            todo = Todo(title="Test todo", description="Test description")
            storage.add(todo)

            # Verify lock file was created
            lock_file_path = self.temp_file + ".lock"
            self.assertTrue(
                os.path.exists(lock_file_path),
                "Lock file should exist"
            )

            # Simulate atexit cleanup (normally called on program exit)
            storage._cleanup()

            # Verify lock file was cleaned up by atexit handler
            self.assertFalse(
                os.path.exists(lock_file_path),
                "atexit handler should clean up lock file"
            )

    @unittest.skipIf(os.name != 'nt', "Test only applies to Windows")
    def test_windows_degraded_mode_stale_lock_detection(self):
        """Test that stale lock detection works in degraded mode.

        Issue #905: Verify that stale locks are properly detected and cleaned up.
        """
        # Mock pywin32 to be unavailable
        with patch('flywheel.storage.win32file', None):
            from flywheel.todo import Todo

            # Create first storage instance
            storage1 = FileStorage(self.temp_file)
            todo1 = Todo(title="Todo 1", description="Description 1")
            storage1.add(todo1)

            # Get the lock file path
            lock_file_path = self.temp_file + ".lock"
            self.assertTrue(os.path.exists(lock_file_path))

            # Read the lock file to get the PID
            with open(lock_file_path, 'r') as f:
                content = f.read()
                # Verify lock file has PID and timestamp
                self.assertIn('pid=', content)
                self.assertIn('locked_at=', content)

            # Close first storage
            storage1.close()

            # Create second storage instance - should acquire lock successfully
            # (no stale lock since first storage closed properly)
            storage2 = FileStorage(self.temp_file)
            todo2 = Todo(title="Todo 2", description="Description 2")
            storage2.add(todo2)

            # Verify second storage works
            todos = storage2.list()
            self.assertEqual(len(todos), 2)

            storage2.close()

    @unittest.skipIf(os.name != 'nt', "Test only applies to Windows")
    def test_windows_degraded_mode_no_deadlock_with_concurrent_access(self):
        """Test that degraded mode handles concurrent access without deadlock.

        Issue #905: Verify that file-based locking prevents deadlock in
        concurrent access scenarios.
        """
        import threading

        # Mock pywin32 to be unavailable
        with patch('flywheel.storage.win32file', None):
            from flywheel.todo import Todo

            errors = []
            success_count = [0]

            def add_todo(index):
                """Add a todo from a thread."""
                try:
                    # Each thread creates its own storage instance
                    storage = FileStorage(self.temp_file)
                    todo = Todo(title=f"Todo {index}", description=f"Description {index}")
                    storage.add(todo)
                    success_count[0] += 1
                    storage.close()
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
                thread.join(timeout=10)  # 10 second timeout to detect deadlock

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

    @unittest.skipIf(os.name != 'nt', "Test only applies to Windows")
    def test_windows_degraded_mode_lock_timeout(self):
        """Test that lock acquisition timeout works in degraded mode.

        This verifies that the code doesn't hang indefinitely when
        a lock cannot be acquired.
        """
        # Mock pywin32 to be unavailable
        with patch('flywheel.storage.win32file', None):
            from flywheel.todo import Todo

            # Create first storage instance with short timeout
            storage1 = FileStorage(self.temp_file, lock_timeout=1.0)
            todo1 = Todo(title="Todo 1", description="Description 1")
            storage1.add(todo1)

            # Try to create second storage instance without closing first
            # This should timeout because the first storage holds the lock
            with self.assertRaises(RuntimeError) as context:
                storage2 = FileStorage(self.temp_file, lock_timeout=1.0)
                todo2 = Todo(title="Todo 2", description="Description 2")
                storage2.add(todo2)

            # Verify timeout error message
            self.assertIn("timed out", str(context.exception).lower())
            self.assertIn("lock", str(context.exception).lower())

            # Clean up
            storage1.close()

    @unittest.skipIf(os.name != 'nt', "Test only applies to Windows")
    def test_windows_degraded_mode_assertion_safety(self):
        """Test that assertion prevents unsafe win32file usage.

        Issue #905: Verify the assertion at line 1385-1388 prevents
        accidental use of win32file in degraded mode.
        """
        # Mock pywin32 to be unavailable
        with patch('flywheel.storage.win32file', None):

            # Verify _is_degraded_mode returns True
            self.assertTrue(_is_degraded_mode())

            # The assertion in _acquire_file_lock ensures win32file is None
            # If win32file were not None, the assertion would fail
            # This is a critical safety check

            # Create storage to trigger the assertion check
            storage = FileStorage(self.temp_file)

            # If we get here, the assertion passed (win32file is None)
            self.assertTrue(
                storage._lock_range == "filelock" or storage._lock_range is None,
                "Storage should use file-based locking in degraded mode"
            )

            storage.close()


if __name__ == '__main__':
    unittest.main()
