"""Test for Issue #389 - File lock release implementation."""

import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestFileLockRelease:
    """Test file lock release functionality (Issue #389)."""

    def test_release_file_lock_windows(self):
        """Test Windows file lock release with proper unlock range."""
        # Create a temporary file for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Add a todo to trigger file operations
            todo = Todo(title="Test todo")
            storage.add(todo)

            # Verify that _lock_range was set during acquire
            if os.name == 'nt':  # Windows
                assert storage._lock_range == 0x7FFFFFFF, \
                    "Lock range should be set to 0x7FFFFFFF on Windows"
            else:
                assert storage._lock_range == 0, \
                    "Lock range should be 0 on Unix"

            # Clean up
            storage.close()

    def test_acquire_and_release_lock_consistency(self):
        """Test that lock acquire and release use consistent parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Perform multiple operations to test lock consistency
            for i in range(3):
                todo = Todo(title=f"Todo {i}")
                storage.add(todo)

            # The lock range should remain consistent
            if os.name == 'nt':  # Windows
                assert storage._lock_range == 0x7FFFFFFF, \
                    "Lock range should remain consistent across operations"

            storage.close()

    def test_file_lock_methods_exist(self):
        """Test that file lock methods are implemented."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Verify methods exist
            assert hasattr(storage, '_acquire_file_lock'), \
                "_acquire_file_lock method should exist"
            assert hasattr(storage, '_release_file_lock'), \
                "_release_file_lock method should exist"
            assert hasattr(storage, '_get_file_lock_range_from_handle'), \
                "_get_file_lock_range_from_handle method should exist"

            storage.close()
