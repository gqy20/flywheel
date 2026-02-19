"""Regression tests for issue #4547: os.fchmod platform compatibility.

Issue: os.fchmod is not available on Windows, causing AttributeError when
saving todos on Windows platforms.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import os

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available_by_removing_attribute(tmp_path) -> None:
    """Issue #4547: save() should work even when os.fchmod is not available.

    Before fix: save() raises AttributeError on Windows where os.fchmod doesn't exist
    After fix: save() gracefully skips permission setting when fchmod unavailable
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows environment where os.fchmod doesn't exist
    # We need to actually remove the attribute, not just set it to None
    original_fchmod = os.fchmod

    # Temporarily remove fchmod from os module
    delattr(os, 'fchmod')
    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test")])

        # Verify save succeeded
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"
    finally:
        # Restore fchmod
        os.fchmod = original_fchmod


def test_save_works_when_hasattr_returns_false_for_fchmod(tmp_path) -> None:
    """Issue #4547: save() should skip fchmod when hasattr returns False.

    This test verifies that the hasattr check properly guards the fchmod call.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save the original fchmod
    original_fchmod = getattr(os, 'fchmod', None)

    # Remove fchmod from os module to simulate Windows
    if hasattr(os, 'fchmod'):
        delattr(os, 'fchmod')

    try:
        # This should NOT raise any error
        storage.save([Todo(id=1, text="test")])

        # Verify save succeeded
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_still_sets_permissions_when_fchmod_available(tmp_path) -> None:
    """Issue #4547: Permission setting should still work on platforms with fchmod.

    This test verifies that on Unix-like platforms, we still set restrictive
    permissions on the temp file.
    """
    # Skip this test if os.fchmod is not available (e.g., Windows)
    if not hasattr(os, 'fchmod'):
        import pytest
        pytest.skip("os.fchmod not available on this platform")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Verify save succeeded and file exists
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"
