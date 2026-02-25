"""Tests for file descriptor leak fix (Issue #5639).

This test verifies that file descriptors are properly closed when
os.fchmod fails before os.fdopen takes ownership of the fd.

Bug: If os.fchmod(fd, ...) raises OSError, the fd leaks because
os.fdopen hasn't been called yet to take ownership.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_fd_closed_on_fchmod_failure(tmp_path) -> None:
    """Regression test for issue #5639: fd must be closed if fchmod fails.

    When os.fchmod raises OSError, the file descriptor should still be
    closed to prevent resource leaks. This test mocks fchmod to fail
    and verifies that no fd is leaked.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Get open fd count before the test
    # We'll track fds by checking what mkstemp returns and ensuring it gets closed
    opened_fds = []
    original_mkstemp = __import__("tempfile").mkstemp
    closed_fds = []

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        opened_fds.append(fd)
        return fd, path

    # Mock os.close to track which fds get closed
    original_close = os.close

    def tracking_close(fd, *args, **kwargs):
        closed_fds.append(fd)
        return original_close(fd, *args, **kwargs)

    # Mock fchmod to fail
    def failing_fchmod(fd, mode):
        raise OSError("Simulated fchmod failure")

    import tempfile

    with (
        patch.object(tempfile, "mkstemp", tracking_mkstemp),
        patch("flywheel.storage.os.fchmod", failing_fchmod),
        patch("flywheel.storage.os.close", tracking_close),
        pytest.raises(OSError, match="Simulated fchmod failure"),
    ):
        storage.save(todos)

    # Verify that the fd that was opened has been closed
    assert len(opened_fds) == 1, f"Expected 1 fd to be opened, got {len(opened_fds)}"
    opened_fd = opened_fds[0]

    # The fd should have been closed explicitly
    assert opened_fd in closed_fds, (
        f"File descriptor {opened_fd} was not closed after fchmod failure. "
        f"Closed fds: {closed_fds}"
    )


def test_temp_file_cleaned_up_on_fchmod_failure(tmp_path) -> None:
    """Test that temp file is cleaned up when fchmod fails.

    Even if fchmod fails, the temporary file should be removed
    to avoid leaving orphaned files.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Track temp file paths
    temp_files = []
    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files.append(path)
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
        storage.save(todos)

    # Verify temp file was cleaned up
    assert len(temp_files) == 1, f"Expected 1 temp file, got {len(temp_files)}"
    temp_path = temp_files[0]
    assert not os.path.exists(temp_path), (
        f"Temp file {temp_path} should have been cleaned up after fchmod failure"
    )


def test_original_file_preserved_on_fchmod_failure(tmp_path) -> None:
    """Test that original file is preserved if fchmod fails.

    If we have an existing file and fchmod fails during save,
    the original file should remain intact.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Get original content
    original_content = db.read_text(encoding="utf-8")

    # Mock fchmod to fail
    def failing_fchmod(fd, mode):
        raise OSError("Simulated fchmod failure")

    with (
        patch("flywheel.storage.os.fchmod", failing_fchmod),
        pytest.raises(OSError, match="Simulated fchmod failure"),
    ):
        storage.save([Todo(id=3, text="new")])

    # Original file should be unchanged
    assert db.read_text(encoding="utf-8") == original_content

    # Verify we can still load original data
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "original"
    assert loaded[1].text == "data"
