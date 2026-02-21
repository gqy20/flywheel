"""Regression tests for issue #4971: os.fchmod is not available on Windows.

Issue: os.fchmod is a POSIX-specific function that raises AttributeError on Windows.
The storage.py module should handle this gracefully by checking for availability.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path) -> None:
    """Issue #4971: save() should work even when os.fchmod is unavailable.

    This simulates Windows behavior where os.fchmod doesn't exist.
    Before fix: AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() succeeds without calling fchmod
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by removing fchmod temporarily
    original_fchmod = getattr(os, "fchmod", None)

    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError
        todos = [Todo(id=1, text="test on Windows")]
        storage.save(todos)

        # Verify save succeeded
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test on Windows"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_still_sets_restrictive_permissions_on_posix(tmp_path) -> None:
    """Issue #4971: On POSIX systems, save() should still set 0o600 permissions.

    This test verifies that the fix doesn't break the security feature on
    systems where fchmod is available.
    """
    # Skip test on Windows (where fchmod doesn't exist)
    if not hasattr(os, "fchmod"):
        return

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track permissions of created temp files
    permissions_seen = []

    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        # Check permissions immediately after creation
        file_stat = os.stat(path)
        file_mode = stat.S_IMODE(file_stat.st_mode)
        permissions_seen.append(file_mode)
        return fd, path

    import tempfile
    original = tempfile.mkstemp
    tempfile.mkstemp = tracking_mkstemp

    try:
        storage.save([Todo(id=1, text="test")])
    finally:
        tempfile.mkstemp = original

    # Verify temp file was created with restrictive permissions
    assert len(permissions_seen) > 0, "No temp files were created"
    for mode in permissions_seen:
        # Check that group and others have no permissions
        assert mode & 0o077 == 0, f"Temp file has overly permissive mode: {oct(mode)}"
        # Owner should have read+write at minimum
        assert mode & stat.S_IRUSR != 0, f"Temp file lacks owner read: {oct(mode)}"
        assert mode & stat.S_IWUSR != 0, f"Temp file lacks owner write: {oct(mode)}"


def test_import_storage_succeeds_on_simulated_windows(tmp_path) -> None:
    """Issue #4971: Importing storage module should work even without fchmod.

    This test verifies that the module-level checks don't cause import errors.
    """
    # Simulate Windows environment
    original_fchmod = getattr(os, "fchmod", None)

    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # Re-import the module to trigger any module-level code
        import importlib
        import flywheel.storage

        importlib.reload(flywheel.storage)

        # If we get here without AttributeError, the fix works
        assert True
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_with_mock_missing_fchmod_attribute(tmp_path, monkeypatch) -> None:
    """Issue #4971: Verify save() handles missing fchmod gracefully using monkeypatch.

    This is an alternative test using pytest's monkeypatch fixture.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Use monkeypatch to temporarily remove fchmod
    if hasattr(os, "fchmod"):
        monkeypatch.delattr(os, "fchmod")

    # This should NOT raise AttributeError
    todos = [Todo(id=1, text="test with monkeypatch")]
    storage.save(todos)

    # Verify save succeeded
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test with monkeypatch"
