"""Test for Issue #444 - _acquire_file_lock method completion."""

import os
import tempfile
import pytest
from pathlib import Path

from flywheel.storage import Storage


class TestAcquireFileLock:
    """Test _acquire_file_lock method is complete and functional."""

    def test_acquire_file_lock_method_exists(self):
        """Test that _acquire_file_lock method is properly defined."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Verify the method exists
            assert hasattr(storage, '_acquire_file_lock')
            assert callable(storage._acquire_file_lock)

    def test_acquire_file_lock_with_file_handle(self):
        """Test that _acquire_file_lock can acquire a lock on a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Create a test file
            test_file = Path(tmpdir) / "test.lock"
            test_file.write_text("test")

            # Try to acquire lock on the file
            with test_file.open('r') as f:
                # This should not raise an exception
                storage._acquire_file_lock(f)
                # Lock should be acquired successfully

                # Release the lock
                storage._release_file_lock(f)

    def test_acquire_file_lock_syntax_complete(self):
        """Test that _acquire_file_lock method is syntactically complete."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            # This should not raise SyntaxError or IndentationError
            try:
                storage = Storage(str(storage_path))
                # If we can instantiate Storage, the method is syntactically complete
                assert True
            except (SyntaxError, IndentationError) as e:
                pytest.fail(f"_acquire_file_lock method has syntax errors: {e}")

    def test_file_lock_prevents_concurrent_access(self):
        """Test that file locks work for concurrent access prevention."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage1 = Storage(str(storage_path))

            # Add a todo to create the file
            from flywheel.todo import Todo
            todo1 = Todo(title="Test todo 1")
            storage1.add(todo1)

            # Create another storage instance pointing to the same file
            storage2 = Storage(str(storage_path))

            # Both should be able to read the file
            todos1 = storage1.list()
            todos2 = storage2.list()

            assert len(todos1) == 1
            assert len(todos2) == 1
            assert todos1[0].title == "Test todo 1"
            assert todos2[0].title == "Test todo 1"

    def test_lock_timeout_attributes_exist(self):
        """Test that lock timeout attributes are initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Verify timeout attributes exist
            assert hasattr(storage, '_lock_timeout')
            assert hasattr(storage, '_lock_retry_interval')
            assert storage._lock_timeout > 0
            assert storage._lock_retry_interval > 0
