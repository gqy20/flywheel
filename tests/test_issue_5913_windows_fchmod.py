"""Regression tests for issue #5913: os.fchmod is Unix-only, causing AttributeError on Windows.

Issue: os.fchmod is not available on Windows, causing AttributeError when
TodoStorage.save() is called on Windows platforms.

This test FAILS before the fix (on Windows or when simulating Windows)
and PASSES after the fix.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_unavailable(tmp_path: Path) -> None:
    """Issue #5913: TodoStorage.save() should work when os.fchmod is unavailable.

    This simulates the Windows environment where os.fchmod doesn't exist.
    Before fix: Raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: Saves successfully with a fallback mechanism.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows environment by hiding fchmod
    original_fchmod = getattr(os, "fchmod", None)

    # Create a mock os module without fchmod
    if original_fchmod is not None:
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test todo on Windows")])

        # Verify the save actually worked
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo on Windows"
    finally:
        # Restore fchmod if it was originally available
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_uses_fchmod_on_unix(tmp_path: Path) -> None:
    """Issue #5913: On Unix, TodoStorage.save() should still use os.fchmod.

    This ensures the fix doesn't remove the security benefit on Unix platforms.
    """
    # Skip this test if fchmod is not available (i.e., we're on Windows)
    if not hasattr(os, "fchmod"):
        pytest.skip("os.fchmod not available on this platform")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track if fchmod was called
    fchmod_calls = []
    original_fchmod = os.fchmod

    def tracking_fchmod(fd, mode):
        fchmod_calls.append((fd, mode))
        return original_fchmod(fd, mode)

    with patch.object(os, "fchmod", tracking_fchmod):
        storage.save([Todo(id=1, text="test")])

    # Verify fchmod was called with correct permissions
    assert len(fchmod_calls) == 1, "fchmod should be called exactly once"
    assert fchmod_calls[0][1] == 0o600, f"fchmod should set 0o600, got {oct(fchmod_calls[0][1])}"


def test_save_works_on_real_windows(tmp_path: Path) -> None:
    """Issue #5913: Integration test - save() should work on actual Windows.

    This test passes on any platform if the fix is correct.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # This should work regardless of platform
    storage.save([Todo(id=1, text="cross-platform todo")])

    # Verify the save worked
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "cross-platform todo"

    # Verify file exists and has valid content
    assert db.exists()
    content = db.read_text(encoding="utf-8")
    assert "cross-platform todo" in content
