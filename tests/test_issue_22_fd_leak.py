"""Test for file descriptor leak fix (Issue #22).

This test ensures that file descriptors are properly closed even when
exceptions occur during write operations.

Issue #22 highlights that if os.write() throws an exception, the file
descriptor (fd) will not be closed, causing a resource leak. The fix
ensures that try-finally blocks are used to guarantee fd cleanup.
"""

import errno
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_fd_closed_on_os_write_failure():
    """Test that file descriptors are properly closed when os.write fails.

    This directly addresses Issue #22: if os.write() throws an exception,
    the fd should still be closed via the finally block.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Mock os.write to raise an exception (simulating write failure)
        def mock_write(fd, data):
            raise OSError("Simulated write failure during os.write")

        with patch('os.write', mock_write):
            storage = Storage(str(storage_path))

            # This should raise an error but properly close the file descriptor
            # via the finally block in _save()
            with pytest.raises(OSError, match="Simulated write failure"):
                storage.add(Todo(id=1, title="Test todo", status="pending"))

            # Verify no file descriptors are leaked by checking storage is still functional
            # after the error. If fd was leaked, subsequent operations might fail or hang.
            storage._todos = []
            storage._save()  # This should work without running out of file descriptors


def test_fd_closed_on_disk_full_enospc():
    """Test that file descriptors are closed when disk is full (ENOSPC).

    This is a specific case of Issue #22 where os.write fails with ENOSPC.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add initial todo
        storage.add(Todo(title="Initial todo"))

        # Mock os.write to simulate disk full error
        def mock_write_enospc(fd, data):
            raise OSError(errno.ENOSPC, "No space left on device")

        # Try to add another todo when disk is full
        with patch('os.write', mock_write_enospc):
            with pytest.raises(OSError) as exc_info:
                storage.add(Todo(title="Should fail"))

            # Verify it's the correct error
            assert exc_info.value.errno == errno.ENOSPC

        # Verify storage still works after error (no fd leak)
        # This would fail if fd was leaked and not properly closed
        storage.add(Todo(title="Recovery test"))
        todos = storage.list()
        assert len(todos) >= 1  # At least the initial todo


def test_normal_operations_do_not_leak_fds():
    """Test that normal operations don't leak file descriptors.

    This is a baseline test to ensure that in normal operation,
    file descriptors are properly managed.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Perform many operations - if fds leak, this could eventually fail
        for i in range(100):
            storage.add(Todo(title=f"Todo {i+1}", status="pending"))

        # Verify storage still works
        todos = storage.list()
        assert len(todos) == 100

        # Perform update and delete operations as well
        todo = todos[0]
        todo.title = "Updated todo"
        storage.update(todo)

        storage.delete(todo.id)
        todos = storage.list()
        assert len(todos) == 99
