"""Regression tests for issue #2248: os.fchmod() is Unix-only and will crash on Windows.

Issue: Code calls os.fchmod() unconditionally without platform check.
This function doesn't exist on Windows, causing AttributeError.

The fix should check hasattr(os, 'fchmod') before calling it.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_without_fchmod(tmp_path) -> None:
    """Issue #2248: TodoStorage.save() should work even when os.fchmod is unavailable.

    On Windows, os.fchmod doesn't exist. The code should gracefully skip
    the chmod operation when the function is not available.

    Before fix: AttributeError: module 'os' has no attribute 'fchmod'
    After fix: Save succeeds even without os.fchmod
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Mock os.fchmod to not exist (simulating Windows)
    import os as os_module

    original_fchmod = getattr(os_module, "fchmod", None)

    # Delete fchmod to simulate Windows environment
    if hasattr(os_module, "fchmod"):
        delattr(os_module, "fchmod")

    try:
        # This should NOT raise AttributeError
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        # Verify the save actually worked
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"

    finally:
        # Restore os.fchmod if it existed
        if original_fchmod is not None:
            os_module.fchmod = original_fchmod


def test_save_works_without_fchmod_multiple_todos(tmp_path) -> None:
    """Issue #2248: Verify save works without fchmod for multiple todos."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    import os as os_module

    original_fchmod = getattr(os_module, "fchmod", None)

    if hasattr(os_module, "fchmod"):
        delattr(os_module, "fchmod")

    try:
        todos = [
            Todo(id=1, text="first todo", done=False),
            Todo(id=2, text="second todo", done=True),
            Todo(id=3, text="third todo"),
        ]
        storage.save(todos)

        # Verify all todos were saved correctly
        loaded = storage.load()
        assert len(loaded) == 3
        assert loaded[0].text == "first todo"
        assert loaded[1].done is True
        assert loaded[2].text == "third todo"

    finally:
        if original_fchmod is not None:
            os_module.fchmod = original_fchmod
