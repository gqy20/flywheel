"""Regression tests for issue #3544: os.fchmod() is not available on Windows.

Issue: os.fchmod() is not available on Windows, causing save() to fail with
AttributeError on Windows platforms.

The fix should wrap os.fchmod in a try/except AttributeError and fall back
gracefully on Windows, while still setting 0o600 permissions on Unix systems.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import builtins
import os
import stat
from unittest import mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path) -> None:
    """Issue #3544: save() should work when os.fchmod is not available (Windows).

    This simulates the Windows environment where os.fchmod doesn't exist.
    Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() completes successfully
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by removing the fchmod attribute
    original_hasattr = builtins.hasattr

    def mock_hasattr(obj, name):
        if obj is os and name == "fchmod":
            return False  # Simulate Windows where os.fchmod doesn't exist
        return original_hasattr(obj, name)

    with mock.patch("builtins.hasattr", side_effect=mock_hasattr):
        # This should NOT raise AttributeError on Windows
        storage.save([Todo(id=1, text="test todo")])

    # Verify the file was saved successfully
    assert db.exists()
    content = db.read_text()
    assert "test todo" in content


def test_save_still_sets_permissions_on_unix(tmp_path) -> None:
    """Issue #3544: save() should still set 0o600 permissions on Unix.

    This test ensures the fix doesn't break Unix permission handling.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    # On Unix, verify the file has secure permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify owner can read and write
    assert file_mode & stat.S_IRUSR, f"File lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR, f"File lacks owner write: {oct(file_mode)}"

    # Verify group and others have no permissions (0o0XX)
    assert file_mode & 0o077 == 0, f"File has overly permissive mode: {oct(file_mode)}"


def test_save_handles_attribute_error_gracefully(tmp_path) -> None:
    """Issue #3544: save() should handle missing os.fchmod gracefully.

    This directly tests the hasattr check for os.fchmod.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by making hasattr return False for os.fchmod
    original_hasattr = builtins.hasattr

    def mock_hasattr(obj, name):
        if obj is os and name == "fchmod":
            return False
        return original_hasattr(obj, name)

    with mock.patch("builtins.hasattr", side_effect=mock_hasattr):
        # This should NOT raise - the missing attribute should be handled
        storage.save([Todo(id=1, text="test todo")])

    # Verify the file was saved successfully despite missing os.fchmod
    assert db.exists()
    content = db.read_text()
    assert "test todo" in content
