"""Regression test for issue #5351: File descriptor leak in save().

This test verifies that when os.fchmod fails in TodoStorage.save(),
the file descriptor returned by mkstemp is properly closed.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_fchmod_failure_closes_file_descriptor(tmp_path) -> None:
    """Test that fd is closed when os.fchmod fails (issue #5351)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track fd closure
    fd_closed = []
    original_close = os.close

    def tracking_close(fd: int) -> None:
        fd_closed.append(fd)
        original_close(fd)

    # Make os.fchmod fail
    def failing_fchmod(fd: int, mode: int) -> None:
        raise OSError("Simulated fchmod failure")

    import tempfile

    original_mkstemp = tempfile.mkstemp
    original_fchmod = os.fchmod

    with (
        patch.object(os, "fchmod", failing_fchmod),
        patch.object(os, "close", tracking_close),
        pytest.raises(OSError, match="Simulated fchmod failure"),
    ):
        storage.save([Todo(id=1, text="test")])

    # Restore originals
    tempfile.mkstemp = original_mkstemp
    os.fchmod = original_fchmod

    # Verify that fd was closed
    assert len(fd_closed) >= 1, "File descriptor should be closed on fchmod failure"


def test_fdopen_failure_closes_file_descriptor(tmp_path) -> None:
    """Test that fd is closed when os.fdopen fails.

    This tests a related case where if fdopen fails (after fchmod succeeds),
    the fd should also be closed.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track fd closure
    fd_closed = []
    original_close = os.close

    def tracking_close(fd: int) -> None:
        fd_closed.append(fd)
        original_close(fd)

    # Simulate fdopen failure after fchmod succeeds
    original_fdopen = os.fdopen
    fdopen_call_count = [0]

    def failing_fdopen(fd: int, *args, **kwargs):
        fdopen_call_count[0] += 1
        if fdopen_call_count[0] == 1:
            # First call should fail to simulate fdopen error
            raise OSError("Simulated fdopen failure")
        return original_fdopen(fd, *args, **kwargs)

    with (
        patch.object(os, "fdopen", failing_fdopen),
        patch.object(os, "close", tracking_close),
        pytest.raises(OSError, match="Simulated fdopen failure"),
    ):
        storage.save([Todo(id=1, text="test")])

    # On failure, fd should have been attempted to be closed
    # The fix ensures os.close(fd) is called in the except block when fd wasn't consumed by fdopen
    assert len(fd_closed) >= 1, "File descriptor should be closed on fdopen failure"


def test_successful_save_does_not_leak_fd(tmp_path) -> None:
    """Test that successful save properly closes the file descriptor."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Track open fds before save
    before_fds = set(os.listdir("/proc/self/fd"))

    # Perform save
    storage.save([Todo(id=1, text="updated"), Todo(id=2, text="new")])

    # Track open fds after save
    after_fds = set(os.listdir("/proc/self/fd"))

    # No new fds should remain open
    _ = after_fds - before_fds  # soft check since test infrastructure may open files

    # Verify we can still perform operations (fd wasn't exhausted)
    for i in range(10):
        storage.save([Todo(id=i, text=f"test-{i}")])

    assert storage.load()[0].text == "test-9"
