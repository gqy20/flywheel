"""Regression tests for issue #5971: os.fchmod() is Unix-only, raises AttributeError on Windows.

Issue: The save() method uses os.fchmod() which is not available on Windows,
causing AttributeError when the code runs on Windows.

The fix should gracefully handle the absence of os.fchmod on Windows by
wrapping the call in a try/except or using hasattr check.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import contextlib
import os
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path) -> None:
    """Issue #5971: save() should work on Windows without AttributeError.

    On Windows, os.fchmod does not exist. The code should gracefully handle
    this and still complete the save operation successfully.

    Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() completes successfully, skipping chmod on Windows
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows environment where os.fchmod doesn't exist
    original_fchmod = getattr(os, 'fchmod', None)

    # Create a mock that simulates Windows behavior (no fchmod)
    mock_os = type(os)('os')
    for attr in dir(os):
        if attr != 'fchmod':
            with contextlib.suppress(AttributeError, TypeError):
                setattr(mock_os, attr, getattr(os, attr))

    todos = [Todo(id=1, text="test todo")]

    with patch.dict('flywheel.storage.os.__dict__', {'fchmod': None}):
        # Remove fchmod from os module temporarily
        if hasattr(os, 'fchmod'):
            delattr(os, 'fchmod')

        try:
            # This should NOT raise AttributeError
            storage.save(todos)
        finally:
            # Restore original fchmod if it existed
            if original_fchmod is not None:
                os.fchmod = original_fchmod

    # Verify the save was successful
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_handles_oserror_from_fchmod(tmp_path) -> None:
    """Issue #5971: save() should catch OSError from os.fchmod.

    This tests the scenario where fchmod is available but fails
    (e.g., permission issues, invalid fd, etc.).
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    def fake_fchmod(*args, **kwargs):
        """Simulate fchmod failing with OSError."""
        raise OSError("Simulated fchmod failure")

    todos = [Todo(id=1, text="test todo")]

    # Patch os.fchmod to raise OSError
    with patch.object(os, 'fchmod', fake_fchmod):
        # This should NOT raise OSError - it should be caught
        storage.save(todos)

    # Verify the save was successful
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1


def test_save_still_sets_permissions_on_unix(tmp_path) -> None:
    """Issue #5971: On Unix, fchmod should still be called to set 0o600 permissions.

    This ensures the fix doesn't break the security feature on Unix systems
    where fchmod is available.
    """
    # Skip this test on Windows since fchmod doesn't exist
    if not hasattr(os, 'fchmod'):
        pytest.skip("os.fchmod not available on this platform (Windows)")

    import stat

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track if fchmod was called
    fchmod_calls = []
    original_fchmod = os.fchmod

    def tracking_fchmod(fd, mode):
        fchmod_calls.append((fd, mode))
        return original_fchmod(fd, mode)

    todos = [Todo(id=1, text="test todo")]

    with patch.object(os, 'fchmod', tracking_fchmod):
        storage.save(todos)

    # Verify fchmod was called with correct mode (0o600)
    assert len(fchmod_calls) == 1, "fchmod should be called exactly once"
    assert fchmod_calls[0][1] == stat.S_IRUSR | stat.S_IWUSR, \
        f"fchmod should be called with 0o600 mode, got {oct(fchmod_calls[0][1])}"
