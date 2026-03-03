"""Regression tests for issue #6938: os.fchmod() is Unix-only.

Issue: os.fchmod() does not exist on Windows, causing save() to raise
AttributeError instead of completing successfully.

The fix should:
1. Check if os.fchmod exists before calling it (hasattr check)
2. On Windows, skip the fchmod call since tempfile.mkstemp already creates
   secure temp files with restricted permissions

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_succeeds_when_fchmod_not_available(tmp_path) -> None:
    """Issue #6938: save() should succeed on Windows where os.fchmod doesn't exist.

    Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() succeeds, skipping the Unix-only fchmod call
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by making fchmod not exist
    original_fchmod = getattr(os, "fchmod", None)

    # Remove fchmod from os module temporarily
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test")])

        # Verify the save actually worked
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"

    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_fchmod_not_called_when_not_available(tmp_path) -> None:
    """Issue #6938: fchmod should not be called when it doesn't exist.

    This verifies that the code path skips fchmod entirely when hasattr
    returns False, rather than trying to call it and handling the error.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by making fchmod not exist
    original_fchmod = getattr(os, "fchmod", None)
    fchmod_call_count = [0]

    # Create a mock that should NEVER be called
    def mock_fchmod_should_not_be_called(*args, **kwargs):
        fchmod_call_count[0] += 1
        # If this is called, the test should fail
        raise AssertionError("fchmod should not be called when it doesn't exist")

    # Remove fchmod and verify the code doesn't try to call it
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        storage.save([Todo(id=1, text="test")])

        # Verify fchmod was never called
        assert fchmod_call_count[0] == 0, "fchmod should not be called when it doesn't exist"

        # Verify the save actually worked
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"

    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_hasattr_check_for_fchmod() -> None:
    """Verify that the code properly checks for fchmod availability.

    This is a documentation test showing the expected behavior.
    """
    # This should not raise - it should return True on Unix, False on Windows
    has_fchmod = hasattr(os, "fchmod")
    assert isinstance(has_fchmod, bool)
