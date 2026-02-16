"""Regression tests for issue #3650: os.fchmod is not available on Windows.

Issue: The code calls os.fchmod() directly on line 112 of storage.py, but
os.fchmod is not available on Windows, causing AttributeError.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_unavailable(tmp_path) -> None:
    """Issue #3650: save() should work on Windows where os.fchmod is not available.

    On Windows, os.fchmod does not exist. The code should gracefully handle
    this by either:
    1. Using os.chmod(path, mode) as a fallback on Windows
    2. Using getattr to check availability before calling os.fchmod

    This test simulates Windows by removing the fchmod attribute from os.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test todo")]

    # Simulate Windows by removing fchmod from the os module
    original_fchmod = getattr(os, "fchmod", None)

    # Remove fchmod to simulate Windows environment
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError
        storage.save(todos)

        # Verify data was saved correctly
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_uses_fchmod_on_unix_when_available(tmp_path) -> None:
    """Issue #3650: On Unix, save() should still use os.fchmod if available.

    This ensures that the fix doesn't break the existing Unix behavior.
    The fix should use os.fchmod when available (Unix) and fall back
    gracefully when not available (Windows).
    """
    # Skip this test if we're on Windows (fchmod not available)
    if not hasattr(os, "fchmod"):
        pytest.skip("os.fchmod not available on this platform")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test")]

    # Track if fchmod was called
    fchmod_calls = []
    original_fchmod = os.fchmod

    def tracking_fchmod(fd, mode):
        fchmod_calls.append((fd, mode))
        return original_fchmod(fd, mode)

    with patch.object(os, "fchmod", tracking_fchmod):
        storage.save(todos)

    # Verify fchmod was called with 0o600 permissions
    assert len(fchmod_calls) == 1, f"Expected 1 fchmod call, got {len(fchmod_calls)}"
    _fd, mode = fchmod_calls[0]
    assert mode == 0o600, f"Expected 0o600 mode, got {oct(mode)}"


def test_save_permissions_on_unix_like_platform(tmp_path) -> None:
    """Issue #3650: Verify file permissions are set correctly on Unix-like platforms.

    This test verifies that even with the Windows compatibility fix, the
    resulting file still has secure permissions (0o600) on Unix.
    """
    # Skip on Windows since permission checking is different there
    if not hasattr(os, "fchmod"):
        pytest.skip("Permission test requires Unix-like platform")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="secure todo")]

    storage.save(todos)

    # Check the file permissions
    import stat
    file_mode = stat.S_IMODE(db.stat().st_mode)
    assert file_mode == 0o600, (
        f"File should have 0o600 (rw-------) permissions, got {oct(file_mode)}"
    )
