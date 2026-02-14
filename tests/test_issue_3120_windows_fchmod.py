"""Regression test for issue #3120: os.fchmod is Unix-only.

os.fchmod is not available on Windows and will raise AttributeError.
This test ensures the code handles this gracefully on Windows platforms.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_on_windows_without_fchmod(tmp_path) -> None:
    """Test that save works on Windows where os.fchmod does not exist.

    Regression test for issue #3120: os.fchmod is Unix-only and raises
    AttributeError on Windows.

    This test simulates Windows by removing fchmod from the os module
    and verifies that save() still works correctly.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Save the original fchmod (may be None on Windows)
    original_fchmod = getattr(os, "fchmod", None)

    # Simulate Windows by removing fchmod from os module
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError on Windows
        storage.save(todos)

        # Verify the data was saved correctly
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_on_unix_with_fchmod(tmp_path) -> None:
    """Test that save still uses fchmod on Unix when available.

    This verifies that the fix doesn't break Unix functionality.
    """
    # Skip this test on Windows where fchmod doesn't exist
    if not hasattr(os, "fchmod"):
        pytest.skip("os.fchmod not available on this platform")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="unix test")]

    # Track if fchmod was called
    original_fchmod = os.fchmod
    fchmod_calls = []

    def tracking_fchmod(fd, mode):
        fchmod_calls.append((fd, mode))
        return original_fchmod(fd, mode)

    with patch.object(os, "fchmod", tracking_fchmod):
        storage.save(todos)

    # Verify fchmod was called
    assert len(fchmod_calls) == 1
    # Verify permissions were set to 0o600 (owner read/write only)
    assert fchmod_calls[0][1] == 0o600

    # Verify the data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "unix test"
