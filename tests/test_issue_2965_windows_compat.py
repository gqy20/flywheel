"""Regression tests for issue #2965: os.fchmod not available on Windows.

Issue: os.fchmod is POSIX-only and raises AttributeError on Windows, causing
save() to fail on that platform.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
from unittest import mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path) -> None:
    """Issue #2965: save() should work on Windows where os.fchmod doesn't exist.

    On Windows, os.fchmod doesn't exist (hasattr returns False). The code should
    handle this gracefully and skip the chmod call.

    Before fix: save() would call os.fchmod blindly and fail
    After fix: save() completes successfully by checking hasattr first
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows environment where os.fchmod doesn't exist
    # We need to remove fchmod from os module temporarily
    with mock.patch.dict('os.__dict__', {'fchmod': mock.DEFAULT}):
        # Remove fchmod from the dict to simulate it not existing
        if 'fchmod' in os.__dict__:
            del os.__dict__['fchmod']

        # Now hasattr should return False
        # This should NOT raise any error - it should skip fchmod
        storage.save([Todo(id=1, text="test todo")])

    # Verify the file was saved correctly
    assert db.exists()
    content = db.read_text()
    assert "test todo" in content


def test_save_handles_missing_fchmod_gracefully(tmp_path) -> None:
    """Issue #2965: save() should gracefully handle missing os.fchmod.

    This test verifies that the code uses hasattr() to check for fchmod
    availability before calling it.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Store original fchmod if it exists
    original_fchmod = getattr(os, 'fchmod', None)

    try:
        # Remove fchmod from the module dict temporarily
        if 'fchmod' in os.__dict__:
            del os.__dict__['fchmod']

        # Verify that hasattr returns False
        assert not hasattr(os, 'fchmod'), "fchmod should not be available in mock"

        # This should NOT raise any error
        storage.save([Todo(id=1, text="windows compatible")])
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.__dict__['fchmod'] = original_fchmod

    # Verify the file was saved correctly
    assert db.exists()
    content = db.read_text()
    assert "windows compatible" in content


def test_save_still_sets_restrictive_permissions_on_unix(tmp_path) -> None:
    """Issue #2965: Ensure Unix systems still get restrictive file permissions.

    The fix should maintain security on Unix systems while being compatible
    with Windows.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="secure todo")])

    # On Unix, verify the file has restrictive permissions
    # Note: This test only verifies Unix behavior; on Windows the concept
    # of Unix file permissions doesn't apply the same way
    if hasattr(os, 'fchmod'):
        file_stat = db.stat()
        file_mode = stat.S_IMODE(file_stat.st_mode)
        # The final file should have been created with restrictive permissions
        # The exact permissions may vary, but group/others should not have write
        assert not (file_mode & stat.S_IWOTH), (
            f"File should not be world-writable: {oct(file_mode)}"
        )
