"""Regression tests for issue #6065: os.fchmod is Unix-only.

Issue: os.fchmod raises AttributeError on Windows because it's not available.
The code should gracefully handle Windows by skipping the fchmod call.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from unittest import mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_handles_missing_fchmod_gracefully(tmp_path) -> None:
    """Issue #6065: save() should work when os.fchmod is not available.

    Simulates Windows environment where os.fchmod doesn't exist by
    temporarily removing it from the os module.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save original fchmod if it exists
    original_fchmod = getattr(os, "fchmod", None)

    # Simulate Windows by removing fchmod
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test")])

        # Verify the save actually worked
        assert db.exists()
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"
    finally:
        # Restore original fchmod
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_fchmod_used_on_unix_platforms(tmp_path) -> None:
    """Issue #6065: fchmod should still be used on Unix when available.

    This ensures the fix doesn't break Unix behavior by always skipping fchmod.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Only run this test if fchmod is available (Unix)
    if not hasattr(os, "fchmod"):
        return

    # Track if fchmod was called
    fchmod_calls = []

    original_fchmod = os.fchmod

    def tracking_fchmod(fd, mode):
        fchmod_calls.append((fd, mode))
        return original_fchmod(fd, mode)

    with mock.patch.object(os, "fchmod", side_effect=tracking_fchmod):
        storage.save([Todo(id=1, text="unix test")])

    # Verify fchmod was called on Unix
    assert len(fchmod_calls) > 0, "fchmod should be called on Unix platforms"

    # Verify the mode was set to 0o600 (owner read/write only)
    for _fd, mode in fchmod_calls:
        assert mode == 0o600, f"Expected mode 0o600, got {oct(mode)}"
