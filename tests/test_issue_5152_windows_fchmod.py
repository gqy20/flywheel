"""Regression test for issue #5152: os.fchmod not available on Windows.

This test verifies that TodoStorage.save() works on Windows where
os.fchmod is not available, falling back gracefully without raising
AttributeError.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_handles_missing_fchmod_gracefully(tmp_path) -> None:
    """Test that save() handles missing os.fchmod (Windows) without AttributeError.

    On Windows, os.fchmod does not exist, causing AttributeError.
    The fix should catch this and continue without failing.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Save original fchmod if it exists
    original_fchmod = getattr(os, 'fchmod', None)

    # Delete the attribute to simulate Windows (os.fchmod doesn't exist)
    if hasattr(os, 'fchmod'):
        delattr(os, 'fchmod')

    try:
        # This should NOT raise AttributeError
        storage.save(todos)
    finally:
        # Restore original fchmod
        if original_fchmod is not None:
            os.fchmod = original_fchmod

    # Verify the file was still saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_with_fchmod_attribute_error(tmp_path) -> None:
    """Test that save() handles AttributeError from os.fchmod gracefully.

    Even if os.fchmod exists but raises AttributeError (edge case),
    save() should still work.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Create a mock that raises AttributeError when called
    def mock_fchmod_raises(*args, **kwargs):
        raise AttributeError("fchmod not available")

    with patch.object(os, 'fchmod', mock_fchmod_raises):
        # This should NOT raise AttributeError - it should be caught and handled
        storage.save(todos)

    # Verify the file was still saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_still_sets_permissions_on_unix(tmp_path, monkeypatch) -> None:
    """Test that on Unix systems, permissions are still set correctly.

    This test verifies that the fix doesn't break the security feature
    of setting 0o600 permissions on Unix systems.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Track if fchmod was called with correct permissions
    fchmod_calls = []

    def mock_fchmod(fd, mode):
        fchmod_calls.append((fd, mode))

    # Only run this test if we're on a system that has fchmod
    if hasattr(os, 'fchmod'):
        with patch.object(os, 'fchmod', mock_fchmod):
            storage.save(todos)

        # Verify fchmod was called with 0o600 permissions
        assert len(fchmod_calls) == 1
        # S_IRUSR | S_IWUSR = 0o600 = 0b110000000 = 0o600
        import stat
        assert fchmod_calls[0][1] == (stat.S_IRUSR | stat.S_IWUSR)
    else:
        # On Windows without fchmod, just verify save works
        storage.save(todos)

    # Verify the file was still saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"
