"""Tests for file descriptor leak fix (issue #7203).

This test verifies that file descriptors are properly closed if os.fdopen()
raises an exception during write operations in TodoStorage.save().
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_fd_does_not_leak_when_fdopen_fails(tmp_path: Path) -> None:
    """Test that fd is closed if os.fdopen() raises an exception.

    Regression test for issue #7203:
    If os.fdopen() raises an exception, the file descriptor should be
    properly closed to prevent resource leaks.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track file descriptors before the operation
    initial_fds = set(os.listdir("/proc/self/fd"))

    # Mock os.fdopen to raise an exception, simulating a failure
    # This happens AFTER mkstemp creates the fd, so fd needs to be cleaned up

    def failing_fdopen(fd, *args, **kwargs):
        # Close the fd to simulate what would happen if fdopen failed
        # before taking ownership - but our fix should have already closed it
        raise OSError("Simulated fdopen failure")

    with (
        patch("flywheel.storage.os.fdopen", failing_fdopen),
        pytest.raises(OSError, match="Simulated fdopen failure"),
    ):
        storage.save([Todo(id=1, text="test")])

    # Check file descriptors after the operation
    final_fds = set(os.listdir("/proc/self/fd"))

    # The fd should have been closed, so the fd count should be the same
    # Allow some tolerance for other operations, but the fd from mkstemp
    # should definitely be closed
    leaked_fds = final_fds - initial_fds

    # Filter out any fds that might be from other sources (like logging, etc)
    # We're mainly checking that we didn't leave a single fd open from our test
    assert len(leaked_fds) == 0, (
        f"File descriptor leak detected: {len(leaked_fds)} fds were not closed"
    )


def test_temp_file_cleaned_up_when_fdopen_fails(tmp_path: Path) -> None:
    """Test that temp file is cleaned up if os.fdopen() raises an exception.

    This ensures that both the fd and the temp file path are cleaned up
    when os.fdopen() fails.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track temp files in the directory before the operation
    initial_temp_files = list(tmp_path.glob(".*.tmp"))

    # Mock os.fdopen to raise an exception
    with (
        patch("flywheel.storage.os.fdopen", side_effect=OSError("Simulated fdopen failure")),
        pytest.raises(OSError, match="Simulated fdopen failure"),
    ):
        storage.save([Todo(id=1, text="test")])

    # Check temp files after the operation
    final_temp_files = list(tmp_path.glob(".*.tmp"))

    # No new temp files should remain
    assert len(final_temp_files) == len(initial_temp_files), (
        f"Temp file leak detected: {final_temp_files}"
    )


def test_normal_save_still_works_after_fix(tmp_path: Path) -> None:
    """Test that normal save operations still work correctly after the fix."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # This should work normally without any mocks
    storage.save(todos)

    # Verify the data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].id == 1
    assert loaded[0].text == "test todo"
