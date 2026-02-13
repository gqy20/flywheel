"""Regression tests for issue #3014: os.fchmod not available on Windows.

Issue: os.fchmod is a Unix-only function and raises AttributeError on Windows.
The code in storage.py:112 uses os.fchmod directly without checking availability.

The fix should:
1. Check if os.fchmod exists before using it (hasattr check)
2. Fall back to os.chmod on platforms where fchmod is unavailable
3. Still set restrictive 0o600 permissions when possible

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from unittest import mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_does_not_raise_attributeerror_when_fchmod_unavailable(tmp_path) -> None:
    """Issue #3014: save() should not raise AttributeError on Windows.

    On Windows, os.fchmod does not exist. The code should handle this gracefully
    by checking availability and falling back to os.chmod.

    Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() completes successfully, using os.chmod as fallback
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save original fchmod for restoration
    original_fchmod = os.fchmod

    # Simulate Windows environment where os.fchmod doesn't exist
    # We must delete the attribute (not set to None) for hasattr to return False
    delattr(os, 'fchmod')

    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test todo")])
    finally:
        # Restore fchmod for other tests
        os.fchmod = original_fchmod

    # Verify data was saved correctly
    assert db.exists()
    saved_todos = storage.load()
    assert len(saved_todos) == 1
    assert saved_todos[0].text == "test todo"


def test_save_uses_chmod_fallback_when_fchmod_unavailable(tmp_path) -> None:
    """Issue #3014: save() should use os.chmod when os.fchmod is unavailable.

    This verifies that the fallback path actually calls os.chmod to set
    restrictive permissions on the temp file.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    chmod_calls = []

    # Track calls to os.chmod
    original_chmod = os.chmod
    original_fchmod = os.fchmod

    def tracking_chmod(path, mode, *args, **kwargs):
        chmod_calls.append((path, mode))
        return original_chmod(path, mode, *args, **kwargs)

    # Simulate Windows environment by deleting fchmod attribute
    delattr(os, 'fchmod')

    try:
        with mock.patch.object(os, 'chmod', tracking_chmod):
            storage.save([Todo(id=1, text="test todo")])
    finally:
        # Restore fchmod for other tests
        os.fchmod = original_fchmod

    # Verify chmod was called with restrictive permissions (0o600)
    assert len(chmod_calls) >= 1, "os.chmod should have been called as fallback"
    for _path, mode in chmod_calls:
        assert mode == 0o600, f"Expected permissions 0o600, got {oct(mode)}"


def test_save_works_normally_when_fchmod_available(tmp_path) -> None:
    """Issue #3014: Existing Unix behavior should not be broken.

    On Unix systems where os.fchmod exists, the existing behavior should
    continue to work correctly.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Don't mock fchmod - test normal Unix behavior
    storage.save([Todo(id=1, text="test todo")])

    # Verify data was saved correctly
    assert db.exists()
    saved_todos = storage.load()
    assert len(saved_todos) == 1
    assert saved_todos[0].text == "test todo"
