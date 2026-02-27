"""Regression tests for issue #6157: os.fchmod is Unix-only.

Issue: os.fchmod is Unix-only and will raise AttributeError on Windows platforms.
The code needs to handle the case where os.fchmod is not available.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_unavailable(tmp_path) -> None:
    """Issue #6157: save() should work when os.fchmod is not available (Windows).

    On Windows, os.fchmod does not exist and accessing it raises AttributeError.
    The code should handle this gracefully by either:
    1. Catching AttributeError and continuing
    2. Using a cross-platform alternative like os.chmod after file creation

    Before fix: save() raises AttributeError on Windows
    After fix: save() completes successfully without AttributeError
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by making fchmod unavailable
    # We need to patch at the module level where it's used

    # Create a mock that raises AttributeError (simulating Windows)
    def mock_fchmod(*args, **kwargs):
        raise AttributeError("module 'os' has no attribute 'fchmod'")

    with patch.object(os, "fchmod", mock_fchmod):
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test")])

    # Verify the file was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_save_works_without_fchmod_attribute(tmp_path) -> None:
    """Issue #6157: save() should work when os module has no fchmod attribute.

    This tests the case where the attribute simply doesn't exist,
    which is the actual behavior on Windows.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Store the original fchmod if it exists
    original_fchmod = getattr(os, "fchmod", None)

    # Remove fchmod attribute if it exists, simulating Windows
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="windows test")])

        # Verify the file was saved correctly
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "windows test"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod
