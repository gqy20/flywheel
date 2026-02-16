"""Regression tests for issue #3748: os.fchmod not available on Windows.

Issue: os.fchmod is not available on Windows, causing save() to crash
with AttributeError when running on Windows platform.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_handles_missing_fchmod_gracefully(tmp_path) -> None:
    """Issue #3748: save() should handle missing os.fchmod on Windows.

    On Windows, os.fchmod does not exist and accessing it raises AttributeError.
    The save() method should gracefully handle this and continue without
    setting file permissions (Windows uses ACLs instead).

    Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() completes successfully on Windows
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows behavior where os.fchmod doesn't exist
    original_fchmod = getattr(sys.modules['os'], 'fchmod', None)

    # Remove fchmod from os module to simulate Windows
    if hasattr(sys.modules['os'], 'fchmod'):
        delattr(sys.modules['os'], 'fchmod')

    try:
        # This should NOT raise an exception
        storage.save([Todo(id=1, text="test todo")])

        # Verify the data was saved correctly
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        # Restore fchmod if it existed before
        if original_fchmod is not None:
            sys.modules['os'].fchmod = original_fchmod


def test_save_works_when_fchmod_patched_to_none(tmp_path) -> None:
    """Issue #3748: save() should handle os.fchmod being set to None.

    Some environments might have os.fchmod set to None instead of not existing.
    This tests that the hasattr check correctly handles this case.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Patch os.fchmod to None to simulate environments where it's explicitly disabled
    with patch('flywheel.storage.os.fchmod', None):
        # This should NOT raise an exception - hasattr will return False for None
        storage.save([Todo(id=1, text="test todo")])

    # Verify the data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_still_works_with_fchmod_on_unix(tmp_path) -> None:
    """Issue #3748: Ensure fix doesn't break Unix behavior.

    On Unix systems where os.fchmod exists, it should still be called
    and work as expected.
    """
    import os

    # Skip this test on Windows where fchmod doesn't exist
    if not hasattr(os, 'fchmod'):
        pytest.skip("os.fchmod not available on this platform")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track if fchmod was called
    fchmod_called = []
    original_fchmod = os.fchmod

    def tracking_fchmod(fd, mode):
        fchmod_called.append((fd, mode))
        return original_fchmod(fd, mode)

    with patch('flywheel.storage.os.fchmod', tracking_fchmod):
        storage.save([Todo(id=1, text="test todo")])

    # Verify fchmod was called with correct mode
    assert len(fchmod_called) == 1
    assert fchmod_called[0][1] == 0o600  # stat.S_IRUSR | stat.S_IWUSR

    # Verify the data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"
