"""Test Windows lock range synchronization with file growth (Issue #281)."""

import os
import tempfile
import json
from pathlib import Path
import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestWindowsLockRange:
    """Test that Windows file locks cover the entire file even after growth."""

    def test_windows_lock_range_with_large_fixed_value(self):
        """Test that Windows uses a sufficiently large fixed lock range.

        The issue: Windows msvcrt.locking locks a specific byte range.
        If the file grows beyond this range after locking, the new data
        won't be locked, potentially causing data corruption.

        Solution: Use a large fixed range (e.g., 0xFFFF0000) instead of
        the actual file size to ensure future growth is also locked.
        """
        # This test verifies the fix uses a large fixed lock range
        # We can't test actual multi-process locking in a unit test,
        # but we can verify the lock range is sufficiently large

        # Create a temporary storage file
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_lock.json"
            storage = Storage(str(storage_path))

            # Get the lock range that would be used
            if os.name == 'nt':
                lock_range = storage._get_windows_lock_range(storage.path)
                # The lock range should be a large fixed value (0xFFFF0000 or similar)
                # to ensure it covers file growth
                # With the fix, this should be >= 0xFFFF0000 (about 4GB)
                # Or at least much larger than the actual file size
                actual_file_size = storage_path.stat().st_size if storage_path.exists() else 0

                # The fix should use a large fixed range instead of actual file size
                # Verify it's using a sufficiently large value
                assert lock_range >= 0xFFFF0000, (
                    f"Lock range {lock_range} is too small. "
                    f"Should use large fixed range (0xFFFF0000) to handle file growth. "
                    f"Actual file size: {actual_file_size}"
                )
            else:
                # On Unix, we don't have this issue
                # Just verify the method exists and doesn't crash
                lock_range = storage._get_windows_lock_range(storage.path)
                assert isinstance(lock_range, int)
                assert lock_range >= 0

    def test_windows_lock_range_handles_nonexistent_file(self):
        """Test that lock range calculation works for non-existent files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "nonexistent.json"
            storage = Storage(str(storage_path))

            # File doesn't exist yet - should still return a valid lock range
            lock_range = storage._get_windows_lock_range(storage_path)
            assert isinstance(lock_range, int)
            assert lock_range > 0

            # With the fix, should return large fixed range on Windows
            if os.name == 'nt':
                assert lock_range >= 0xFFFF0000, (
                    f"Lock range for non-existent file should use large fixed value, "
                    f"got {lock_range}"
                )

    def test_windows_lock_range_handles_large_file(self):
        """Test that lock range is sufficient even for large files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_large.json"

            # Create a large file (larger than typical 1MB default)
            large_data = {"todos": [], "next_id": 1, "metadata": {"checksum": ""}}
            for i in range(10000):
                large_data["todos"].append({
                    "id": i,
                    "title": f"Task {i}" * 100,  # Make each todo large
                    "status": "pending"
                })

            # Write the large file
            with open(storage_path, 'w') as f:
                json.dump(large_data, f)

            file_size = storage_path.stat().st_size

            storage = Storage(str(storage_path))
            lock_range = storage._get_windows_lock_range(storage.path)

            # On Windows with the fix, should use large fixed range
            # regardless of actual file size
            if os.name == 'nt':
                assert lock_range >= 0xFFFF0000, (
                    f"Lock range should be large fixed value (0xFFFF0000), "
                    f"not actual file size. File size: {file_size}, Lock range: {lock_range}"
                )
            else:
                # On Unix, just verify it's valid
                assert isinstance(lock_range, int)
                assert lock_range > 0

    def test_windows_lock_range_consistency(self):
        """Test that lock and unlock use the same range."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_consistency.json"
            storage = Storage(str(storage_path))

            # Add some todos to create a file
            storage.add(Todo(title="Test task"))
            storage.add(Todo(title="Another task"))

            # Verify lock range is consistent
            lock_range1 = storage._get_windows_lock_range(storage.path)
            lock_range2 = storage._get_windows_lock_range(storage.path)

            assert lock_range1 == lock_range2, (
                f"Lock range should be consistent: {lock_range1} != {lock_range2}"
            )

            # On Windows, should be large fixed value
            if os.name == 'nt':
                assert lock_range1 >= 0xFFFF0000
