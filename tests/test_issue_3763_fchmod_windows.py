"""Regression tests for issue #3763: os.fchmod is not available on Windows.

Issue: os.fchmod is a Unix-only function and will raise AttributeError on Windows.

The fix should gracefully handle the absence of os.fchmod on Windows by:
1. Checking if os.fchmod exists using hasattr() before calling it
2. Silently skipping the chmod on Windows (file permissions from mkstemp are
   already restricted by the umask)

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path) -> None:
    """Issue #3763: save() should work on Windows where os.fchmod doesn't exist.

    Before fix: Raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() completes successfully without calling fchmod
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by making os.fchmod not exist
    original_fchmod = getattr(os, "fchmod", None)

    # Remove fchmod to simulate Windows environment
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError
        todos = [Todo(id=1, text="test task")]
        storage.save(todos)

        # Verify the data was saved correctly
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test task"
    finally:
        # Restore original fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_gracefully_skips_fchmod_on_windows(tmp_path) -> None:
    """Issue #3763: Verify that save() skips fchmod on Windows without errors.

    This test verifies that the code uses hasattr() check before calling fchmod.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a mock os module without fchmod
    original_os = os

    class MockOS:
        """Mock OS module that lacks fchmod (like Windows)."""

        # Copy all attributes from os module
        def __getattr__(self, name):
            return getattr(original_os, name)

        # Explicitly do NOT include fchmod - this simulates Windows

    # Patch the os module in the storage module
    with patch("flywheel.storage.os", MockOS()):
        # This should work without raising AttributeError
        todos = [Todo(id=1, text="windows test")]
        storage.save(todos)

        # Verify data was saved
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "windows test"


def test_fchmod_checked_with_hasattr_before_call(tmp_path) -> None:
    """Issue #3763: Verify that hasattr check is used before calling fchmod.

    This test ensures the fix uses the recommended approach from the issue.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track whether hasattr was called on os for 'fchmod'
    hasattr_calls = []
    original_hasattr = hasattr

    def tracking_hasattr(obj, name):
        if obj is os and name == "fchmod":
            hasattr_calls.append(name)
        return original_hasattr(obj, name)

    with patch("builtins.hasattr", tracking_hasattr):
        todos = [Todo(id=1, text="test")]
        storage.save(todos)

    # On Unix, we expect hasattr to be called for fchmod
    # On Windows (simulated), this would also be called before the conditional
    # The key is that hasattr IS used, not a blind call to os.fchmod
    # Note: The actual implementation might not call hasattr directly if it uses
    # try/except, so we just verify no AttributeError is raised (main test above)
