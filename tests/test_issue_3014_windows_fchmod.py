"""Regression tests for issue #3014: os.fchmod not available on Windows.

Issue: os.fchmod is not available on Windows, causing AttributeError when
saving todos on Windows platform.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
from unittest import mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_unavailable(tmp_path) -> None:
    """Issue #3014: save() should work when os.fchmod is not available.

    On Windows, os.fchmod does not exist. The code should fall back to
    os.chmod or handle the missing function gracefully.

    Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() completes successfully
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows environment where fchmod is not available
    with mock.patch.object(os, "fchmod", None, create=True):
        # This should not raise AttributeError
        storage.save([Todo(id=1, text="test")])

    # Verify the file was actually saved
    assert db.exists(), "Database file should be created"

    # Verify content is correct
    storage2 = TodoStorage(str(db))
    todos = storage2.load()
    assert len(todos) == 1
    assert todos[0].text == "test"


def test_save_works_without_fchmod_attribute(tmp_path) -> None:
    """Issue #3014: save() should handle missing fchmod attribute.

    This test ensures the code uses hasattr or try/except to handle
    the missing fchmod function on Windows.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Completely remove fchmod attribute to simulate Windows
    original_fchmod = getattr(os, "fchmod", None)
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should not raise AttributeError
        storage.save([Todo(id=2, text="test without fchmod")])

        # Verify the file was saved
        assert db.exists(), "Database file should be created"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_uses_chmod_on_windows(tmp_path) -> None:
    """Issue #3014: On Windows, chmod should be used instead of fchmod.

    Verify that when fchmod is unavailable, chmod is used as fallback.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    chmod_called = []

    original_chmod = os.chmod

    def tracking_chmod(path, mode, *args, **kwargs):
        chmod_called.append((path, mode))
        return original_chmod(path, mode, *args, **kwargs)

    # Simulate Windows environment where fchmod is not available
    with (
        mock.patch.object(os, "fchmod", None, create=True),
        mock.patch.object(os, "chmod", tracking_chmod),
    ):
        storage.save([Todo(id=3, text="test chmod fallback")])

    # Verify chmod was called with restrictive permissions (0o600)
    assert len(chmod_called) > 0, "os.chmod should have been called as fallback"

    for _path, mode in chmod_called:
        # On Unix, the mode should be 0o600 (rw-------)
        # We verify at least owner read/write is set
        assert mode & stat.S_IRUSR, f"chmod should set owner read bit: {oct(mode)}"
        assert mode & stat.S_IWUSR, f"chmod should set owner write bit: {oct(mode)}"
