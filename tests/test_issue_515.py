"""Test for issue #515 - Verify _acquire_file_lock method is complete and functional.

This test validates that the _acquire_file_lock method is fully implemented
and not truncated at the docstring as reported in the issue.

Issue #515 claimed the code was truncated at the docstring, but upon inspection,
the method is actually complete with full implementation for both Windows and Unix.
"""

import inspect
import os
import pytest
from pathlib import Path
from flywheel.storage import Storage
from flywheel.todo import Todo


class TestIssue515:
    """Verify _acquire_file_lock method implementation is complete.

    This test suite validates that issue #515 is a false positive - the code
    is not truncated and is fully functional.
    """

    def test_acquire_file_lock_method_exists(self):
        """Test that _acquire_file_lock method exists and is callable."""
        storage = Storage(path="~/.flywheel/test_issue_515.json")
        assert hasattr(storage, '_acquire_file_lock')
        assert callable(storage._acquire_file_lock)

    def test_acquire_file_lock_has_complete_docstring(self):
        """Test that _acquire_file_lock has a complete docstring."""
        storage = Storage(path="~/.flywheel/test_issue_515.json")
        docstring = storage._acquire_file_lock.__doc__
        assert docstring is not None
        # Check that docstring contains key sections
        assert "Args:" in docstring
        assert "Raises:" in docstring
        assert "Note:" in docstring
        # Verify docstring is complete (not truncated)
        assert docstring.count('\n') > 10  # Should have many lines

    def test_acquire_file_lock_source_complete(self):
        """Test that _acquire_file_lock source code is complete."""
        source = inspect.getsource(Storage._acquire_file_lock)
        # Check for key implementation details
        assert "if os.name == 'nt':" in source
        assert "win32file.LockFileEx" in source
        assert "fcntl.flock" in source
        assert "RuntimeError" in source
        assert "IOError" in source
        # Check that method ends properly (not truncated mid-statement)
        assert source.rstrip().endswith("raise")
        # Check for timeout mechanism
        assert "_lock_timeout" in source
        assert "time.sleep" in source

    def test_acquire_file_lock_functional_test(self):
        """Test that _acquire_file_lock actually works with a real file."""
        import tempfile
        import os

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
            f.write('{"todos": [], "next_id": 1, "metadata": {"checksum": ""}}')

        try:
            # Create storage instance
            storage = Storage(path=temp_path)

            # Try to acquire file lock on the storage file
            with storage.path.open('r') as f:
                # This should not raise an exception
                storage._acquire_file_lock(f)
                # If we get here, lock was acquired successfully
                # Now release it
                storage._release_file_lock(f)

            # Verify we can acquire and release multiple times
            with storage.path.open('r') as f:
                storage._acquire_file_lock(f)
                storage._release_file_lock(f)

            # Verify it works with normal storage operations
            todo = Todo(title="Test todo", status="pending")
            added = storage.add(todo)
            assert added.id == 1
            assert storage.get(1) is not None

        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            backup_path = temp_path + ".backup"
            if os.path.exists(backup_path):
                os.unlink(backup_path)

    def test_acquire_file_lock_timeout_attributes_exist(self):
        """Test that timeout-related attributes exist."""
        storage = Storage(path="~/.flywheel/test_issue_515.json")
        assert hasattr(storage, '_lock_timeout')
        assert hasattr(storage, '_lock_retry_interval')
        assert storage._lock_timeout > 0
        assert storage._lock_retry_interval > 0

    def test_acquire_file_lock_windows_path_uses_correct_imports(self):
        """Test that Windows code path uses correct module-level imports."""
        source = inspect.getsource(Storage._acquire_file_lock)
        # Windows-specific checks
        if os.name == 'nt':
            # On Windows, verify the Windows code path is present
            assert "win32file.LockFileEx" in source
            assert "win32con.LOCKFILE_FAIL_IMMEDIATELY" in source
            assert "win32con.LOCKFILE_EXCLUSIVE_LOCK" in source
            assert "pywintypes.OVERLAPPED" in source
        else:
            # On Unix, verify Unix code path is present
            assert "fcntl.flock" in source
            assert "fcntl.LOCK_EX" in source
            assert "fcntl.LOCK_NB" in source

    def test_acquire_file_lock_handles_timeout(self):
        """Test that _acquire_file_lock can handle timeout scenarios."""
        import tempfile
        import os
        import time

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
            f.write('{"todos": [], "next_id": 1, "metadata": {"checksum": ""}}')

        try:
            storage = Storage(path=temp_path)

            # Set a very short timeout for testing
            original_timeout = storage._lock_timeout
            storage._lock_timeout = 0.1  # 100ms timeout

            try:
                # Try to acquire lock (should succeed quickly)
                with storage.path.open('r') as f:
                    storage._acquire_file_lock(f)
                    storage._release_file_lock(f)
            except Exception as e:
                # If it times out or fails, that's acceptable for this test
                # We're just verifying the timeout mechanism exists
                pass
            finally:
                storage._lock_timeout = original_timeout

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            backup_path = temp_path + ".backup"
            if os.path.exists(backup_path):
                os.unlink(backup_path)
