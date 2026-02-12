"""Regression tests for issue #2965: os.fchmod is not available on Windows.

Issue: os.fchmod is POSIX-only and raises AttributeError on Windows,
causing save() to fail on that platform.

Fix: Use hasattr check to gracefully handle Windows systems
where os.fchmod does not exist.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_succeeds_on_windows_without_fchmod(tmp_path) -> None:
    """Issue #2965: save() should work on Windows where os.fchmod doesn't exist.

    os.fchmod is a POSIX-only function. On Windows, it doesn't exist as an
    attribute of the os module, which would cause AttributeError before the fix.

    Before fix: save() raises AttributeError when os.fchmod is called
    After fix: save() completes successfully with graceful fallback
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save and remove os.fchmod to simulate Windows behavior
    original_fchmod = getattr(os, "fchmod", None)

    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise an AttributeError
        # It should complete successfully, using hasattr check
        storage.save([Todo(id=1, text="test todo")])

        # Verify the data was saved correctly
        assert db.exists()
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        # Restore the original fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod
