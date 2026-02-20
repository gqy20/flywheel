"""Regression test for issue #4776: File descriptor leak if os.fdopen() raises.

If os.fdopen() itself raises an exception before the with block is entered,
the raw file descriptor returned by tempfile.mkstemp() could leak.

This test verifies that the fd is properly closed even when os.fdopen() fails.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_fd_closed_when_fdopen_raises_exception(tmp_path: Path) -> None:
    """Test that file descriptor is closed if os.fdopen() raises an exception.

    Regression test for issue #4776:
    tempfile.mkstemp returns a raw file descriptor. os.fdopen() takes ownership
    of this fd. If os.fdopen() fails before successfully wrapping the fd,
    the raw fd could leak. The fix ensures fd is closed in this case.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track which file descriptors are created
    leaked_fds = []

    # Get the original mkstemp to track fds it creates
    import tempfile

    original_mkstemp = tempfile.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        leaked_fds.append(fd)
        return fd, path

    # Make os.fdopen raise an OSError to simulate the failure case
    def failing_fdopen(fd, *args, **kwargs):
        # Simulate os.fdopen failure before wrapping the fd
        raise OSError("Simulated fdopen failure")

    with (
        patch.object(tempfile, "mkstemp", tracking_mkstemp),
        patch.object(os, "fdopen", failing_fdopen),
        pytest.raises(OSError, match="Simulated fdopen failure"),
    ):
        storage.save([Todo(id=1, text="test")])

    # Verify that the fd was properly closed despite the fdopen failure
    assert len(leaked_fds) == 1, "Expected exactly one fd to be created"
    fd = leaked_fds[0]

    # Check that the fd is no longer open
    # On Linux, we can check /proc/self/fd to see if fd is still open
    try:
        fd_status = os.fstat(fd)
        # If we get here, the fd is still open (leaked!)
        pytest.fail(
            f"File descriptor {fd} is still open (leaked)! "
            f"fdopen failure should have closed it. fstat result: {fd_status}"
        )
    except OSError as e:
        # Bad file descriptor means the fd was properly closed
        # On Linux, EBADF (errno 9) means "Bad file descriptor"
        import errno

        assert e.errno == errno.EBADF, f"Expected EBADF (errno 9), got errno {e.errno}: {e}"


def test_fd_not_leaked_on_successful_save(tmp_path: Path) -> None:
    """Baseline test: verify no fd leaks on successful save."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Get open fds before save
    open_fds_before = set(os.listdir("/proc/self/fd"))

    # Perform save
    storage.save([Todo(id=1, text="test")])

    # Get open fds after save
    open_fds_after = set(os.listdir("/proc/self/fd"))

    # The number of open fds should be the same (no leaks)
    # Note: some variance is normal, so we allow small differences
    # But we should not have significantly more fds after
    new_fds = open_fds_after - open_fds_before
    leaked_count = len(new_fds)

    assert leaked_count == 0, (
        f"Potential fd leak detected: {leaked_count} new fds opened. New fds: {new_fds}"
    )
