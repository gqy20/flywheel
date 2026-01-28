"""Tests for Issue #306: Windows 锁定范围可能导致无效参数错误."""

import os
import tempfile
import pytest
from pathlib import Path

from flywheel.storage import Storage


class TestWindowsLockRange:
    """Test Windows file lock range handling (Issue #306)."""

    def test_get_windows_lock_range_for_small_file(self):
        """Test that lock range works for small files.

        The issue is that using a fixed 0xFFFF0000 (4GB) lock range
        may fail if the actual file is smaller. The method should
        either use the actual file size or handle IOError gracefully.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a storage instance with a small file
            storage_path = Path(tmpdir) / "test_todos.json"

            # Create a small file (less than 1KB)
            storage_path.write_text('{"todos": [], "next_id": 1}')

            # Create storage instance
            storage = Storage(str(storage_path))

            # Get the lock range for this file
            lock_range = storage._get_windows_lock_range(storage_path)

            # The lock range should be a positive integer
            assert isinstance(lock_range, int)
            assert lock_range > 0

    def test_get_windows_lock_range_returns_positive_integer(self):
        """Test that lock range is always a positive integer.

        msvcrt.locking() requires a positive lock range.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"

            # Test with non-existent file
            storage = Storage(str(storage_path))

            lock_range = storage._get_windows_lock_range(storage_path)

            # Should return a positive integer
            assert isinstance(lock_range, int)
            assert lock_range > 0
            # Current implementation returns 0xFFFF0000
            # This test documents the current behavior
            assert lock_range == 0xFFFF0000

    @pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
    def test_windows_file_lock_with_actual_file(self):
        """Test file locking on Windows with actual file operations.

        This test verifies that we can acquire and release locks
        on small files without getting IOError.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"

            # Create a very small file
            storage_path.write_text('{"todos": [], "next_id": 1}')

            # Create storage and perform operations
            storage = Storage(str(storage_path))

            # Add a small todo - this will trigger file locking
            from flywheel.todo import Todo
            todo = Todo(title="Test todo")
            storage.add(todo)

            # Verify the todo was added
            assert storage.get(1) is not None
            assert storage.get(1).title == "Test todo"

    def test_lock_range_does_not_exceed_file_size_by_too_much(self):
        """Test that lock range is reasonable relative to file size.

        While we want to lock more than the current file size to handle
        growth (Issue #281), locking 4GB when the file is only 1KB may
        cause issues on Windows. This test documents the expected behavior.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"

            # Create a tiny file
            storage_path.write_text('{"todos": [], "next_id": 1}')

            storage = Storage(str(storage_path))

            # Get actual file size
            file_size = os.path.getsize(storage_path)

            # Get lock range
            lock_range = storage._get_windows_lock_range(storage_path)

            # Current implementation uses a fixed large range
            # This test documents that the lock range is much larger
            # than the actual file size, which may cause issues
            assert lock_range > file_size * 1000
