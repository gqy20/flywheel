"""Regression tests for issue #4971: os.fchmod not available on Windows.

Issue: os.fchmod is a POSIX-specific function that doesn't exist on Windows.
Calling it on Windows raises AttributeError.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import os

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path) -> None:
    """Issue #4971: save() should work on platforms without os.fchmod.

    Before fix: AttributeError: module 'os' has no attribute 'fchmod'
    After fix: Should gracefully skip fchmod on unsupported platforms
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows where os.fchmod doesn't exist
    # We need to patch hasattr to return False for os.fchmod
    import builtins

    original_hasattr = builtins.hasattr

    def mock_hasattr(obj, name):
        if obj is os and name == "fchmod":
            return False
        return original_hasattr(obj, name)

    builtins.hasattr = mock_hasattr

    try:
        todos = [Todo(id=1, text="test on windows")]
        # This should NOT raise AttributeError after the fix
        storage.save(todos)
    finally:
        builtins.hasattr = original_hasattr

    # Verify save succeeded
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test on windows"


def test_save_handles_missing_fchmod_gracefully(tmp_path) -> None:
    """Issue #4971: Verify graceful handling when fchmod attribute is missing.

    This test ensures that even if os.fchmod is completely absent from the os
    module (as on Windows), the code doesn't crash.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Store the original function if it exists
    original_fchmod = getattr(os, "fchmod", None)

    # Remove fchmod from os module to simulate Windows
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        todos = [Todo(id=1, text="cross-platform save")]
        # This should NOT raise AttributeError after the fix
        storage.save(todos)

        # Verify save succeeded
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "cross-platform save"
    finally:
        # Restore fchmod if it was present
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_temp_file_permissions_on_posix_systems(tmp_path) -> None:
    """Issue #4971: Verify permissions are still set on POSIX systems.

    This test ensures that on POSIX systems where os.fchmod is available,
    the restrictive permissions are still properly set.
    """
    import stat

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="secure todo")]

    # Only run permission check if fchmod is available (POSIX systems)
    if hasattr(os, "fchmod"):
        storage.save(todos)

        # Check that the saved file has restrictive permissions
        # Note: On some systems, the exact permissions may vary due to umask
        file_mode = stat.S_IMODE(db.stat().st_mode)

        # The file should have owner-only permissions (0o600 or more restrictive)
        # Group and others should have no permissions
        assert file_mode & 0o077 == 0, f"File has overly permissive mode: {oct(file_mode)}"
    else:
        # On non-POSIX systems, just verify save works
        storage.save(todos)

    # Verify content is correct
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "secure todo"


def test_import_storage_works_without_fchmod(tmp_path) -> None:
    """Issue #4971: Module should be importable even without fchmod.

    This is a sanity check that the storage module can be imported
    on platforms without os.fchmod support.
    """
    # The import should work without raising any errors
    # This test passes if we got here without import errors
    from flywheel.storage import TodoStorage

    storage = TodoStorage(str(tmp_path / "test.json"))
    storage.save([Todo(id=1, text="import test")])
    loaded = storage.load()
    assert len(loaded) == 1
