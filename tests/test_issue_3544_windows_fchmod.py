"""Regression tests for issue #3544: os.fchmod() not available on Windows.

Issue: os.fchmod() is not available on Windows, causing save() to fail
on Windows platforms with AttributeError.

The fix should gracefully handle the absence of os.fchmod on Windows
while still setting restrictive permissions on Unix systems.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
from unittest import mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_handles_missing_fchmod_on_windows(tmp_path) -> None:
    """Issue #3544: save() should work on Windows where os.fchmod is not available.

    On Windows, os.fchmod does not exist and raises AttributeError.
    The save() function should handle this gracefully.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows environment where os.fchmod doesn't exist
    with mock.patch.object(os, 'fchmod', side_effect=AttributeError("module 'os' has no attribute 'fchmod'")):
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test")])

    # Verify the data was saved correctly
    assert db.exists()
    saved_todos = storage.load()
    assert len(saved_todos) == 1
    assert saved_todos[0].text == "test"


def test_save_still_sets_permissions_on_unix_when_fchmod_available(tmp_path) -> None:
    """Issue #3544: save() should still set 0o600 permissions on Unix.

    This test verifies that when os.fchmod IS available (Unix),
    the restrictive permissions are still set.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track if fchmod was called with correct permissions
    fchmod_calls = []

    original_fchmod = getattr(os, 'fchmod', None)

    if original_fchmod is None:
        # Skip on Windows since fchmod doesn't exist
        import pytest
        pytest.skip("os.fchmod not available on this platform")

    def tracking_fchmod(fd, mode):
        fchmod_calls.append((fd, mode))
        return original_fchmod(fd, mode)

    with mock.patch.object(os, 'fchmod', side_effect=tracking_fchmod):
        storage.save([Todo(id=1, text="test")])

    # Verify fchmod was called with 0o600
    assert len(fchmod_calls) == 1
    _, mode = fchmod_calls[0]
    assert mode == stat.S_IRUSR | stat.S_IWUSR, f"Expected 0o600, got {oct(mode)}"


def test_save_falls_back_gracefully_when_fchmod_fails(tmp_path) -> None:
    """Issue #3544: save() should handle fchmod failures gracefully.

    Even if os.fchmod exists but fails (e.g., on some filesystems),
    save() should still complete successfully.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate fchmod existing but failing (like on some filesystems)
    with mock.patch.object(os, 'fchmod', side_effect=OSError("Operation not permitted")):
        # This should NOT raise OSError - it should handle the error gracefully
        storage.save([Todo(id=1, text="test")])

    # Verify the data was saved correctly despite fchmod failure
    assert db.exists()
    saved_todos = storage.load()
    assert len(saved_todos) == 1
    assert saved_todos[0].text == "test"
