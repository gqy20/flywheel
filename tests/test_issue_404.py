"""Test for issue #404 - false positive verification.

This test verifies that the _acquire_file_lock method in src/flywheel/storage.py
is complete and syntactically correct. Issue #404 claimed the code was incomplete
with a syntax error at line 236, but this was a false positive from an AI scanner.

The code at line 236 is `try:` which is perfectly valid Python syntax.
The complete timeout retry loop exists from lines 242-270 (Unix) and 192-222 (Windows).
"""

import os
import pytest
import tempfile
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestIssue404FalsePositive:
    """Test that issue #404 is a false positive - code is complete."""

    def test_acquire_file_lock_method_is_complete(self):
        """Test that _acquire_file_lock method exists and is syntactically valid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Verify the method exists
            assert hasattr(storage, '_acquire_file_lock')
            assert callable(storage._acquire_file_lock)

    def test_file_lock_timeout_attributes_exist(self):
        """Test that timeout mechanism attributes are initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Verify timeout configuration exists (Issue #396)
            assert hasattr(storage, '_lock_timeout')
            assert storage._lock_timeout == 30.0

            # Verify retry interval exists (Issue #396)
            assert hasattr(storage, '_lock_retry_interval')
            assert storage._lock_retry_interval == 0.1

    def test_file_operations_work_correctly(self):
        """Test that file operations work, proving _acquire_file_lock is functional."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Add a todo - this will call _acquire_file_lock internally
            todo = Todo(title="Test issue 404")
            added_todo = storage.add(todo)

            # Verify it was added successfully
            assert added_todo.id is not None
            assert storage.get(added_todo.id) is not None
            assert storage.get(added_todo.id).title == "Test issue 404"

            # Update the todo - another file lock operation
            added_todo.status = "completed"
            storage.update(added_todo)
            assert storage.get(added_todo.id).status == "completed"

            # Delete the todo - another file lock operation
            result = storage.delete(added_todo.id)
            assert result is True
            assert storage.get(added_todo.id) is None

    def test_timeout_retry_loop_exists_on_unix(self):
        """Test that Unix timeout retry loop code exists (lines 242-270)."""
        import inspect
        from flywheel.storage import Storage

        # Get the source code of _acquire_file_lock
        source = inspect.getsource(Storage._acquire_file_lock)

        # Verify the timeout retry loop exists for Unix
        assert 'start_time = time.time()' in source
        assert 'elapsed = time.time() - start_time' in source
        assert 'if elapsed >= self._lock_timeout:' in source
        assert 'File lock acquisition timed out' in source
        assert 'time.sleep(self._lock_retry_interval)' in source

    @pytest.mark.skipif(
        os.name != 'nt',
        reason="Windows-specific timeout test"
    )
    def test_timeout_retry_loop_exists_on_windows(self):
        """Test that Windows timeout retry loop code exists (lines 192-222)."""
        import inspect
        from flywheel.storage import Storage

        # Get the source code of _acquire_file_lock
        source = inspect.getsource(Storage._acquire_file_lock)

        # Verify Windows-specific timeout code
        assert 'LK_NBLCK' in source
        assert 'msvcrt.locking' in source
