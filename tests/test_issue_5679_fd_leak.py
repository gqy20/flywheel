"""Regression test for issue #5679: File descriptor leak when os.fchmod fails.

This test verifies that when os.fchmod fails before os.fdopen takes ownership,
the file descriptor is properly closed to prevent resource leaks.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_fd_closed_when_fchmod_fails(tmp_path) -> None:
    """Test that file descriptor is closed when os.fchmod fails.

    Regression test for issue #5679: File descriptor leak when os.fchmod
    fails before os.fdopen takes ownership.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track the fd that mkstemp returns
    leaked_fds = []
    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        leaked_fds.append(fd)
        return fd, path

    # Mock fchmod to fail
    def failing_fchmod(fd, mode):
        raise OSError("Simulated fchmod failure")

    import tempfile

    with (
        patch.object(tempfile, "mkstemp", tracking_mkstemp),
        patch("flywheel.storage.os.fchmod", failing_fchmod),
        pytest.raises(OSError, match="Simulated fchmod failure"),
    ):
        storage.save([Todo(id=1, text="test")])

    # Verify the fd was closed (no longer open)
    assert len(leaked_fds) == 1, "Expected exactly one fd to be created"
    fd = leaked_fds[0]

    # On Linux, we can check if fd is still open via /proc/self/fd
    # If fd is closed, it won't exist in /proc/self/fd
    try:
        os.fstat(fd)
        # If we get here without exception, fd is still open = leak!
        pytest.fail(f"File descriptor {fd} was not closed after fchmod failure - LEAK DETECTED")
    except OSError:
        # OSError means fd is closed - this is the expected behavior
        pass


def test_fd_closed_when_fdopen_fails(tmp_path) -> None:
    """Test that file descriptor is closed when os.fdopen fails.

    If os.fdopen fails after fchmod succeeds, the fd should still be closed.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track the fd that mkstemp returns
    leaked_fds = []
    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        leaked_fds.append(fd)
        return fd, path

    # Mock fdopen to fail
    def failing_fdopen(fd, *args, **kwargs):
        raise OSError("Simulated fdopen failure")

    import tempfile

    with (
        patch.object(tempfile, "mkstemp", tracking_mkstemp),
        patch("flywheel.storage.os.fdopen", failing_fdopen),
        pytest.raises(OSError, match="Simulated fdopen failure"),
    ):
        storage.save([Todo(id=1, text="test")])

    # Verify the fd was closed
    assert len(leaked_fds) == 1, "Expected exactly one fd to be created"
    fd = leaked_fds[0]

    try:
        os.fstat(fd)
        pytest.fail(f"File descriptor {fd} was not closed after fdopen failure - LEAK DETECTED")
    except OSError:
        # OSError means fd is closed - this is the expected behavior
        pass
