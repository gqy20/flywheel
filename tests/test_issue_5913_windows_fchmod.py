"""Regression tests for issue #5913: os.fchmod is Unix-only, causing AttributeError on Windows.

Issue: The code uses os.fchmod() which is Unix-only. On Windows, this causes
an AttributeError because os.fchmod does not exist on that platform.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path) -> None:
    """Issue #5913: TodoStorage.save() should work on Windows without AttributeError.

    On Windows, os.fchmod does not exist. The code should gracefully handle
    this by either skipping the permission setting or using a fallback.

    Before fix: AttributeError: module 'os' has no attribute 'fchmod'
    After fix: No error, save completes successfully
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by removing fchmod from os temporarily
    original_fchmod = getattr(os, "fchmod", None)

    # Remove fchmod to simulate Windows environment
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test on simulated Windows")])

        # Verify the save was successful
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test on simulated Windows"

    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_with_fchmod_hasattr_false(tmp_path) -> None:
    """Issue #5913: Verify that hasattr check is used for os.fchmod.

    This test ensures the code uses a proper platform check (hasattr)
    rather than assuming os.fchmod exists.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by removing fchmod from os temporarily
    # This tests that the code uses hasattr to check for fchmod availability
    original_fchmod = getattr(os, "fchmod", None)

    # Remove fchmod to simulate Windows environment
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError because the fix uses hasattr check
        storage.save([Todo(id=1, text="test with hasattr False")])

        # Verify the save was successful
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test with hasattr False"

    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_works_on_windows_platform(tmp_path) -> None:
    """Issue #5913: Ensure save() works when sys.platform is 'win32'.

    This test simulates running on Windows platform to ensure the code
    handles the Windows case properly.
    """
    import sys

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Patch sys.platform to simulate Windows
    with patch.object(sys, "platform", "win32"):
        # Also ensure fchmod is not available (as on real Windows)
        original_fchmod = getattr(os, "fchmod", None)
        if hasattr(os, "fchmod"):
            delattr(os, "fchmod")

        try:
            # This should NOT raise AttributeError on simulated Windows
            storage.save([Todo(id=1, text="Windows test")])

            # Verify the save was successful
            loaded = storage.load()
            assert len(loaded) == 1
            assert loaded[0].text == "Windows test"

        finally:
            # Restore fchmod if it existed
            if original_fchmod is not None:
                os.fchmod = original_fchmod
