"""Tests for Issue #326 - Windows file lock should cover entire file."""

import os
import tempfile
import json
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestWindowsFileLockCoverage:
    """Test that Windows file locks cover the entire file, not just 1MB."""

    def test_file_lock_range_covers_entire_file(self):
        """Test that file lock range is based on actual file size, not fixed 1MB."""
        # Create a temporary storage path
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Create a storage instance
            storage = Storage(str(storage_path))

            # Add enough todos to exceed 1MB when serialized
            # Each todo with a long title is approximately 200-300 bytes
            # We need about 4000-5000 todos to exceed 1MB
            todos_to_add = 5000
            for i in range(todos_to_add):
                # Create todos with long titles to maximize size
                long_title = f"Task {i}: " + "x" * 200  # ~210 bytes per todo
                todo = Todo(title=long_title)
                storage.add(todo)

            # Get the actual file size
            file_size = storage_path.stat().st_size

            # Verify the file exceeds 1MB
            assert file_size > 1024 * 1024, f"File size ({file_size}) should exceed 1MB"

            # Open the file and check that lock range would be sufficient
            with storage_path.open('r') as f:
                # Get the lock range that would be used
                if os.name == 'nt':  # Windows
                    lock_range = storage._get_file_lock_range_from_handle(f)
                    # The lock range should be at least as large as the file
                    # to prevent concurrent writes to different parts of the file
                    assert lock_range >= file_size, (
                        f"Lock range ({lock_range} bytes) must be at least "
                        f"the file size ({file_size} bytes) to prevent concurrent writes. "
                        f"Fixed 1MB lock is insufficient for large files."
                    )
                else:
                    # On Unix, fcntl.flock locks the entire file by default
                    # This is just a sanity check that we can call the method
                    lock_range = storage._get_file_lock_range_from_handle(f)
                    # On non-Windows systems, we should still get a valid range
                    assert isinstance(lock_range, int)
                    assert lock_range > 0

            # Verify that all todos were saved correctly
            todos = storage.list()
            assert len(todos) == todos_to_add, f"Expected {todos_to_add} todos, got {len(todos)}"

            # Verify data integrity
            for i, todo in enumerate(todos):
                expected_prefix = f"Task {i}: Task"
                assert todo.title.startswith(expected_prefix), f"Todo {i} has incorrect title"

    def test_file_lock_range_for_small_files(self):
        """Test that file lock range is reasonable for small files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Add a small number of todos
            for i in range(10):
                todo = Todo(title=f"Task {i}")
                storage.add(todo)

            # Get the actual file size
            file_size = storage_path.stat().st_size

            # Verify the file is small (< 100KB)
            assert file_size < 100 * 1024, f"File size ({file_size}) should be small"

            # Open the file and check lock range
            with storage_path.open('r') as f:
                lock_range = storage._get_file_lock_range_from_handle(f)

                # For small files, the lock range should be reasonable
                # It should not be excessively large
                # but it should still lock the entire file
                if os.name == 'nt':  # Windows
                    # On Windows, lock the entire file
                    assert lock_range >= file_size, (
                        f"Lock range ({lock_range} bytes) must cover the entire file ({file_size} bytes)"
                    )
                    # But it should not be unreasonably large (e.g., > 10MB for a small file)
                    # to prevent integer overflow issues
                    assert lock_range <= 10 * 1024 * 1024, (
                        f"Lock range ({lock_range} bytes) is excessively large for a small file"
                    )
