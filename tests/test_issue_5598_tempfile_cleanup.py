"""Regression test for issue #5598: Temp file cleanup on non-OSError exceptions.

This test verifies that save() cleans up temporary files when exceptions
other than OSError occur inside the try block (e.g., during file write operations).

The bug: save() exception handler at line 121 only catches OSError, but other
exceptions (like ValueError, RuntimeError) could occur during f.write() or
other operations inside the try block, leaving temp files orphaned.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_temp_file_cleaned_up_on_runtime_error_in_try_block(tmp_path: Path) -> None:
    """Test that temp file is cleaned up when a non-OSError exception occurs in try block.

    Regression test for issue #5598: save() exception handler only catches OSError
    but other exceptions can occur inside the try block, leaving temp files orphaned.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Track temp files created during save attempts
    temp_files_created: list[Path] = []
    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    import os
    import tempfile

    # Mock os.fchmod to raise a RuntimeError (non-OSError exception)
    # This simulates an unexpected error inside the try block
    def failing_fchmod(*args, **kwargs):
        raise RuntimeError("Unexpected runtime error during fchmod")

    with (
        patch.object(os, "fchmod", failing_fchmod),
        patch.object(tempfile, "mkstemp", tracking_mkstemp),
        pytest.raises(RuntimeError, match="Unexpected runtime error"),
    ):
        storage.save(todos)

    # Verify temp file was created
    assert len(temp_files_created) == 1, "Expected one temp file to be created"

    # CRITICAL: Verify temp file was cleaned up (this is the bug)
    temp_file = temp_files_created[0]
    assert not temp_file.exists(), (
        f"Temp file {temp_file} should be cleaned up after RuntimeError. "
        "This is the bug from issue #5598."
    )


def test_temp_file_cleaned_up_on_value_error_during_write(tmp_path: Path) -> None:
    """Test that temp file is cleaned up when ValueError occurs during file write.

    This simulates a case where f.write() raises a non-OSError exception.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Track temp files created during save attempts
    temp_files_created: list[Path] = []
    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    import os
    import tempfile

    # Track the file descriptor and mock os.fdopen to return a failing file object
    captured_fd = []

    original_fdopen = os.fdopen

    class FailingFile:
        def __init__(self, fd):
            self.fd = fd

        def write(self, content):
            raise ValueError("Simulated encoding error during write")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def failing_fdopen(fd, *args, **kwargs):
        captured_fd.append(fd)
        return FailingFile(fd)

    with (
        patch.object(os, "fdopen", failing_fdopen),
        patch.object(tempfile, "mkstemp", tracking_mkstemp),
        pytest.raises(ValueError, match="encoding error"),
    ):
        storage.save(todos)

    # Verify temp file was created
    assert len(temp_files_created) == 1, "Expected one temp file to be created"

    # CRITICAL: Verify temp file was cleaned up (this is the bug)
    temp_file = temp_files_created[0]
    assert not temp_file.exists(), (
        f"Temp file {temp_file} should be cleaned up after ValueError. "
        "This is the bug from issue #5598."
    )


def test_exception_still_propagated_after_temp_file_cleanup(tmp_path: Path) -> None:
    """Test that the original exception is still propagated after cleanup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    import os

    # Mock os.fchmod to raise a specific RuntimeError
    def failing_fchmod(*args, **kwargs):
        raise RuntimeError("Custom error for propagation test")

    with (
        patch.object(os, "fchmod", failing_fchmod),
        pytest.raises(RuntimeError, match="Custom error for propagation test") as exc_info,
    ):
        storage.save(todos)

    # Verify the exception was propagated correctly
    assert "Custom error for propagation test" in str(exc_info.value)


def test_no_tmp_files_remain_after_failed_save_with_runtime_error(
    tmp_path: Path,
) -> None:
    """Verify no .tmp files remain after failed save with non-OSError exception."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    import os

    # Mock os.fchmod to raise RuntimeError
    def failing_fchmod(*args, **kwargs):
        raise RuntimeError("Unexpected error")

    with (
        patch.object(os, "fchmod", failing_fchmod),
        pytest.raises(RuntimeError),
    ):
        storage.save(todos)

    # List all .tmp files in the directory
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0, (
        f"No .tmp files should remain after failed save. Found: {tmp_files}"
    )
