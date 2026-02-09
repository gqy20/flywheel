"""Regression tests for issue #2443: fchmod failure after fdopen may cause resource leaks.

Issue: If os.fchmod fails after os.fdopen transfers ownership of fd, the fd
is already closed by fdopen context manager, but os.unlink(temp_path) in the
except handler may fail silently with suppress. This could leave temp files
on disk.

The fix should ensure:
1. fchmod is called BEFORE fdopen transfers ownership (already correct order)
2. fchmod failures are properly handled and reported
3. Temp file cleanup happens even when fchmod fails
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_fchmod_failure_raises_oserror(tmp_path) -> None:
    """Issue #2443: fchmod failure should raise OSError, not be silently ignored.

    This test verifies that if os.fchmod fails, the error is properly propagated
    to the caller rather than being silently suppressed.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    def failing_fchmod(fd, mode):
        raise OSError(errno.EPERM, "Operation not permitted")

    import errno

    with (
        patch("flywheel.storage.os.fchmod", failing_fchmod),
        pytest.raises(OSError, match="Operation not permitted"),
    ):
        storage.save([Todo(id=1, text="test")])


def test_fchmod_failure_cleans_up_temp_file(tmp_path) -> None:
    """Issue #2443: When fchmod fails, temp file should be cleaned up.

    This test verifies that if os.fchmod fails during temp file creation,
    the temp file is properly removed and not left on disk.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    temp_files_created = []

    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    def failing_fchmod(fd, mode):
        raise OSError(errno.EPERM, "Operation not permitted")

    import errno

    with (
        patch("flywheel.storage.os.fchmod", failing_fchmod),
        patch("tempfile.mkstemp", tracking_mkstemp),
        pytest.raises(OSError, match="Operation not permitted"),
    ):
        storage.save([Todo(id=1, text="test")])

    # Verify all temp files were cleaned up
    for temp_file in temp_files_created:
        assert not temp_file.exists(), (
            f"Temp file was not cleaned up after fchmod failure: {temp_file}"
        )


def test_fchmod_called_before_fdopen(tmp_path) -> None:
    """Issue #2443: fchmod should be called BEFORE fdopen wraps the fd.

    This is a correctness test - the current order is correct, but we want to
    ensure it stays correct. fchmod must be called on the raw fd before fdopen
    transfers ownership.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    call_order = []

    original_fchmod = os.fchmod
    original_fdopen = os.fdopen

    def tracking_fchmod(fd, mode):
        call_order.append("fchmod")
        return original_fchmod(fd, mode)

    def tracking_fdopen(fd, *args, **kwargs):
        call_order.append("fdopen")
        return original_fdopen(fd, *args, **kwargs)

    with (
        patch("flywheel.storage.os.fchmod", tracking_fchmod),
        patch("flywheel.storage.os.fdopen", tracking_fdopen),
    ):
        storage.save([Todo(id=1, text="test")])

    # fchmod must be called before fdopen
    assert call_order == ["fchmod", "fdopen"], (
        f"fchmod must be called before fdopen, got order: {call_order}"
    )
