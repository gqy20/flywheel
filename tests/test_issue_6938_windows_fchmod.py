"""Regression tests for issue #6938: os.fchmod() is Unix-only.

Issue: os.fchmod() does not exist on Windows and raises AttributeError,
causing save() to fail with a confusing error message.

The fix should gracefully handle the absence of os.fchmod on Windows
while maintaining 0o600 permissions on Unix systems.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_succeeds_when_fchmod_not_available(tmp_path: Path) -> None:
    """Issue #6938: save() should succeed on Windows where os.fchmod doesn't exist.

    This simulates Windows behavior by removing os.fchmod temporarily.
    The save operation should still complete successfully because:
    1. tempfile.mkstemp already creates files with secure permissions
    2. On Windows, file permissions work differently (ACLs, not Unix modes)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test task")]

    # Simulate Windows by removing fchmod from os module
    original_fchmod = getattr(os, "fchmod", None)
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError after the fix
        storage.save(todos)

        # Verify the file was written correctly
        assert db.exists()
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test task"
    finally:
        # Restore fchmod if it existed before
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_works_without_fchmod_attribute(tmp_path: Path) -> None:
    """Issue #6938: save() should work when os has no fchmod attribute.

    This is a more direct test that removes fchmod from os temporarily,
    simulating the actual Windows environment more closely.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2")]

    original_fchmod = getattr(os, "fchmod", None)

    # Temporarily remove fchmod from os module
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT crash
        storage.save(todos)

        # Verify the file was written correctly
        assert db.exists()
        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].text == "task 1"
        assert loaded[1].text == "task 2"
    finally:
        # Restore fchmod if it existed before
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_load_cycle_without_fchmod(tmp_path: Path) -> None:
    """Issue #6938: Full save/load cycle should work without fchmod.

    This tests that multiple save operations work correctly when
    fchmod is unavailable (Windows scenario).
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    original_fchmod = getattr(os, "fchmod", None)
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # First save
        storage.save([Todo(id=1, text="first")])
        assert len(storage.load()) == 1

        # Second save (overwrites)
        storage.save([Todo(id=1, text="updated"), Todo(id=2, text="new")])
        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].text == "updated"
        assert loaded[1].text == "new"

        # Third save (appending logic at caller level)
        todos = storage.load()
        todos.append(Todo(id=3, text="appended"))
        storage.save(todos)
        assert len(storage.load()) == 3
    finally:
        if original_fchmod is not None:
            os.fchmod = original_fchmod
