"""Tests for Issue #351: Windows 文件解锁逻辑存在潜在死锁风险."""

import os
import tempfile
from pathlib import Path
import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestWindowsFileLockRangeConsistency:
    """Test that lock range is consistent between acquire and release.

    Issue #351: If the file size changes between _acquire_file_lock and
    _release_file_lock, using different lock ranges can cause undefined
    behavior or potential deadlock on Windows.

    The solution is to cache the lock_range in _acquire_file_lock and
    reuse it in _release_file_lock.
    """

    @pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
    def test_lock_range_cached_between_acquire_and_release(self):
        """Test that lock_range is cached and reused between acquire and release.

        This test verifies that the lock_range used in _release_file_lock
        matches the one used in _acquire_file_lock, even if the file size
        changes in between.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_lock_consistency.json"

            # Create a storage instance
            storage = Storage(str(storage_path))
            storage.add(Todo(title="Test todo"))

            # Open the file and acquire lock
            with storage_path.open('r+') as f:
                # Acquire the lock
                storage._acquire_file_lock(f)

                # Get the lock range that was used (should be cached)
                # After the fix, storage._lock_range should contain the cached value
                assert hasattr(storage, '_lock_range'), (
                    "Storage should cache _lock_range after acquiring lock"
                )

                cached_lock_range = storage._lock_range
                assert cached_lock_range > 0, "Cached lock range should be positive"

                # Simulate file size change by writing more data
                # This would cause _get_file_lock_range_from_handle to return
                # a different value if we didn't cache it
                f.write(" " * 5000)  # Add 5000 bytes to increase file size
                f.flush()

                # Get what the lock range would be if we recalculated
                new_file_size = storage_path.stat().st_size
                expected_new_range = max(new_file_size, 4096)

                # If the file grew significantly, the recalculated range would be different
                if expected_new_range != cached_lock_range:
                    # Verify that _release_file_lock uses the cached range
                    # by checking that it doesn't raise an error
                    # If it used the new range, we'd get a mismatch error
                    storage._release_file_lock(f)

                    # The cached value should still be the original
                    assert storage._lock_range == cached_lock_range, (
                        "Cached lock range should not change after file size change"
                    )
                else:
                    # File size didn't change enough, just test release
                    storage._release_file_lock(f)

    def test_lock_range_attribute_exists(self):
        """Test that Storage instance has _lock_range attribute.

        This is a simple test to ensure the _lock_range caching mechanism
        is in place.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_lock_range_attr.json"

            # Create a storage instance
            storage = Storage(str(storage_path))

            # Before acquiring lock, _lock_range should not exist or be None
            assert not hasattr(storage, '_lock_range') or storage._lock_range is None, (
                "_lock_range should not be set before acquiring lock"
            )

            # Acquire lock
            with storage_path.open('r') as f:
                storage._acquire_file_lock(f)

                # After acquiring lock, _lock_range should be set
                assert hasattr(storage, '_lock_range'), (
                    "Storage should have _lock_range attribute after acquiring lock"
                )
                assert storage._lock_range is not None, (
                    "_lock_range should not be None after acquiring lock"
                )
                assert isinstance(storage._lock_range, int), (
                    "_lock_range should be an integer"
                )

                # On Windows, it should be a positive value
                if os.name == 'nt':
                    assert storage._lock_range > 0, (
                        "_lock_range should be positive on Windows"
                    )

                # Release lock
                storage._release_file_lock(f)

            # After releasing, the cached value should still exist
            # (we keep it for potential re-use)
            assert hasattr(storage, '_lock_range'), (
                "_lock_range should still exist after releasing lock"
            )

    @pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
    def test_lock_operations_with_size_change(self):
        """Test lock/unlock operations work correctly when file size changes.

        This is an integration test that verifies the actual behavior of
        acquiring and releasing locks when the file size changes.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_size_change.json"

            # Create a storage instance with a small file
            storage = Storage(str(storage_path))
            storage.add(Todo(title="Initial todo"))

            # Get initial file size
            initial_size = storage_path.stat().st_size

            # Perform lock/unlock cycle
            with storage_path.open('r+') as f:
                # Acquire lock with small file
                storage._acquire_file_lock(f)
                initial_lock_range = storage._lock_range

                # Increase file size significantly
                f.write("x" * 10000)  # Add 10000 bytes
                f.flush()

                # Verify file size changed
                new_size = storage_path.stat().st_size
                assert new_size > initial_size, "File size should have increased"

                # Release lock should use the cached lock range
                # This should not raise an error even though file size changed
                storage._release_file_lock(f)

            # If we get here without exception, the test passes
            assert True

    def test_multiple_lock_cycles_with_different_sizes(self):
        """Test multiple lock/acquire cycles with varying file sizes.

        This verifies that the cached lock_range is updated correctly
        across multiple lock cycles.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_multiple_cycles.json"

            # Create a storage instance
            storage = Storage(str(storage_path))

            # First cycle - small file
            storage.add(Todo(title="Todo 1"))
            with storage_path.open('r') as f:
                storage._acquire_file_lock(f)
                first_lock_range = storage._lock_range
                storage._release_file_lock(f)

            # Second cycle - larger file
            storage.add(Todo(title="Todo 2"))
            with storage_path.open('r') as f:
                storage._acquire_file_lock(f)
                second_lock_range = storage._lock_range
                storage._release_file_lock(f)

            # The lock ranges should match for each cycle
            # (or be updated if the implementation resets the cache)
            assert isinstance(first_lock_range, int)
            assert isinstance(second_lock_range, int)

            # Both should be valid positive integers on Windows
            if os.name == 'nt':
                assert first_lock_range > 0
                assert second_lock_range > 0
