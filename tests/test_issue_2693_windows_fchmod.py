"""Regression tests for issue #2693: os.fchmod() is not available on Windows.

Issue: os.fchmod() is Unix-only and causes AttributeError on Windows platforms.

The fix should:
1. Check if os.fchmod is available before using it
2. Gracefully handle Windows (where fchmod doesn't exist)
3. Still set restrictive permissions on Unix systems

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_raises_attribute_error(tmp_path) -> None:
    """Issue #2693: TodoStorage.save() should work even if os.fchmod raises AttributeError.

    On Windows, os.fchmod doesn't exist. The code should gracefully handle this
    case and still allow saving data.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Mock os.fchmod to raise AttributeError (simulating Windows access)
    def mock_fchmod(*args, **kwargs):
        raise AttributeError("module 'os' has no attribute 'fchmod'")

    with patch.object(os, "fchmod", side_effect=mock_fchmod):
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test on windows")])

    # Verify the file was actually saved
    assert db.exists(), "Database file should be created"
    content = db.read_text(encoding="utf-8")
    assert "test on windows" in content


def test_save_fchmod_none_handling(tmp_path) -> None:
    """Issue #2693: Verify graceful handling when os.fchmod is None.

    This simulates what getattr(os, "fchmod", None) returns on Windows.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Set fchmod to None (simulating Windows getattr behavior)
    with patch.object(os, "fchmod", None):
        # This should NOT raise AttributeError
        storage.save([Todo(id=2, text="another test")])

    # Verify the file was saved
    assert db.exists()
    content = db.read_text(encoding="utf-8")
    assert "another test" in content


def test_unix_still_sets_restrictive_permissions(tmp_path) -> None:
    """Issue #2693: On Unix systems with fchmod, restrictive permissions should still be set.

    This ensures the security fix from issue #2027 (0o600 permissions) is maintained
    for Unix systems.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    fchmod_calls = []

    original_fchmod = os.fchmod

    def tracking_fchmod(fd, mode):
        fchmod_calls.append((fd, mode))
        return original_fchmod(fd, mode)

    with patch.object(os, "fchmod", side_effect=tracking_fchmod):
        storage.save([Todo(id=3, text="unix permission test")])

    # Verify fchmod was called with restrictive permissions (on Unix systems)
    if hasattr(os, "fchmod"):
        assert len(fchmod_calls) > 0, "fchmod should have been called on Unix"
        for _fd, mode in fchmod_calls:
            assert mode == 0o600, (
                f"fchmod should set 0o600 permissions on Unix, got {oct(mode)}"
            )


def test_fchmod_not_called_when_none(tmp_path) -> None:
    """Issue #2693: When fchmod is None, it should not be called.

    This verifies the hasattr/getattr check in storage.py works correctly.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track if fchmod is called
    fchmod_called = []

    def mock_fchmod(*args, **kwargs):
        fchmod_called.append(True)
        raise RuntimeError("fchmod should not be called when None")

    # Set fchmod to None - it should not even attempt to call it
    with patch.object(os, "fchmod", None):
        storage.save([Todo(id=4, text="no fchmod call test")])

    assert len(fchmod_called) == 0, "fchmod should not be called when it's None"
    assert db.exists()


def test_save_works_on_both_platforms(tmp_path) -> None:
    """Issue #2693: save() should work on both Unix and Windows.

    This test verifies cross-platform compatibility.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    test_todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo"),
        Todo(id=3, text="third todo"),
    ]

    # Test with fchmod available (Unix simulation - current platform)
    storage.save(test_todos)
    assert db.exists()

    loaded = storage.load()
    assert len(loaded) == 3
    assert [t.text for t in loaded] == ["first todo", "second todo", "third todo"]

    # Test without fchmod (Windows simulation)
    with patch.object(os, "fchmod", None):
        storage.save(test_todos)
        assert db.exists()

    loaded = storage.load()
    assert len(loaded) == 3
