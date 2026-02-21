"""Regression tests for issue #4834: os.fchmod is Unix-only.

Issue: os.fchmod is Unix-only and will raise AttributeError on Windows.
The code should gracefully handle the absence of os.fchmod on Windows.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_without_fchmod(tmp_path) -> None:
    """Issue #4834: save() should work on Windows without os.fchmod.

    Simulates Windows environment where os.fchmod does not exist.
    Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() completes successfully without error.
    """
    import os

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save original fchmod
    original_fchmod = getattr(os, "fchmod", None)

    # Remove fchmod to simulate Windows
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test on Windows")])

        # Verify the file was created correctly
        assert db.exists()
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test on Windows"
    finally:
        # Restore fchmod
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_still_sets_permissions_on_unix(tmp_path) -> None:
    """Issue #4834: On Unix, save() should still set restrictive permissions.

    When os.fchmod is available (Unix), it should be used to set permissions.
    This ensures we don't accidentally skip permission setting on Unix.
    """
    import os
    import stat

    # Skip this test if we're actually on Windows (fchmod not available)
    if not hasattr(os, "fchmod"):
        pytest.skip("os.fchmod not available on this platform")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track if fchmod was called
    original_fchmod = os.fchmod
    fchmod_calls = []

    def tracking_fchmod(fd, mode):
        fchmod_calls.append((fd, mode))
        return original_fchmod(fd, mode)

    with patch("flywheel.storage.os.fchmod", tracking_fchmod):
        storage.save([Todo(id=1, text="test")])

    # Verify fchmod was called with correct permissions
    assert len(fchmod_calls) == 1, "fchmod should be called exactly once"
    assert fchmod_calls[0][1] == stat.S_IRUSR | stat.S_IWUSR, (
        f"Permissions should be 0o600, got {oct(fchmod_calls[0][1])}"
    )


def test_save_works_when_fchmod_missing_from_os_module(tmp_path) -> None:
    """Issue #4834: save() should handle os module without fchmod attribute.

    Tests the specific case where hasattr(os, 'fchmod') returns False.
    """
    import os

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save the original fchmod if it exists
    original_fchmod = getattr(os, "fchmod", None)

    # Remove fchmod from os module
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="Windows compatibility test")])

        # Verify the file was created correctly
        assert db.exists()
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "Windows compatibility test"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod
