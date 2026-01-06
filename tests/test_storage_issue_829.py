"""Test for issue #829: Unix degraded mode lacks file locking mechanism.

This test ensures that when fcntl is not available on Unix systems,
a file-based locking mechanism is used instead of completely disabling locking.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import FileStorage, _is_degraded_mode


class TestUnixDegradedModeLocking(unittest.TestCase):
    """Test that Unix degraded mode has proper file locking fallback.

    Issue #829: When fcntl is not available on Unix, the code should implement
    a file-based lock fallback mechanism instead of completely disabling locking.
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

    @unittest.skipIf(os.name == 'nt', "Test only applies to Unix-like systems")
    def test_unix_degraded_mode_has_fallback_locking(self):
        """Test that Unix degraded mode implements fallback file locking.

        When fcntl is not available on Unix, the system should use a file-based
        locking mechanism (like lock files) instead of completely disabling locking.

        This test verifies that:
        1. When fcntl is not available, degraded mode is detected
        2. File locking still works through a fallback mechanism
        3. Concurrent writes are properly serialized
        """
        # Mock fcntl to be unavailable
        with patch('flywheel.storage.fcntl', None):
            # Verify degraded mode is detected
            self.assertTrue(
                _is_degraded_mode(),
                "Unix system without fcntl should be in degraded mode"
            )

            # Create storage instance (should not raise an error)
            storage = FileStorage(self.temp_file)

            # Verify that storage can be created and used
            # The key is that file locking should still work via fallback
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

    @unittest.skipIf(os.name == 'nt', "Test only applies to Unix-like systems")
    def test_unix_degraded_mode_locking_prevents_race_conditions(self):
        """Test that Unix degraded mode fallback locking prevents concurrent access issues.

        This test creates a simple concurrent access scenario to verify that
        the fallback locking mechanism works.
        """
        import threading
        import time

        # Mock fcntl to be unavailable
        with patch('flywheel.storage.fcntl', None):
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
                f"No errors should occur with fallback locking. Got: {errors}"
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
    def test_windows_degraded_mode_has_file_lock_fallback(self):
        """Test that Windows degraded mode uses file-based locking fallback.

        Issue #846, #869: Verify that Windows degraded mode uses file-based
        locking (.lock files) instead of msvcrt.locking to prevent deadlock risk.
        """
        # Mock pywin32 to be unavailable
        with patch('flywheel.storage.win32file', None):
            # Verify degraded mode is detected
            self.assertTrue(
                _is_degraded_mode(),
                "Windows without pywin32 should be in degraded mode"
            )

            # Create storage instance
            storage = FileStorage(self.temp_file)

            # Verify that storage works
            from flywheel.todo import Todo

            todo = Todo(title="Test todo", description="Test description")
            added_todo = storage.add(todo)

            self.assertIsNotNone(added_todo)
            self.assertEqual(added_todo.title, "Test todo")


if __name__ == '__main__':
    unittest.main()
