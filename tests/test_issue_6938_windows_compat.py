"""Regression tests for issue #6938: os.fchmod() is Unix-only.

Issue: os.fchmod() is Unix-only and will raise AttributeError on Windows,
causing save() to fail with a confusing error message.

The fix should make save() work on both Unix and Windows platforms.
On Windows, tempfile.mkstemp already creates files with restricted permissions,
so the security intent is maintained even without fchmod.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_on_simulated_windows_platform(tmp_path) -> None:
    """Issue #6938: Verify save() works when fchmod is not available.

    This tests the scenario where hasattr(os, 'fchmod') returns False,
    simulating Windows platform behavior where os.fchmod doesn't exist.

    Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() completes successfully, file contains valid data
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Store original fchmod
    original_fchmod = os.fchmod

    # Remove fchmod to simulate Windows
    delattr(os, "fchmod")

    try:
        # This should work without attempting to call fchmod
        storage.save([Todo(id=1, text="test on simulated Windows")])

        # Verify the file was saved correctly
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test on simulated Windows"
    finally:
        # Restore fchmod for other tests
        os.fchmod = original_fchmod


def test_save_preserves_data_integrity_on_simulated_windows(tmp_path) -> None:
    """Issue #6938: Verify data integrity is preserved on Windows (no fchmod).

    This test ensures that skipping fchmod on Windows doesn't corrupt
    or lose any data.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first task", done=False),
        Todo(id=2, text="second task", done=True),
        Todo(id=3, text="unicode: 你好世界", done=False),
    ]

    # Store original fchmod
    original_fchmod = os.fchmod

    # Remove fchmod to simulate Windows
    delattr(os, "fchmod")

    try:
        storage.save(todos)

        # Verify all data is preserved correctly
        loaded = storage.load()
        assert len(loaded) == 3
        assert loaded[0].text == "first task"
        assert loaded[0].done is False
        assert loaded[1].text == "second task"
        assert loaded[1].done is True
        assert loaded[2].text == "unicode: 你好世界"
        assert loaded[2].done is False
    finally:
        # Restore fchmod for other tests
        os.fchmod = original_fchmod


def test_save_works_on_unix_with_fchmod(tmp_path) -> None:
    """Issue #6938: Verify save() still works on Unix with fchmod available.

    This test ensures the fix doesn't break the existing Unix behavior.
    On Unix, os.fchmod should still be called to set 0o600 permissions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Verify we're on a platform with fchmod (Unix)
    assert hasattr(os, "fchmod"), "This test should run on Unix platforms"

    # This should work with fchmod available
    storage.save([Todo(id=1, text="test on Unix")])

    # Verify the file was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test on Unix"
