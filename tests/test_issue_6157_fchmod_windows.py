"""Regression tests for issue #6157: os.fchmod is Unix-only.

Issue: os.fchmod raises AttributeError on Windows platforms because it's
a Unix-only function. The code should gracefully handle this by either
skipping the permission setting on Windows or using a cross-platform
alternative.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path) -> None:
    """Issue #6157: save() should not raise AttributeError when os.fchmod is missing.

    This simulates the Windows environment where os.fchmod does not exist.
    Before fix: Raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() completes successfully (permissions skipped on Windows)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Store original fchmod for restoration
    original_fchmod = getattr(os, "fchmod", None)

    try:
        # Remove fchmod from os module to simulate Windows
        if hasattr(os, "fchmod"):
            delattr(os, "fchmod")

        # This should NOT raise AttributeError
        storage.save(todos)

        # Verify the file was saved correctly
        assert db.exists()
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_works_on_actual_windows_or_without_fchmod(tmp_path, monkeypatch) -> None:
    """Issue #6157: save() should work when os.fchmod doesn't exist.

    Uses monkeypatch to properly remove the attribute (works better than delattr).
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Check if fchmod exists
    has_fchmod = hasattr(os, "fchmod")

    if has_fchmod:
        # On Unix, simulate Windows by removing fchmod
        original_fchmod = os.fchmod
        monkeypatch.delattr(os, "fchmod")

        # This should NOT raise AttributeError
        storage.save(todos)

        # Restore for the assertion below
        monkeypatch.setattr(os, "fchmod", original_fchmod, raising=False)
    else:
        # On actual Windows, just verify save works
        storage.save(todos)

    # Verify the file was saved correctly
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"
