"""Test that _acquire_file_lock method is fully implemented (Issue #495).

This test verifies that the _acquire_file_lock method exists and is properly
implemented for both Windows and Unix-like systems.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestAcquireFileLockImplementation:
    """Test that _acquire_file_lock method is fully implemented."""

    def test_acquire_file_lock_method_exists(self):
        """Test that _acquire_file_lock method exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Check that the method exists
            assert hasattr(storage, '_acquire_file_lock'), \
                "_acquire_file_lock method does not exist"

            # Check that it's callable
            assert callable(storage._acquire_file_lock), \
                "_acquire_file_lock is not callable"

    @pytest.mark.skipif(
        os.name == 'nt',
        reason="This test is for Unix-like systems"
    )
    def test_acquire_file_lock_unix_implementation(self):
        """Test that _acquire_file_lock is implemented for Unix systems."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Create a test file
            test_file = Path(tmpdir) / "test_lock.txt"
            test_file.write_text("test")

            # Try to acquire a lock
            with test_file.open('r') as f:
                # This should not raise an error
                storage._acquire_file_lock(f)

                # Release the lock
                storage._release_file_lock(f)

    @pytest.mark.skipif(
        os.name != 'nt',
        reason="This test is for Windows systems"
    )
    def test_acquire_file_lock_windows_implementation(self):
        """Test that _acquire_file_lock is implemented for Windows systems."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Create a test file
            test_file = Path(tmpdir) / "test_lock.txt"
            test_file.write_text("test")

            # Try to acquire a lock
            with test_file.open('r') as f:
                # This should not raise an error
                storage._acquire_file_lock(f)

                # Release the lock
                storage._release_file_lock(f)

    def test_acquire_file_lock_with_real_file_operations(self):
        """Test that _acquire_file_lock works during real file operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Add a todo - this will trigger _acquire_file_lock internally
            todo = Todo(title="Test todo for lock")
            storage.add(todo)

            # Verify the todo was added successfully
            # If _acquire_file_lock was not implemented, this would have failed
            assert storage.get(todo.id) is not None
            assert storage.get(todo.id).title == "Test todo for lock"

    def test_acquire_file_lock_timeout_configuration(self):
        """Test that _acquire_file_lock has timeout configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Check that timeout attributes exist
            assert hasattr(storage, '_lock_timeout'), \
                "_lock_timeout attribute does not exist"
            assert hasattr(storage, '_lock_retry_interval'), \
                "_lock_retry_interval attribute does not exist"

            # Verify timeout is a positive value
            assert storage._lock_timeout > 0, \
                "_lock_timeout should be positive"
            assert storage._lock_retry_interval > 0, \
                "_lock_retry_interval should be positive"

    @pytest.mark.skipif(
        os.name == 'nt',
        reason="fcntl is only available on Unix"
    )
    def test_acquire_file_lock_unix_uses_fcntl(self):
        """Test that Unix implementation uses fcntl.flock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Create a test file
            test_file = Path(tmpdir) / "test_fcntl.txt"
            test_file.write_text("test")

            # Mock fcntl to verify it's being called
            import fcntl
            with patch('fcntl.flock', wraps=fcntl.flock) as mock_flock:
                with test_file.open('r') as f:
                    storage._acquire_file_lock(f)

                    # Verify fcntl.flock was called
                    assert mock_flock.called, \
                        "fcntl.flock was not called"

                # Release the lock
                with patch('fcntl.flock', wraps=fcntl.flock) as mock_flock_release:
                    storage._release_file_lock(f)
                    # Note: fcntl.flock should be called with LOCK_UN

    def test_acquire_file_lock_complete_implementation(self):
        """Test that _acquire_file_lock has a complete implementation.

        This test verifies the structure of _acquire_file_lock to ensure
        it's not truncated or missing implementation (Issue #495).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Get the source code of _acquire_file_lock
            import inspect
            source = inspect.getsource(storage._acquire_file_lock)

            # Verify the method has more than just a docstring
            # A complete implementation should have significant logic
            assert len(source) > 500, \
                f"_acquire_file_lock appears incomplete (only {len(source)} characters)"

            # Check for key implementation elements
            if os.name == 'nt':
                # Windows: should have win32file.LockFileEx
                assert 'win32file' in source or 'LockFileEx' in source, \
                    "Windows implementation missing win32file.LockFileEx"
                assert 'timeout' in source.lower() or 'retry' in source.lower(), \
                    "Windows implementation missing timeout/retry logic"
            else:
                # Unix: should have fcntl.flock
                assert 'fcntl' in source or 'flock' in source, \
                    "Unix implementation missing fcntl.flock"
                assert 'LOCK_EX' in source or 'LOCK_NB' in source, \
                    "Unix implementation missing lock flags"

            # Check for error handling
            assert 'except' in source, \
                "_acquire_file_lock missing error handling"

            # Check for while loop (for retry mechanism)
            assert 'while' in source, \
                "_acquire_file_lock missing retry loop"
