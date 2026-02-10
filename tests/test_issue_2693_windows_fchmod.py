"""Regression tests for issue #2693: os.fchmod() is not available on Windows.

Issue: os.fchmod() is Unix-only and causes AttributeError on Windows platforms.

The fix should:
1. Check if os.fchmod is available before using it
2. Provide a Windows fallback (either skip or use os.chmod after closing)
3. Maintain restrictive permissions (0o600) on Unix

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path) -> None:
    """Issue #2693: TodoStorage.save() should work on Windows (no os.fchmod).

    On Windows, os.fchmod() doesn't exist. This test simulates that
    environment by deleting the attribute and verifies that save()
    still works without raising AttributeError.

    Before fix: AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() completes successfully on Windows-like environments
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows environment where os.fchmod doesn't exist
    original_fchmod = getattr(os, 'fchmod', None)

    # Delete fchmod to simulate Windows
    if hasattr(os, 'fchmod'):
        delattr(os, 'fchmod')

    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test todo")])

        # Verify the file was actually saved
        assert db.exists(), "Database file should exist after save"

        # Verify content is correct
        todos = storage.load()
        assert len(todos) == 1
        assert todos[0].text == "test todo"

    finally:
        # Restore fchmod for other tests
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_sets_restrictive_permissions_on_unix(tmp_path) -> None:
    """Issue #2693: On Unix systems, temp files should still have 0o600 permissions.

    This verifies that the fix maintains security on Unix platforms
    while providing Windows compatibility.
    """
    import tempfile as tempfile_module

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    permissions_seen = []

    original_mkstemp = tempfile_module.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        # Track permissions of created temp files
        if hasattr(os, 'stat'):
            file_stat = os.stat(path)
            file_mode = stat.S_IMODE(file_stat.st_mode)
            permissions_seen.append((path, file_mode))
        return fd, path

    import tempfile
    original = tempfile.mkstemp
    tempfile.mkstemp = tracking_mkstemp

    try:
        storage.save([Todo(id=1, text="test")])
    finally:
        tempfile.mkstemp = original

    # Only verify permissions on Unix (where fchmod exists)
    if hasattr(os, 'fchmod'):
        assert len(permissions_seen) > 0, "No temp files were created"

        for path, mode in permissions_seen:
            # The mode should be EXACTLY 0o600 (rw-------)
            assert mode == 0o600, (
                f"Temp file has incorrect permissions: {oct(mode)} "
                f"(expected 0o600, got 0o{mode:o}). "
                f"File was: {path}"
            )


def test_save_without_fchmod_no_crash(tmp_path) -> None:
    """Issue #2693: Verify save() gracefully handles missing os.fchmod.

    This uses mock to delete the fchmod attribute at runtime,
    simulating a Windows environment.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Store original fchmod
    original_fchmod = getattr(os, 'fchmod', None)

    try:
        # Actually delete the attribute to simulate Windows environment
        if hasattr(os, 'fchmod'):
            delattr(os, 'fchmod')

        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="another test")])
    except AttributeError as e:
        if 'fchmod' in str(e):
            raise AssertionError(
                f"save() should not crash on missing os.fchmod. Got: {e}"
            ) from e
        # Re-raise if it's a different AttributeError
        raise
    finally:
        # Restore fchmod for other tests
        if original_fchmod is not None:
            os.fchmod = original_fchmod

    # Verify the file was saved even without fchmod
    assert db.exists(), "Database file should exist after save without fchmod"
    todos = storage.load()
    assert len(todos) == 1
