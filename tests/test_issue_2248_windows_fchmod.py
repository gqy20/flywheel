"""Regression tests for issue #2248: os.fchmod() is Unix-only and will crash on Windows.

Issue: Code calls os.fchmod() unconditionally on line 112 of storage.py.
This function doesn't exist on Windows and will raise AttributeError.

The fix should add a platform check before calling os.fchmod.
On Windows, rely on mkstemp's default 0o600 permissions.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_does_not_crash_on_windows_missing_fchmod(tmp_path) -> None:
    """Issue #2248: Should not crash when os.fchmod is not available (Windows).

    On Windows, os.fchmod doesn't exist and will raise AttributeError.
    The code should gracefully handle this and still work correctly.

    Before fix: Raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: Works correctly on both Unix and Windows
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo"), Todo(id=2, text="another task")]

    # Simulate Windows by deleting fchmod from os module entirely
    # This is the actual behavior on Windows - the attribute doesn't exist
    import os as os_module
    original_fchmod = getattr(os_module, "fchmod", None)

    # Remove fchmod to simulate Windows
    if hasattr(os_module, "fchmod"):
        delattr(os_module, "fchmod")

    try:
        # This should NOT raise AttributeError
        # The fix uses hasattr check, so fchmod won't be called on Windows
        storage.save(todos)
    finally:
        # Restore fchmod for other tests
        if original_fchmod is not None:
            os_module.fchmod = original_fchmod

    # Verify the file was saved correctly
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "test todo"
    assert loaded[1].text == "another task"

    # Verify the file exists and has valid content
    assert db.exists()
    assert db.read_text(encoding="utf-8")


def test_save_with_missing_fchmod_attribute(tmp_path) -> None:
    """Issue #2248: Alternative test - delete fchmod entirely from os module."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test"), Todo(id=2, text="test2", done=True)]

    # Simulate Windows by removing fchmod from os module entirely
    import os as os_module

    original_fchmod = os_module.fchmod
    delattr(os_module, "fchmod")

    try:
        # This should work even without os.fchmod
        storage.save(todos)

        # Verify data was saved correctly
        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].text == "test"
        assert loaded[1].done is True
    finally:
        # Restore fchmod for other tests
        os_module.fchmod = original_fchmod


def test_save_windows_simulation_with_hasattr_check(tmp_path) -> None:
    """Issue #2248: Test that hasattr check allows Windows to work."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="windows test")]

    # Use patch.object to simulate os module without fchmod
    # This tests the hasattr guard in the code
    with patch("flywheel.storage.os", spec=["replace", "fdopen", "unlink", "write"]):
        # The code's hasattr check will handle missing fchmod gracefully
        # We need to import the real os functions we still need
        import os as real_os

        with patch("flywheel.storage.os.replace", real_os.replace), \
             patch("flywheel.storage.os.fdopen", real_os.fdopen), \
             patch("flywheel.storage.os.unlink", real_os.unlink):
            # This should work because hasattr(os, 'fchmod') will return False
            storage.save(todos)

    # Verify save worked
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "windows test"


def test_unix_platform_still_uses_fchmod(tmp_path) -> None:
    """Issue #2248: On Unix platforms, fchmod should still be called.

    This ensures the fix doesn't break Unix security behavior.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="unix test")]

    # Track that fchmod was called on Unix
    fchmod_called = []
    original_fchmod = __import__("os").fchmod

    def tracking_fchmod(fd, mode):
        fchmod_called.append((fd, mode))
        return original_fchmod(fd, mode)

    with patch("flywheel.storage.os.fchmod", side_effect=tracking_fchmod):
        storage.save(todos)

    # On Unix (or when fchmod exists), it should be called
    # If we're on a system with fchmod, verify it was used
    import os as os_module
    if hasattr(os_module, "fchmod"):
        assert len(fchmod_called) > 0, "fchmod should be called on Unix platforms"
        # Verify the mode is 0o600 (rw-------)
        _, mode = fchmod_called[0]
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"
