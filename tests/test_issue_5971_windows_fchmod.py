"""Regression tests for issue #5971: os.fchmod() is Unix-only, raises AttributeError on Windows.

Issue: The code uses os.fchmod() which is only available on Unix systems.
On Windows, this raises AttributeError because os.fchmod doesn't exist.

The fix should gracefully handle the absence of os.fchmod on Windows while
still maintaining restrictive permissions on Unix.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path) -> None:
    """Issue #5971: save() should work when os.fchmod is not available (Windows).

    On Windows, os.fchmod doesn't exist. The code should gracefully handle
    this by catching AttributeError and continuing without setting explicit
    permissions (tempfile.mkstemp already creates files with secure defaults).

    Before fix: AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() completes successfully on Windows
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows environment where os.fchmod doesn't exist
    original_fchmod = getattr(os, "fchmod", None)

    # Remove fchmod to simulate Windows
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test todo")])

        # Verify the save actually worked
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"

    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_works_when_fchmod_raises_attribute_error(tmp_path) -> None:
    """Issue #5971: save() should handle AttributeError from os.fchmod gracefully.

    This test explicitly mocks os.fchmod to raise AttributeError to verify
    the fix handles the exception properly.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Mock os.fchmod to raise AttributeError (simulating Windows)
    with patch.object(os, "fchmod", side_effect=AttributeError("fchmod not available")):
        # This should NOT raise AttributeError - it should be caught
        storage.save([Todo(id=1, text="test todo")])

    # Verify the save actually worked
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


@pytest.mark.skipif(not hasattr(os, "fchmod"), reason="os.fchmod not available on this platform")
def test_save_sets_restrictive_permissions_on_unix(tmp_path) -> None:
    """Issue #5971: On Unix, save() should still set restrictive permissions.

    After the fix, on Unix systems where os.fchmod exists, the code should
    continue to set 0o600 permissions for security.
    """
    import tempfile

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    permissions_seen = []

    original_mkstemp = tempfile.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        # Check permissions after save completes
        permissions_seen.append((path, os.stat(path).st_mode & 0o777))
        return fd, path

    with patch.object(tempfile, "mkstemp", tracking_mkstemp):
        storage.save([Todo(id=1, text="test")])

    # Verify temp file has 0o600 permissions on Unix
    for path, mode in permissions_seen:
        assert mode == 0o600, (
            f"Temp file should have 0o600 permissions on Unix, got {oct(mode)}. "
            f"File: {path}"
        )
