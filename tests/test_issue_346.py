"""Tests for Issue #346: Windows file lock range exceeding file size."""

import os
import tempfile
from pathlib import Path
import pytest

from flywheel.storage import Storage


class TestWindowsFileLockRange:
    """Test that file lock range does not exceed file size on Windows."""

    def test_file_lock_range_does_not_exceed_file_size(self):
        """Test that _get_file_lock_range_from_handle returns a safe lock range.

        On Windows, msvcrt.locking requires the lock range to not exceed the
        current file size. This test verifies that the lock range is safe to use.
        """
        # Create a temporary storage with a small file
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"

            # Create a storage instance with a small file
            storage = Storage(str(storage_path))

            # Add a small todo to create a file with known size
            from flywheel.todo import Todo
            storage.add(Todo(title="Test todo"))

            # Get the actual file size
            actual_file_size = storage_path.stat().st_size

            # Get the lock range that would be used
            with storage_path.open('r') as f:
                lock_range = storage._get_file_lock_range_from_handle(f)

            # On Windows, verify that lock range is reasonable
            # The lock range should not exceed the file size by too much
            # or use a size that would cause IOError (Error 33)
            if os.name == 'nt':
                # On Windows, the lock range should be based on file size
                # or use a platform-appropriate locking mechanism
                # We verify that the lock range is not excessively larger than file size
                # A reasonable multiplier would be 2x or using actual file size
                # The old implementation used 0xFFFF0000 (~4GB) which is problematic
                # We expect the new implementation to use file size or a reasonable multiple
                assert lock_range <= max(actual_file_size * 2, 4096), (
                    f"Lock range {lock_range} exceeds 2x file size {actual_file_size} "
                    f"or minimum 4KB, which may cause IOError on Windows"
                )
            else:
                # On Unix, we don't use lock ranges (fcntl.flock doesn't need it)
                # The value is ignored, so any value is acceptable
                assert isinstance(lock_range, int)
                assert lock_range > 0

    def test_file_lock_with_empty_file(self):
        """Test file locking behavior with an empty file.

        Even with an empty file, the lock range should be safe.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_empty.json"

            # Create an empty file
            storage_path.touch()

            # Create storage instance
            storage = Storage(str(storage_path))

            # Get file size (should be 0 or small)
            actual_file_size = storage_path.stat().st_size

            # Get the lock range
            with storage_path.open('r') as f:
                lock_range = storage._get_file_lock_range_from_handle(f)

            # On Windows, lock range should still be safe even with empty file
            if os.name == 'nt':
                # Should handle empty file gracefully
                # Either use file size (0) or a reasonable minimum
                assert lock_range >= 0, "Lock range should not be negative"
                # Should not use excessively large value for empty file
                assert lock_range <= 4096, (
                    f"Lock range {lock_range} for empty file is too large, "
                    f"may cause IOError on Windows"
                )

    def test_acquire_and_release_file_lock_with_small_file(self):
        """Test that file lock can be acquired and released on a small file.

        This is a regression test for Issue #346.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_lock.json"

            # Create a small file
            storage = Storage(str(storage_path))
            from flywheel.todo import Todo
            storage.add(Todo(title="Small todo"))

            # Test that we can acquire and release lock without IOError
            with storage_path.open('r') as f:
                # This should not raise IOError (Error 33) on Windows
                storage._acquire_file_lock(f)
                storage._release_file_lock(f)

            # If we get here without exception, the test passes
            assert True
