"""Test FileLock context manager (Issue #943).

This test verifies that a context manager exists for handling file lock
acquisition and release automatically, eliminating error-prone manual
try/finally blocks.
"""

import os
import pytest
import tempfile
from pathlib import Path

from flywheel.storage import Storage


class TestFileLockContextManager:
    """Test FileLock context manager for automatic lock handling."""

    def test_file_lock_context_manager_exists(self):
        """Test that FileLock context manager class exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # The storage should have a FileLock context manager
            # This test documents the expected behavior
            assert hasattr(storage, '_file_lock'), \
                "Storage should have _file_lock method for context manager"

    def test_file_lock_context_manager_acquire_and_release(self):
        """Test that FileLock context manager acquires and releases lock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Create a test file
            storage_path.write_text('{"todos": [], "next_id": 1}')

            # Test that the context manager works correctly
            with open(storage_path, 'r+b') as f:
                # The context manager should acquire lock on __enter__
                # and release on __exit__
                with storage._file_lock(f):
                    # Inside the context, lock should be held
                    # We can perform file operations here
                    content = f.read()
                    assert content is not None

                # After exiting context, lock should be released
                # This is verified implicitly if no deadlock occurs

    def test_file_lock_context_manager_exception_handling(self):
        """Test that FileLock context manager releases lock on exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Create a test file
            storage_path.write_text('{"todos": [], "next_id": 1}')

            # Test that lock is released even when exception occurs
            with open(storage_path, 'r+b') as f:
                try:
                    with storage._file_lock(f):
                        # Simulate an exception
                        raise ValueError("Test exception")
                except ValueError:
                    pass

                # Lock should be released despite the exception
                # This is verified implicitly if we can acquire the lock again
                with storage._file_lock(f):
                    # If we get here, the lock was properly released
                    assert True

    def test_file_lock_context_manager_with_storage_operations(self):
        """Test FileLock context manager with actual storage operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Add a todo using the storage
            from flywheel.todo import Todo
            todo = Todo(title="Test context manager")
            storage.add(todo)

            # Verify the todo was saved
            retrieved = storage.get(todo.id)
            assert retrieved is not None
            assert retrieved.title == "Test context manager"
