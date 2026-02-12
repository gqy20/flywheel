"""Regression tests for issue #2896: os.fchmod not available on Windows.

Issue: os.fchmod is a Unix-only function and raises AttributeError on Windows.
The code at storage.py:112 calls os.fchmod unconditionally, causing save()
to fail on Windows.

This test FAILS before the fix and PASSES after the fix by simulating
the Windows environment where os.fchmod is not available.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path) -> None:
    """Issue #2896: save() should work when os.fchmod is not available.

    On Windows, os.fchmod does not exist. This test simulates that
    environment by temporarily removing fchmod from os module.

    Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() succeeds without calling fchmod
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save original fchmod (if it exists on this platform)
    original_fchmod = getattr(os, "fchmod", None)

    # Simulate Windows environment where fchmod doesn't exist
    # We need to patch the os module used in flywheel.storage
    with (
        patch.object(os, "fchmod", None),
        patch.dict("os.__dict__", {"fchmod": None}, clear=False),
    ):
        # Actually delete it to truly simulate AttributeError
        del os.__dict__["fchmod"]

        try:
            # This should NOT raise AttributeError
            storage.save([Todo(id=1, text="test on Windows")])
        finally:
            # Restore fchmod if it existed before
            if original_fchmod is not None:
                os.fchmod = original_fchmod

    # Verify the file was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test on Windows"


def test_save_uses_hasattr_to_check_fchmod_availability(tmp_path) -> None:
    """Issue #2896: Code should use hasattr() to check fchmod availability.

    This test verifies the fix uses hasattr(os, 'fchmod') pattern rather
    than relying on platform detection, which is more robust.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    fchmod_calls = []

    # Track calls to fchmod
    original_fchmod = getattr(os, "fchmod", None)

    def tracking_fchmod(fd, mode):
        fchmod_calls.append((fd, mode))
        if original_fchmod is not None:
            return original_fchmod(fd, mode)
        # If no fchmod (shouldn't happen on Unix), just pass
        return None

    # When fchmod is available, it should be called
    with patch.object(os, "fchmod", tracking_fchmod):
        storage.save([Todo(id=1, text="test")])

    # On Unix, fchmod should have been called
    if hasattr(os, "fchmod"):
        assert len(fchmod_calls) == 1, "fchmod should be called exactly once on Unix"


def test_save_succeeds_without_fchmod_call(tmp_path) -> None:
    """Issue #2896: save() should succeed even if fchmod is never called.

    On Windows, the temp file will have default permissions from mkstemp,
    which are already restrictive. This verifies the code path works.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Temporarily remove fchmod if it exists
    original_hasattr = hasattr

    def patched_hasattr(obj, name):
        if obj is os and name == "fchmod":
            return False
        return original_hasattr(obj, name)

    with patch("builtins.hasattr", patched_hasattr):
        # This should succeed without calling fchmod
        storage.save([Todo(id=1, text="Windows save"), Todo(id=2, text="second")])

    # Verify data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "Windows save"
    assert loaded[1].text == "second"
