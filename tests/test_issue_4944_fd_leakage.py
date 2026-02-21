"""Regression test for issue #4944: fd leakage when os.fdopen raises exception.

This test verifies that if os.fdopen() raises an exception after
tempfile.mkstemp() succeeds, the raw file descriptor is properly closed
to prevent fd leakage.
"""

from __future__ import annotations

import errno
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_fd_closed_when_fdopen_raises_exception(tmp_path: Path) -> None:
    """Regression test for issue #4944.

    When os.fdopen raises an exception after mkstemp succeeds, the raw fd
    from mkstemp must be closed to prevent fd leakage.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track the fd that mkstemp creates
    captured_fd = None
    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        nonlocal captured_fd
        fd, path = original_mkstemp(*args, **kwargs)
        captured_fd = fd
        return fd, path

    # Mock os.fdopen to raise an exception after mkstemp succeeds
    def failing_fdopen(fd, *args, **kwargs):
        # Simulate an error that os.fdopen might raise (e.g., encoding error)
        raise OSError(errno.EINVAL, "Simulated fdopen failure")

    import tempfile

    with (
        patch.object(tempfile, "mkstemp", tracking_mkstemp),
        patch("flywheel.storage.os.fdopen", failing_fdopen),
        pytest.raises(OSError, match="Simulated fdopen failure"),
    ):
        storage.save([Todo(id=1, text="test")])

    # The fd must be closed after the exception
    # os.fstat on a closed fd should raise OSError with EBADF (Bad file descriptor)
    assert captured_fd is not None, "mkstemp should have been called"

    try:
        os.fstat(captured_fd)
        # If we reach here, fd is still open - this is the bug!
        raise AssertionError(
            f"File descriptor {captured_fd} is still open after os.fdopen failed. "
            "This indicates fd leakage."
        )
    except OSError as e:
        # Expected: fd should be closed, so fstat should fail with EBADF
        assert e.errno == errno.EBADF, (
            f"Expected EBADF (bad file descriptor), got errno {e.errno}: {e}"
        )


def test_temp_file_cleaned_when_fdopen_raises_exception(tmp_path: Path) -> None:
    """Verify temp file is also cleaned up when os.fdopen fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    created_temp_paths = []
    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        created_temp_paths.append(Path(path))
        return fd, path

    def failing_fdopen(fd, *args, **kwargs):
        raise OSError(errno.EINVAL, "Simulated fdopen failure")

    import tempfile

    with (
        patch.object(tempfile, "mkstemp", tracking_mkstemp),
        patch("flywheel.storage.os.fdopen", failing_fdopen),
        pytest.raises(OSError, match="Simulated fdopen failure"),
    ):
        storage.save([Todo(id=1, text="test")])

    # Temp file should be cleaned up
    for temp_path in created_temp_paths:
        assert not temp_path.exists(), f"Temp file {temp_path} should be cleaned up"
