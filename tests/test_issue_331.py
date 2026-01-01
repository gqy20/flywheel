"""Test for Issue #331 - Race condition in file size calculation for Windows lock.

This test verifies that the Windows file locking mechanism does not have
a race condition when calculating the file size for the lock range.

The issue: Calculating the lock range based on the current file size creates
a race condition. If the file grows between `seek`/`tell` and `msvcrt.locking`,
the new data will not be locked.

The fix: Use a sufficiently large static range (0xFFFF0000 or similar) for
LK_LOCK to cover the entire file regardless of size.
"""

import os
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

# Skip this test on non-Windows platforms
pytestmark = pytest.mark.skipif(
    os.name != 'nt', reason="Windows-specific test"
)


class TestWindowsLockRaceCondition:
    """Test for race condition in Windows file locking."""

    def test_lock_range_should_use_static_value_not_file_size(self):
        """Test that lock range uses a static value instead of dynamic file size.

        This test ensures that the Windows file lock does not have a race
        condition by using a static lock range instead of calculating the
        range based on file size.
        """
        # Import here to avoid import errors on non-Windows
        try:
            import msvcrt
        except ImportError:
            pytest.skip("msvcrt not available (not on Windows)")

        from flywheel.storage import Storage

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_lock_race.json"
            storage = Storage(str(storage_path))

            # Get the lock range that would be used
            # We need to test that the lock range is static and large enough
            # to cover the file regardless of its current size

            # Open a test file to check the lock range calculation
            test_file = Path(tmpdir) / "test_file.txt"
            test_file.write_text("initial content")

            with test_file.open('r+') as f:
                # Get the lock range using the internal method
                lock_range = storage._get_file_lock_range_from_handle(f)

                # The lock range should be a large static value (0xFFFF0000 or similar)
                # NOT based on the current file size
                # 0xFFFF0000 = 4294901760 bytes (~4GB)

                # Check that the lock range is sufficiently large
                # A static lock range should be at least 0xFFFF0000 (4GB)
                # or use another sufficiently large static value
                expected_min_range = 0xFFFF0000  # ~4GB

                # This assertion will fail if the lock range is based on file size
                # (which would be small for a small test file)
                assert lock_range >= expected_min_range, (
                    f"Lock range ({lock_range}) is too small and likely based on "
                    f"file size. This creates a race condition if the file grows "
                    f"between size calculation and locking. Expected at least "
                    f"{expected_min_range} bytes (0xFFFF0000)."
                )

            storage.close()

    def test_lock_range_handles_large_files(self):
        """Test that lock range works correctly for large files.

        This test verifies that the lock range is a static value that
        works for both small and large files.
        """
        try:
            import msvcrt
        except ImportError:
            pytest.skip("msvcrt not available (not on Windows)")

        from flywheel.storage import Storage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_large_file.json"
            storage = Storage(str(storage_path))

            # Test with a small file
            small_file = Path(tmpdir) / "small.txt"
            small_file.write_text("small")
            with small_file.open('r+') as f:
                small_lock_range = storage._get_file_lock_range_from_handle(f)

            # Test with a larger file
            large_file = Path(tmpdir) / "large.txt"
            large_file.write_text("x" * 10000)  # 10KB
            with large_file.open('r+') as f:
                large_lock_range = storage._get_file_lock_range_from_handle(f)

            # The lock range should be the same static value for both files
            # If it varies based on file size, we have a race condition
            assert small_lock_range == large_lock_range, (
                f"Lock range varies by file size (small={small_lock_range}, "
                f"large={large_lock_range}). This indicates a race condition "
                "where the lock range is calculated based on current file size."
            )

            # Both should use a large static value
            assert small_lock_range >= 0xFFFF0000, (
                f"Lock range ({small_lock_range}) is too small. Expected at "
                f"least 0xFFFF0000 bytes to prevent race conditions."
            )

            storage.close()

    def test_concurrent_write_safety_with_static_lock_range(self):
        """Test that concurrent writes are safe with a static lock range.

        This test simulates the race condition scenario where a file grows
        between size calculation and locking. With a static lock range,
        this should not be an issue.
        """
        try:
            import msvcrt
        except ImportError:
            pytest.skip("msvcrt not available (not on Windows)")

        from flywheel.storage import Storage
        from flywheel.todo import Todo

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_concurrent.json"
            storage = Storage(str(storage_path))

            # Add initial todos
            for i in range(5):
                storage.add(Todo(title=f"Todo {i}", status="pending"))

            errors = []
            success_count = [0]

            def add_todos_thread(thread_id):
                """Thread function that adds todos concurrently."""
                try:
                    for i in range(10):
                        todo = Todo(
                            title=f"Thread {thread_id} Todo {i}",
                            status="pending"
                        )
                        storage.add(todo)
                        success_count[0] += 1
                except Exception as e:
                    errors.append((thread_id, e))

            # Create multiple threads to simulate concurrent access
            threads = []
            num_threads = 3
            for i in range(num_threads):
                t = threading.Thread(target=add_todos_thread, args=(i,))
                threads.append(t)
                t.start()

            # Wait for all threads to complete
            for t in threads:
                t.join()

            # Check for errors
            assert len(errors) == 0, (
                f"Concurrent writes failed with errors: {errors}. "
                "This may indicate a race condition in file locking."
            )

            # Verify all todos were added
            todos = storage.list()
            expected_count = 5 + (num_threads * 10)  # initial + threads
            assert len(todos) == expected_count, (
                f"Expected {expected_count} todos, got {len(todos)}. "
                "Some todos may have been lost due to race condition."
            )

            storage.close()
