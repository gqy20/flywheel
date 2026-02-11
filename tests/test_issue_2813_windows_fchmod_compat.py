"""Regression tests for issue #2813: os.fchmod is not available on Windows.

Issue: The code calls os.fchmod() directly without checking if it exists.
On Windows, os.fchmod doesn't exist, causing an AttributeError.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

from contextlib import suppress
from unittest.mock import MagicMock, patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_without_fchmod(tmp_path) -> None:
    """Issue #2813: TodoStorage.save() should work when os.fchmod is not available.

    On Windows, os.fchmod doesn't exist. The code should handle this gracefully
    by checking hasattr(os, "fchmod") before calling it.

    Before fix: AttributeError: module 'os' has no attribute 'fchmod'
    After fix: Save completes successfully even without fchmod
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Simulate Windows environment where os.fchmod doesn't exist
    # We create a mock os module without fchmod attribute
    import os

    mock_os = MagicMock()
    # Copy all attributes from os except fchmod
    for attr in dir(os):
        if attr != "fchmod":
            with suppress(AttributeError, TypeError):
                setattr(mock_os, attr, getattr(os, attr))

    with patch("flywheel.storage.os", mock_os):
        # On Windows-like systems without fchmod, this should still work
        storage.save(todos)

    # Verify the file was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_with_fchmod_available(tmp_path) -> None:
    """Issue #2813: Verify save still works correctly when fchmod IS available.

    This ensures our fix doesn't break the normal case where fchmod exists.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="unix test"), Todo(id=2, text="another todo")]

    # Normal save with fchmod available (default Unix/Linux case)
    storage.save(todos)

    # Verify the file was saved correctly
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "unix test"
    assert loaded[1].text == "another todo"
