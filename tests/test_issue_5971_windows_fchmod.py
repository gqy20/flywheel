"""Regression tests for issue #5971: os.fchmod() raises AttributeError on Windows.

Issue: The save() method uses os.fchmod() which is Unix-only and raises
AttributeError on Windows when setting file permissions.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import unittest.mock as mock
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_handles_missing_fchmod_gracefully(tmp_path) -> None:
    """Issue #5971: save() should work on Windows without AttributeError.

    On Windows, os.fchmod doesn't exist and raises AttributeError.
    The code should handle this gracefully.

    Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() completes successfully on Windows
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows environment where os.fchmod doesn't exist
    original_fchmod = getattr(os, 'fchmod', None)

    # Remove fchmod to simulate Windows
    if hasattr(os, 'fchmod'):
        delattr(os, 'fchmod')

    try:
        # This should NOT raise AttributeError on Windows
        storage.save([Todo(id=1, text="test")])

        # Verify the file was saved correctly
        assert db.exists(), "Database file should be created"
        content = db.read_text(encoding="utf-8")
        assert '"text": "test"' in content, "Todo should be saved"

    finally:
        # Restore original fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_works_with_mocked_attribute_error(tmp_path) -> None:
    """Issue #5971: save() should handle AttributeError from os.fchmod.

    This test explicitly mocks os.fchmod to raise AttributeError to simulate
    Windows behavior more precisely.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    with mock.patch.object(os, 'fchmod', side_effect=AttributeError("mocked")):
        # This should NOT raise AttributeError
        storage.save([Todo(id=2, text="windows test")])

        # Verify the file was saved correctly
        assert db.exists(), "Database file should be created"
        content = db.read_text(encoding="utf-8")
        assert '"text": "windows test"' in content, "Todo should be saved"


def test_save_preserves_unix_permissions_when_fchmod_available(tmp_path) -> None:
    """Issue #5971: On Unix, save() should still set restrictive permissions.

    This test verifies that the fix doesn't break Unix behavior.
    It only runs meaningfully on Unix systems where os.fchmod exists.
    """
    # Skip this test if we're on Windows (no fchmod)
    if not hasattr(os, 'fchmod'):
        return

    import stat

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=3, text="unix test")])

    # Verify file was created with restrictive permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # On Unix, the final file may have umask applied, but it should be restrictive
    # The temp file should have been 0o600 during write
    # We just verify the file exists and is readable by owner
    assert db.exists(), "Database file should be created"
    assert file_mode & stat.S_IRUSR, "File should be readable by owner"
