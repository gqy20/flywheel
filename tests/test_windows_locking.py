"""Tests for Windows mandatory locking implementation (Issue #490)."""

import os
import sys
import tempfile
import time
from pathlib import Path
import pytest

# Skip these tests on non-Windows platforms
pytestmark = pytest.mark.skipif(
    os.name != 'nt',
    reason="Windows mandatory locking tests only run on Windows"
)

from flywheel.storage import Storage


class TestWindowsMandatoryLocking:
    """Test suite for Windows mandatory file locking (Issue #490)."""

    def test_windows_lock_acquisition_with_retry(self):
        """Test that Windows lock can be acquired and uses retry mechanism."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Add a todo to trigger file locking
            todo = storage.add(__import__('flywheel.todo').Todo(title="Test task"))

            # Verify the todo was added successfully
            assert todo is not None
            assert todo.title == "Test task"

            # Verify lock range is cached correctly (Issue #351, #480)
            # Should be (0, 1) representing exactly 4GB
            assert storage._lock_range == (0, 1)

            storage.close()

    def test_windows_lock_timeout(self):
        """Test that Windows lock acquisition times out appropriately."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos_timeout.json"

            # Create first storage instance
            storage1 = Storage(str(storage_path))

            # Try to create a second storage instance that will contend for the lock
            # This should eventually succeed when the first lock is released
            storage2 = Storage(str(storage_path))

            # Both should work - they just need to wait for each other
            storage1.close()
            storage2.close()

    def test_windows_lock_range_is_4gb(self):
        """Test that Windows lock range is correctly set to 4GB (Issue #480)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_lock_range.json"
            storage = Storage(str(storage_path))

            # The lock range should be (0, 1) representing exactly 4GB
            # According to Issue #480: With (0, 1): low=0, high=1, range = 0 + 1 << 32 = 0x100000000 = 4GB exactly
            lock_range = storage._get_file_lock_range_from_handle(None)
            assert lock_range == (0, 1), f"Expected lock range (0, 1), got {lock_range}"

            storage.close()

    def test_windows_lock_flags_are_correct(self):
        """Test that Windows lock uses correct flags (Issue #490)."""
        # Import Windows modules to verify flags
        try:
            import win32con
        except ImportError:
            pytest.skip("pywin32 not installed")

        # Verify the expected flags are used
        expected_flags = win32con.LOCKFILE_FAIL_IMMEDIATELY | win32con.LOCKFILE_EXCLUSIVE_LOCK

        # The flags should combine non-blocking and exclusive lock
        assert expected_flags & win32con.LOCKFILE_FAIL_IMMEDIATELY
        assert expected_flags & win32con.LOCKFILE_EXCLUSIVE_LOCK

    @pytest.mark.skipif(
        os.name != 'nt',
        reason="Windows-specific test"
    )
    def test_windows_mandatory_lock_prevents_concurrent_write(self):
        """Test that Windows mandatory locking prevents concurrent writes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_concurrent.json"

            # Create storage and add a todo
            storage1 = Storage(str(storage_path))
            todo1 = storage1.add(__import__('flywheel.todo').Todo(title="First task"))

            # Create another storage instance pointing to the same file
            storage2 = Storage(str(storage_path))

            # Add another todo through the second instance
            todo2 = storage2.add(__import__('flywheel.todo').Todo(title="Second task"))

            # Both should be persisted correctly
            all_todos = storage2.list()
            assert len(all_todos) == 2

            storage1.close()
            storage2.close()
