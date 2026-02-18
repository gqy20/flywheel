"""Regression tests for issue #4228: os.fchmod is Unix-only.

Issue: os.fchmod raises AttributeError on Windows, causing save() to fail.

The save() method should handle Windows gracefully by skipping the Unix-only
fchmod call. Python's tempfile.mkstemp already creates files with 0600
permissions by default on all platforms, so this is acceptable.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_handles_missing_fchmod_gracefully(tmp_path) -> None:
    """Issue #4228: save() should not crash when os.fchmod is unavailable.

    Simulates Windows environment by temporarily removing os.fchmod.
    The save() function should gracefully skip the fchmod call and succeed.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Save original fchmod and remove it to simulate Windows
    original_fchmod = getattr(os, "fchmod", None)

    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT crash even without fchmod
        storage.save(todos)
    finally:
        # Restore fchmod if it was there originally
        if original_fchmod is not None:
            os.fchmod = original_fchmod

    # Verify the file was saved correctly
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_works_when_fchmod_attribute_does_not_exist(tmp_path) -> None:
    """Issue #4228: save() should work when os.fchmod doesn't exist at all.

    Tests the hasattr check approach by making fchmod completely unavailable.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="windows test"), Todo(id=2, text="another todo")]

    # Remove fchmod from os module temporarily
    original_fchmod = getattr(os, "fchmod", None)

    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT crash even without fchmod
        storage.save(todos)

        # Verify the file was saved correctly
        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].text == "windows test"
        assert loaded[1].text == "another todo"
    finally:
        # Restore fchmod if it was there originally
        if original_fchmod is not None:
            os.fchmod = original_fchmod
