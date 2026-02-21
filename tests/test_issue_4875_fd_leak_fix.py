"""Tests for issue #4875: File descriptor leak in save() cleanup block.

This test verifies that when os.fchmod raises an OSError, the file descriptor
returned by tempfile.mkstemp is properly closed, preventing fd leaks.

The bug: If os.fchmod(fd, ...) raises OSError before os.fdopen() is called,
the fd is never closed because:
1. mkstemp returns fd which must be closed
2. fdopen() takes ownership of fd and closes it on success
3. But if OSError occurs before fdopen (e.g., in fchmod), fd leaks
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def get_open_fd_count() -> int:
    """Count the number of open file descriptors for the current process."""
    try:
        return len(os.listdir("/proc/self/fd"))
    except OSError:
        # Fallback for systems without /proc
        return -1


def test_fchmod_failure_closes_fd(tmp_path) -> None:
    """Test that fd is closed when os.fchmod fails.

    This is the core regression test for issue #4875.
    When os.fchmod raises OSError, the fd from mkstemp must be closed.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test")]

    fd_captured = []

    def tracking_fchmod(fd: int, mode: int) -> None:
        fd_captured.append(fd)
        raise OSError(9, "Bad file descriptor")  # EBADF

    with (
        patch("flywheel.storage.os.fchmod", tracking_fchmod),
        pytest.raises(OSError, match="Bad file descriptor"),
    ):
        storage.save(todos)

    # Verify the fd was captured (meaning we got past mkstemp)
    assert len(fd_captured) == 1, "fchmod should have been called once"

    # Verify the fd was closed by trying to close it again
    # If it's already closed, os.close will raise Bad file descriptor error
    with pytest.raises(OSError):
        os.close(fd_captured[0])


def test_fchmod_failure_no_fd_leak(tmp_path) -> None:
    """Test that repeated save failures don't exhaust file descriptors.

    This test verifies the fd leak fix works across multiple failures.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test")]

    # Get initial fd count
    initial_fd_count = get_open_fd_count()

    if initial_fd_count < 0:
        pytest.skip("/proc/self/fd not available on this system")

    def failing_fchmod(fd: int, mode: int) -> None:
        raise OSError(9, "Bad file descriptor")

    # Simulate multiple failed saves
    with patch("flywheel.storage.os.fchmod", failing_fchmod):
        for _ in range(10):
            with pytest.raises(OSError):
                storage.save(todos)

    # Force garbage collection to ensure any weak references are cleaned
    import gc
    gc.collect()

    # Check that fd count hasn't grown significantly
    final_fd_count = get_open_fd_count()

    # Allow some tolerance for other system fds, but we shouldn't leak 10 fds
    assert final_fd_count <= initial_fd_count + 2, (
        f"FD leak detected: started with {initial_fd_count}, "
        f"ended with {final_fd_count} after 10 failed saves"
    )


def test_fchmod_failure_temp_file_cleaned_up(tmp_path) -> None:
    """Test that temp file is cleaned up even when fchmod fails.

    This verifies the existing cleanup path handles temp file removal.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test")]

    temp_files_created = []
    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append((fd, path))
        return fd, path

    def failing_fchmod(fd: int, mode: int) -> None:
        raise OSError(9, "Bad file descriptor")

    import tempfile

    with (
        patch.object(tempfile, "mkstemp", tracking_mkstemp),
        patch("flywheel.storage.os.fchmod", failing_fchmod),
        pytest.raises(OSError, match="Bad file descriptor"),
    ):
        storage.save(todos)

    # Verify temp file was created
    assert len(temp_files_created) == 1

    # Verify temp file was cleaned up
    temp_path = temp_files_created[0][1]
    assert not os.path.exists(temp_path), (
        f"Temp file {temp_path} should have been cleaned up"
    )
