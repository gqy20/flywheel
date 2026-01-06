"""Test for issue #881: Windows degraded mode deadlock risk verification.

This test ensures that the file-based lock mechanism is properly implemented
in degraded mode (when pywin32 or fcntl is not available).

The test verifies:
1. Lock files are created during file operations
2. Lock files contain PID and timestamp information
3. Lock files are properly cleaned up after operations
4. Stale lock detection works correctly
"""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import FileStorage, _is_degraded_mode


class TestDegradedModeLockImplementation(unittest.TestCase):
    """Test that degraded mode properly implements file-based locking.

    Issue #881: Verify that the file-based lock mechanism mentioned in comments
    is actually implemented in the FileStorage class when pywin32/fcntl is unavailable.

    Note: This issue was already fixed by Issues #846 and #874.
    This test serves as verification that the fix is working correctly.
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

    def test_degraded_mode_detected_correctly(self):
        """Test that degraded mode is detected correctly.

        This test verifies that _is_degraded_mode() returns True when
        the optimal locking mechanism (pywin32 on Windows, fcntl on Unix)
        is not available.
        """
        if os.name == 'nt':
            # Windows: Mock pywin32 to be unavailable
            with patch('flywheel.storage.win32file', None):
                self.assertTrue(
                    _is_degraded_mode(),
                    "Windows without pywin32 should be in degraded mode"
                )
        else:
            # Unix: Mock fcntl to be unavailable
            with patch('flywheel.storage.fcntl', None):
                self.assertTrue(
                    _is_degraded_mode(),
                    "Unix without fcntl should be in degraded mode"
                )

    def test_degraded_mode_storage_works(self):
        """Test that FileStorage works correctly in degraded mode.

        This test verifies that:
        1. FileStorage can be created in degraded mode
        2. Basic operations (add, get, list) work correctly
        3. The file-based lock mechanism is being used
        """
        if os.name == 'nt':
            # Windows: Mock pywin32 to be unavailable
            context_manager = patch('flywheel.storage.win32file', None)
        else:
            # Unix: Mock fcntl to be unavailable
            context_manager = patch('flywheel.storage.fcntl', None)

        with context_manager:
            # Verify degraded mode is detected
            self.assertTrue(
                _is_degraded_mode(),
                "Should be in degraded mode when optimal locking is unavailable"
            )

            # Create storage instance (should not raise an error)
            storage = FileStorage(self.temp_file)

            # Verify that storage can be used
            from flywheel.todo import Todo

            # Add a todo
            todo = Todo(title="Test todo", description="Test description")
            added_todo = storage.add(todo)

            self.assertIsNotNone(added_todo)
            self.assertEqual(added_todo.title, "Test todo")

            # Verify the todo was persisted
            retrieved_todo = storage.get(added_todo.id)
            self.assertIsNotNone(retrieved_todo)
            self.assertEqual(retrieved_todo.title, "Test todo")

    def test_degraded_mode_lock_metadata(self):
        """Test that degraded mode lock files contain proper metadata.

        This test verifies that lock files contain:
        1. PID (process ID)
        2. Timestamp (when the lock was acquired)
        """
        if os.name == 'nt':
            # Windows: Mock pywin32 to be unavailable
            context_manager = patch('flywheel.storage.win32file', None)
            lock_file_path = self.temp_file + ".lock"
        else:
            # Unix: Mock fcntl to be unavailable
            context_manager = patch('flywheel.storage.fcntl', None)
            lock_file_path = self.temp_file + ".lock"  # Unix uses directory

        with context_manager:
            from flywheel.todo import Todo

            # Create storage instance
            storage = FileStorage(self.temp_file)

            # Manually trigger lock acquisition to inspect lock file
            storage._lock.acquire()

            try:
                # Open file handle to trigger lock acquisition
                with open(self.temp_file, 'a+') as f:
                    storage._acquire_file_lock(f)

                    # Verify lock file exists
                    self.assertTrue(
                        os.path.exists(lock_file_path),
                        f"Lock file {lock_file_path} should exist when lock is held"
                    )

                    # Read and verify lock file content
                    if os.name == 'nt':
                        # Windows: Lock file is a regular file with PID and timestamp
                        with open(lock_file_path, 'r') as lock_file:
                            content = lock_file.read()

                        # Verify content contains PID and timestamp
                        self.assertIn("pid=", content, "Lock file should contain PID")
                        self.assertIn("locked_at=", content, "Lock file should contain timestamp")

                        # Extract and validate PID
                        pid_line = [line for line in content.split('\n') if line.startswith('pid=')][0]
                        lock_pid = int(pid_line.split('=')[1])
                        self.assertEqual(lock_pid, os.getpid(), "PID should match current process")

                        # Extract and validate timestamp
                        time_line = [line for line in content.split('\n') if line.startswith('locked_at=')][0]
                        locked_at = float(time_line.split('=')[1])
                        self.assertGreater(locked_at, 0, "Timestamp should be positive")
                        self.assertLessEqual(locked_at, time.time(), "Timestamp should not be in the future")
                    else:
                        # Unix: Lock file is a directory with a pid file inside
                        pid_file = os.path.join(lock_file_path, "pid")
                        self.assertTrue(
                            os.path.exists(pid_file),
                            "PID file should exist in lock directory"
                        )

                        with open(pid_file, 'r') as pf:
                            pid_str = pf.read().strip()
                            lock_pid = int(pid_str)
                            self.assertEqual(lock_pid, os.getpid(), "PID should match current process")

                    # Release lock
                    storage._release_file_lock(f)

            finally:
                storage._lock.release()

            # After releasing, lock file should be cleaned up
            self.assertFalse(
                os.path.exists(lock_file_path),
                "Lock file should be cleaned up after release"
            )

    def test_degraded_mode_stale_lock_detection(self):
        """Test that degraded mode can detect and cleanup stale locks.

        This test verifies that the stale lock detection mechanism works:
        1. Old lock files are detected
        2. Stale locks are cleaned up automatically
        3. New processes can acquire locks after cleanup
        """
        if os.name == 'nt':
            # Windows: Mock pywin32 to be unavailable
            context_manager = patch('flywheel.storage.win32file', None)
            lock_file_path = self.temp_file + ".lock"
        else:
            # Unix: Mock fcntl to be unavailable
            context_manager = patch('flywheel.storage.fcntl', None)
            lock_file_path = self.temp_file + ".lock"

        with context_manager:
            from flywheel.todo import Todo

            # Create a fake stale lock
            if os.name == 'nt':
                # Windows: Create a stale lock file with old timestamp
                old_timestamp = time.time() - 400  # 400 seconds ago (> 5 min threshold)

                with open(lock_file_path, 'w') as lock_file:
                    lock_file.write(f"pid=99999\n")  # Non-existent PID
                    lock_file.write(f"locked_at={old_timestamp}\n")
            else:
                # Unix: Create a stale lock directory
                os.makedirs(lock_file_path, exist_ok=True)
                pid_file = os.path.join(lock_file_path, "pid")
                with open(pid_file, 'w') as pf:
                    pf.write("99999")  # Non-existent PID

            # Verify lock file exists
            self.assertTrue(os.path.exists(lock_file_path), "Stale lock file should exist")

            # Create storage instance - it should clean up the stale lock
            storage = FileStorage(self.temp_file, lock_timeout=5.0)

            # Perform an operation - this should work after stale lock cleanup
            todo = Todo(title="Test todo", description="Test description")

            # This should succeed with proper stale lock cleanup
            try:
                storage.add(todo)
                success = True
            except RuntimeError as e:
                if "timed out" in str(e).lower():
                    # Stale lock cleanup failed - this would indicate a bug
                    success = False
                else:
                    raise

            self.assertTrue(success, "Should be able to acquire lock after stale lock cleanup")

    def test_degraded_mode_concurrent_access_safety(self):
        """Test that degraded mode prevents concurrent access issues.

        This test verifies that the file-based lock mechanism properly
        serializes concurrent access to prevent data corruption.
        """
        import threading

        if os.name == 'nt':
            # Windows: Mock pywin32 to be unavailable
            context_manager = patch('flywheel.storage.win32file', None)
        else:
            # Unix: Mock fcntl to be unavailable
            context_manager = patch('flywheel.storage.fcntl', None)

        with context_manager:
            from flywheel.todo import Todo

            errors = []
            success_count = [0]

            def add_todo(index):
                """Add a todo from a thread."""
                try:
                    # Each thread creates its own storage instance
                    # (simulating multiple processes)
                    storage = FileStorage(self.temp_file)
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
                thread.join(timeout=10)

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
            storage = FileStorage(self.temp_file)
            todos = storage.list()
            self.assertEqual(
                len(todos), num_threads,
                f"Should have {num_threads} todos in storage"
            )


if __name__ == '__main__':
    unittest.main()
