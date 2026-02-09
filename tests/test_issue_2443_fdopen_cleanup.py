"""Regression tests for issue #2443: fd context manager cleanup and fd leak.

Issue: When fchmod or fdopen fails, the raw fd is never explicitly closed,
causing an fd leak. The fd must be closed before the exception propagates.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import gc
import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_fchmod_failure_does_not_leak_fd(tmp_path) -> None:
    """Issue #2443: If fchmod fails, the fd must be closed (no leak).

    When fchmod fails on the raw fd, the fd is still owned by us and
    must be explicitly closed. Currently it leaks.

    Before fix: fd is leaked (not closed)
    After fix: fd is closed properly
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track created fds to detect leaks
    created_fds = []

    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        created_fds.append(fd)
        return fd, path

    # Make fchmod fail to trigger the leak path
    def failing_fchmod(fd, mode):
        raise OSError("Simulated fchmod failure")

    import tempfile
    original_mkstemp_func = tempfile.mkstemp

    # Get initial fd count
    initial_fd_count = len(os.listdir("/proc/self/fd")) if Path("/proc/self/fd").exists() else 0

    with (
        patch("tempfile.mkstemp", side_effect=tracking_mkstemp),
        patch("os.fchmod", side_effect=failing_fchmod),
        pytest.raises(OSError, match="Simulated fchmod failure"),
    ):
        storage.save([Todo(id=1, text="test")])

    # Restore original
    tempfile.mkstemp = original_mkstemp_func

    # Force garbage collection
    gc.collect()

    # Check that created fds are now closed
    for fd in created_fds:
        # Try to fstat the fd - it should fail (be closed)
        with pytest.raises(OSError, match="Bad file descriptor"):
            os.fstat(fd)

    # Optional: check overall fd count didn't increase
    # (this may be flaky due to other fds opening/closing)
    if Path("/proc/self/fd").exists():
        final_fd_count = len(os.listdir("/proc/self/fd"))
        # Allow some tolerance for other fds that might open/close
        assert final_fd_count <= initial_fd_count + 2, (
            f"FD leak detected: {final_fd_count - initial_fd_count} fds leaked"
        )


def test_fdopen_failure_does_not_leak_fd(tmp_path) -> None:
    """Issue #2443: If fdopen fails, the fd must be closed (no leak).

    When fdopen fails, the fd is still owned by us and must be explicitly closed.
    Currently it leaks.

    Before fix: fd is leaked (not closed)
    After fix: fd is closed properly
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track created fds to detect leaks
    created_fds = []

    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        created_fds.append(fd)
        return fd, path

    # Make fdopen fail to trigger the leak path
    def failing_fdopen(fd, *args, **kwargs):
        raise OSError("Simulated fdopen failure")

    import tempfile
    original_mkstemp_func = tempfile.mkstemp

    with (
        patch("tempfile.mkstemp", side_effect=tracking_mkstemp),
        patch("os.fdopen", side_effect=failing_fdopen),
        pytest.raises(OSError, match="Simulated fdopen failure"),
    ):
        storage.save([Todo(id=1, text="test")])

    # Restore original
    tempfile.mkstemp = original_mkstemp_func

    # Force garbage collection
    gc.collect()

    # Check that created fds are now closed
    for fd in created_fds:
        # Try to fstat the fd - it should fail (be closed)
        with pytest.raises(OSError, match="Bad file descriptor"):
            os.fstat(fd)


def test_fchmod_failure_cleans_up_temp_file(tmp_path) -> None:
    """Issue #2443: Temp file should be cleaned up even when fchmod fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    temp_files_created = []

    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    # Make fchmod fail
    def failing_fchmod(fd, mode):
        raise OSError("Simulated fchmod failure")

    import tempfile
    original_mkstemp_func = tempfile.mkstemp

    with (
        patch("tempfile.mkstemp", side_effect=tracking_mkstemp),
        patch("os.fchmod", side_effect=failing_fchmod),
        pytest.raises(OSError, match="Simulated fchmod failure"),
    ):
        storage.save([Todo(id=1, text="test")])

    # Restore original
    tempfile.mkstemp = original_mkstemp_func

    # Verify all temp files were cleaned up
    for temp_path in temp_files_created:
        assert not temp_path.exists(), (
            f"Temp file was not cleaned up after fchmod failure: {temp_path}"
        )


def test_fdopen_failure_cleans_up_temp_file(tmp_path) -> None:
    """Issue #2443: Temp file should be cleaned up even when fdopen fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    temp_files_created = []

    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    # Make fdopen fail
    def failing_fdopen(fd, *args, **kwargs):
        raise OSError("Simulated fdopen failure")

    import tempfile
    original_mkstemp_func = tempfile.mkstemp

    with (
        patch("tempfile.mkstemp", side_effect=tracking_mkstemp),
        patch("os.fdopen", side_effect=failing_fdopen),
        pytest.raises(OSError, match="Simulated fdopen failure"),
    ):
        storage.save([Todo(id=1, text="test")])

    # Restore original
    tempfile.mkstemp = original_mkstemp_func

    # Verify all temp files were cleaned up
    for temp_path in temp_files_created:
        assert not temp_path.exists(), (
            f"Temp file was not cleaned up after fdopen failure: {temp_path}"
        )


def test_normal_operation_still_works(tmp_path) -> None:
    """Issue #2443: Normal save operation should still work correctly."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Verify file was created correctly
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"
