"""Regression tests for issue #2443: fchmod error handling and temp file cleanup.

Issue: If os.fchmod() fails after fdopen wraps the fd, we need proper error handling.
The fd is transferred to fdopen, so if fchmod fails after that point, the fd would
already be owned by the file object, and cleanup behavior needs to be correct.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_fchmod_failure_raises_oserror(tmp_path) -> None:
    """Issue #2443: fchmod failure should raise OSError with clear message.

    When os.fchmod fails, it should raise an OSError that gets propagated
    to the caller with a clear error message about permission issues.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Mock fchmod to fail
    with patch("os.fchmod", side_effect=OSError("[Errno 1] Operation not permitted")):
        with pytest.raises(OSError) as exc_info:
            storage.save([Todo(id=1, text="test")])

        # Verify it's an OSError about permissions
        assert "Operation not permitted" in str(exc_info.value) or "fchmod" in str(exc_info.value).lower()


def test_fchmod_failure_cleans_up_temp_file(tmp_path) -> None:
    """Issue #2443: When fchmod fails, temp file should be cleaned up.

    If os.fchmod fails, the temp file created by mkstemp should be
    removed to avoid leaving orphaned temp files.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    temp_files_created = []

    original_mkstemp = tempfile.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    with (
        patch("tempfile.mkstemp", side_effect=tracking_mkstemp),
        patch("os.fchmod", side_effect=OSError("[Errno 1] Operation not permitted")),
        pytest.raises(OSError),
    ):
        storage.save([Todo(id=1, text="test")])

    # Verify all temp files were cleaned up
    for temp_file in temp_files_created:
        assert not temp_file.exists(), (
            f"Temp file was not cleaned up after fchmod failure: {temp_file}"
        )


def test_write_failure_after_fdopen_cleans_up_temp_file(tmp_path) -> None:
    """Issue #2443: When write fails after fdopen, temp file should be cleaned up.

    This verifies that even though the fd is closed by the fdopen context manager,
    os.unlink can still remove the temp file. The fd being closed doesn't prevent unlink.

    This tests the actual behavior by making os.write fail (which is what
    f.write() ultimately calls), simulating a disk full condition.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    temp_files_created = []

    original_mkstemp = tempfile.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    # Patch os.write to fail (simulating disk full after fdopen succeeds)
    # We need to be careful here - we want the write to fail during f.write()
    with patch("tempfile.mkstemp", side_effect=tracking_mkstemp):
        # Use a custom file object that fails on write
        original_fdopen = os.fdopen

        class FailingWriteFile:
            """A file object wrapper that fails on write."""

            def __init__(self, fd, mode, encoding):
                # Open the real file
                self._file = original_fdopen(fd, mode, encoding=encoding)

            def write(self, content):
                # Fail on write to simulate disk full
                raise OSError("[Errno 28] No space left on device")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                # Ensure the real file is closed
                self._file.__exit__(*args)

        with (
            patch(
                "os.fdopen",
                side_effect=lambda fd, mode, encoding=None: FailingWriteFile(
                    fd, mode, encoding
                ),
            ),
            pytest.raises(OSError, match="No space left on device"),
        ):
            storage.save([Todo(id=1, text="test")])

    # Verify temp file was cleaned up even though fd was closed by context manager
    for temp_file in temp_files_created:
        assert not temp_file.exists(), (
            f"Temp file was not cleaned up after write failure: {temp_file}"
        )
