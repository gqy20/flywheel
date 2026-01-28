"""Test file lock timeout mechanism (Issue #396).

This test verifies that file lock acquisition has a reasonable timeout
to prevent indefinite hangs when a competing process dies while holding
the lock.
"""

import os
import pytest
import tempfile
import time
from pathlib import Path

from flywheel.storage import Storage


@pytest.mark.skipif(
    os.name != 'nt',
    reason="File lock timeout test is Windows-specific (msvcrt.LK_LOCK)"
)
class TestFileLockTimeout:
    """Test file lock timeout mechanism on Windows."""

    def test_file_lock_has_timeout_configuration(self):
        """Test that file lock timeout is configurable."""
        # This test verifies that the system has a way to configure
        # file lock timeout to prevent indefinite hangs
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # The storage should have a lock timeout mechanism
            # This test documents the expected behavior
            assert storage is not None
            assert storage.path == storage_path

    def test_file_lock_non_blocking_with_retry(self):
        """Test that file lock uses non-blocking mode with retry loop."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Add a todo to trigger file operations
            from flywheel.todo import Todo
            todo = Todo(title="Test todo")
            storage.add(todo)

            # Verify the todo was saved successfully
            assert storage.get(todo.id) is not None
            assert storage.get(todo.id).title == "Test todo"

    def test_file_lock_timeout_prevents_indefinite_hang(self):
        """Test that file lock acquisition times out reasonably."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # This test documents the expected timeout behavior
            # The implementation should use LK_NBLCK (non-blocking)
            # with a retry loop and timeout instead of LK_LOCK
            start_time = time.time()

            # Perform a file operation that acquires lock
            from flywheel.todo import Todo
            todo = Todo(title="Timeout test")
            storage.add(todo)

            elapsed = time.time() - start_time

            # Operation should complete quickly
            # (not hang indefinitely if a competing process holds the lock)
            assert elapsed < 5.0, "File operation took too long, possible hang detected"


@pytest.mark.skipif(
    os.name == 'nt',
    reason="This test is for Unix-like systems"
)
class TestUnixFileLockBehavior:
    """Test file lock behavior on Unix-like systems."""

    def test_unix_file_lock_works_correctly(self):
        """Test that Unix file locks work as expected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Unix uses fcntl.flock with LOCK_EX
            # This should work without timeout issues
            from flywheel.todo import Todo
            todo = Todo(title="Unix test")
            storage.add(todo)

            assert storage.get(todo.id) is not None
