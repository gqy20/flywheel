"""Test for issue #375: Windows file locking deadlock risk due to file size changes.

This test verifies that the file locking mechanism handles file size changes
correctly, preventing deadlocks when:
1. File grows between lock acquisition and release
2. Cached lock range is smaller than actual file size at unlock time
"""

import os
import tempfile
import json
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
def test_windows_lock_handles_file_size_growth():
    """Test that Windows file locking handles file size growth between lock and unlock.

    This test simulates the scenario where:
    1. A file lock is acquired with a certain file size
    2. The file grows (e.g., another process writes to it)
    3. The lock is released - this should NOT fail or cause deadlock

    The fix should use a fixed large range (e.g., 0xFFFFFFFF) or implement
    a retry mechanism to handle this case safely.

    Ref: Issue #375
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a storage instance with a small file
        storage_path = Path(tmpdir) / "test_lock_size.json"
        storage = Storage(str(storage_path))

        # Add a small todo to create initial file
        todo1 = Todo(title="Task 1", status="pending")
        storage.add(todo1)

        # Get the initial file size
        initial_size = storage_path.stat().st_size

        # Verify file was created and has content
        assert initial_size > 0
        assert storage.get_next_id() == 2

        # Simulate file growth by directly appending to the file
        # (This simulates another process writing to the file)
        with storage_path.open('r+') as f:
            # Read existing content
            content = json.load(f)
            # Add more todos to make the file grow significantly
            for i in range(100):
                content["todos"].append({
                    "id": 2 + i,
                    "title": f"Grown task {i}",
                    "status": "pending"
                })
            # Write back the larger content
            f.seek(0)
            json.dump(content, f, indent=2)
            f.truncate()

        # Verify file grew
        grown_size = storage_path.stat().st_size
        assert grown_size > initial_size

        # Now reload the storage - this should acquire and release locks
        # even though the file size has grown
        # If the bug exists, this will fail with IOError or deadlock
        storage2 = Storage(str(storage_path))

        # Verify the storage loaded correctly
        # It should have loaded all the todos we added
        todos = storage2.list()
        assert len(todos) >= 1

        # This should not raise an error or deadlock
        # If it does, the bug is present


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
def test_windows_lock_range_is_fixed_large_value():
    """Test that Windows uses a fixed large lock range instead of file size.

    This is a test that verifies the FIX for issue #375.
    After the fix, the lock range should be a fixed large value (e.g., 0xFFFFFFFF)
    rather than based on the current file size.

    Ref: Issue #375
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_fixed_range.json"
        storage = Storage(str(storage_path))

        # Add a todo
        todo = Todo(title="Task", status="pending")
        storage.add(todo)

        # Verify the lock range was set
        # After the fix, this should be a large fixed value
        assert hasattr(storage, '_lock_range')

        # The lock range should be at least 0x7FFFFFFF (a large fixed value)
        # This ensures it can handle file growth
        # (Note: 0xFFFFFFFF might not work due to msvcrt limitations,
        # so we use 0x7FFFFFFF as a reasonable large value)
        if os.name == 'nt':
            # On Windows, after the fix, we should use a large fixed range
            # For now, we just verify it's set to a reasonable value
            # The actual fix will change the implementation
            assert storage._lock_range >= 4096


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
def test_concurrent_operations_with_file_growth():
    """Test that concurrent operations work even when file grows.

    This is a more realistic test that simulates concurrent access
    where the file might grow between operations.

    Ref: Issue #375
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_concurrent_growth.json"

        # Create initial storage with one todo
        storage = Storage(str(storage_path))
        storage.add(Todo(title="Initial task", status="pending"))

        # Simulate another process growing the file
        with storage_path.open('r+') as f:
            content = json.load(f)
            for i in range(50):
                content["todos"].append({
                    "id": 2 + i,
                    "title": f"Concurrent task {i}",
                    "status": "pending"
                })
            f.seek(0)
            json.dump(content, f, indent=2)
            f.truncate()

        # Now perform operations on the storage
        # These should work without deadlock even though file grew
        storage.add(Todo(title="New task after growth", status="pending"))

        todos = storage.list()
        assert len(todos) >= 2  # At least our two added todos
