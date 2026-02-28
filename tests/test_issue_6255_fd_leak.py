"""Regression test for issue #6255: File descriptor leak when os.fdopen fails.

This test verifies that if os.fdopen raises an exception after mkstemp returns
a file descriptor, the fd is properly closed to prevent resource leaks.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_fd_closed_when_fdopen_fails(tmp_path: Path) -> None:
    """Regression test for issue #6255: fd must be closed if os.fdopen fails.

    The issue: tempfile.mkstemp returns a file descriptor that must be closed.
    If os.fdopen(fd, ...) raises an exception, the fd leaks because:
    1. mkstemp returns fd at line 102
    2. os.fdopen at line 116 raises before wrapping fd
    3. The except block only cleans up temp_path, not fd

    Fix: Close fd explicitly before re-raising, or use try/finally pattern.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track the file descriptor returned by mkstemp
    leaked_fd = None
    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        nonlocal leaked_fd
        fd, path = original_mkstemp(*args, **kwargs)
        leaked_fd = fd
        return fd, path

    # Mock os.fdopen to fail after mkstemp succeeds
    def failing_fdopen(fd, *args, **kwargs):
        # Simulate fdopen failure (e.g., bad file descriptor, encoding error)
        raise OSError("Simulated fdopen failure")

    import tempfile

    with (
        patch.object(tempfile, "mkstemp", tracking_mkstemp),
        patch.object(os, "fdopen", failing_fdopen),
        pytest.raises(OSError, match="Simulated fdopen failure"),
    ):
        storage.save([Todo(id=1, text="test")])

    # CRITICAL ASSERTION: The fd must be closed
    # If the bug exists, this check will fail because fd is still open
    assert leaked_fd is not None, "mkstemp should have been called"

    # On Unix, we can check if fd is closed by trying to use os.fstat
    # A closed fd will raise OSError with EBADF (Bad file descriptor)
    try:
        os.fstat(leaked_fd)
        # If we get here, the fd is still open = BUG
        pytest.fail(
            f"File descriptor leak detected! FD {leaked_fd} is still open. "
            "This is the bug described in issue #6255."
        )
    except OSError as e:
        # Expected: fd should be closed, so fstat should fail
        assert e.errno == 9, f"Expected EBADF (9), got errno {e.errno}: {e}"


def test_no_resource_warning_on_fdopen_failure(tmp_path: Path) -> None:
    """Verify no ResourceWarning is emitted when os.fdopen fails.

    Python's -W error::ResourceWarning flag will turn resource warnings into
    errors. This test ensures no file descriptors are leaked.
    """
    import warnings

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    def failing_fdopen(fd, *args, **kwargs):
        raise OSError("Simulated fdopen failure")

    # Capture resource warnings
    with warnings.catch_warnings(record=True) as warning_list:
        warnings.simplefilter("always", ResourceWarning)

        with (
            patch.object(os, "fdopen", failing_fdopen),
            pytest.raises(OSError, match="Simulated fdopen failure"),
        ):
            storage.save([Todo(id=1, text="test")])

        # Check for ResourceWarning about unclosed file descriptor
        resource_warnings = [w for w in warning_list if issubclass(w.category, ResourceWarning)]
        assert len(resource_warnings) == 0, (
            f"ResourceWarning detected! File descriptors are leaking: {resource_warnings}"
        )
