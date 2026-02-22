"""Regression tests for issue #5189: File descriptor leak when fchmod fails.

Issue: If os.fchmod fails after tempfile.mkstemp but before os.fdopen,
the file descriptor is never closed, causing a resource leak.

The fix should ensure the fd is closed in the except block when fchmod fails,
before attempting to clean up the temp file path.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_fchmod_failure_closes_fd(tmp_path) -> None:
    """Issue #5189: fd should be closed when fchmod fails.

    When os.fchmod raises an OSError after mkstemp, the file descriptor
    must be properly closed to avoid resource leaks.

    This test mocks fchmod to fail and verifies:
    1. The fd is closed (by checking os.close was called)
    2. The temp file path is cleaned up
    3. The original exception is re-raised
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track which fds were created and closed
    fds_created = []
    fds_closed = []

    import tempfile as tempfile_module
    original_mkstemp = tempfile_module.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        fds_created.append(fd)
        return fd, path

    original_close = os.close

    def tracking_close(fd, *args, **kwargs):
        fds_closed.append(fd)
        return original_close(fd, *args, **kwargs)

    def failing_fchmod(fd, mode):
        """Mock fchmod that always fails."""
        raise OSError("Mocked fchmod failure")

    with (
        patch.object(tempfile_module, "mkstemp", tracking_mkstemp),
        patch.object(os, "close", tracking_close),
        patch.object(os, "fchmod", failing_fchmod),
        pytest.raises(OSError, match="Mocked fchmod failure"),
    ):
        storage.save([Todo(id=1, text="test")])

    # Verify that fd was created and then closed
    assert len(fds_created) == 1, f"Expected 1 fd created, got {len(fds_created)}"
    assert len(fds_closed) == 1, f"Expected 1 fd closed, got {len(fds_closed)}"
    assert fds_created[0] == fds_closed[0], "Created fd was not the same as closed fd"


def test_fchmod_failure_cleans_up_temp_path(tmp_path) -> None:
    """Issue #5189: temp file path should be deleted when fchmod fails.

    When os.fchmod raises an OSError, the temp file created by mkstemp
    should be cleaned up (unlinked) to avoid leaving orphan files.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    temp_paths_created = []
    temp_paths_unlinked = []

    import tempfile as tempfile_module
    original_mkstemp = tempfile_module.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_paths_created.append(path)
        return fd, path

    original_unlink = os.unlink

    def tracking_unlink(path, *args, **kwargs):
        temp_paths_unlinked.append(path)
        return original_unlink(path, *args, **kwargs)

    def failing_fchmod(fd, mode):
        raise OSError("Mocked fchmod failure")

    with (
        patch.object(tempfile_module, "mkstemp", tracking_mkstemp),
        patch.object(os, "unlink", tracking_unlink),
        patch.object(os, "fchmod", failing_fchmod),
        pytest.raises(OSError, match="Mocked fchmod failure"),
    ):
        storage.save([Todo(id=1, text="test")])

    # Verify temp path was created and then unlinked
    assert len(temp_paths_created) == 1, f"Expected 1 temp path created, got {len(temp_paths_created)}"
    assert len(temp_paths_unlinked) == 1, f"Expected 1 temp path unlinked, got {len(temp_paths_unlinked)}"
    assert temp_paths_created[0] == temp_paths_unlinked[0], "Created temp path was not cleaned up"


def test_successful_save_does_not_leak_fd_via_os_close(tmp_path) -> None:
    """Verify that successful saves don't trigger os.close directly.

    On success, fd is closed by os.fdopen context manager, not by os.close.
    This test ensures we're not accidentally closing the fd twice.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    original_close = os.close
    close_calls = []

    def tracking_close(fd, *args, **kwargs):
        close_calls.append(fd)
        return original_close(fd, *args, **kwargs)

    with patch.object(os, "close", tracking_close):
        storage.save([Todo(id=1, text="test")])

    # On success, os.close should not be called manually
    # (fdopen handles closing via the file object's close)
    assert len(close_calls) == 0, (
        f"os.close was called {len(close_calls)} times on successful save, "
        "expected 0 (fdopen should handle closing)"
    )
