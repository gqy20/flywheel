"""Test for Issue #684: Verify _lock_range is properly initialized.

This test ensures that the _lock_range attribute is initialized in __init__
to prevent AttributeError when referenced later.

Issue: https://github.com/anthropics/flywheel/issues/684
"""
import tempfile
import os
from pathlib import Path

from flywheel.storage import FileStorage


def test_lock_range_is_initialized():
    """Test that _lock_range attribute is initialized in __init__.

    This test verifies the fix for Issue #684 where _lock_range was
    declared as a type hint but not initialized, causing AttributeError.

    The attribute should be:
    - Initialized to 0 on Unix systems
    - Initialized to 0 on Windows systems (will be updated to tuple when lock is acquired)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test_todos.json")

        # Create FileStorage instance
        storage = FileStorage(test_file)

        # Verify _lock_range attribute exists and is initialized
        assert hasattr(storage, '_lock_range'), \
            "_lock_range attribute should exist after initialization"

        # On all systems, it should be initialized to 0 initially
        assert storage._lock_range == 0, \
            f"_lock_range should be initialized to 0, got {storage._lock_range}"

        # Verify it's the correct type (int initially, may become tuple on Windows after lock acquisition)
        assert isinstance(storage._lock_range, (int, tuple)), \
            f"_lock_range should be int or tuple, got {type(storage._lock_range)}"


def test_lock_range_initialized_in_load_without_sync():
    """Test that _lock_range is initialized when using load_without_sync.

    The load_without_sync classmethod should also properly initialize
    the _lock_range attribute.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test_todos_load.json")

        # Create a FileStorage instance using load_without_sync
        storage = FileStorage.load_without_sync(test_file)

        # Verify _lock_range attribute exists and is initialized
        assert hasattr(storage, '_lock_range'), \
            "_lock_range attribute should exist after load_without_sync"

        assert storage._lock_range == 0, \
            f"_lock_range should be initialized to 0, got {storage._lock_range}"


if __name__ == "__main__":
    test_lock_range_is_initialized()
    test_lock_range_initialized_in_load_without_sync()
    print("All tests passed!")
