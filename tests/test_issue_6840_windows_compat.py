"""Regression tests for issue #6840: os.fchmod is Unix-only, raises AttributeError on Windows.

Issue: The code uses os.fchmod() which only exists on Unix platforms.
On Windows, this raises AttributeError because the function doesn't exist.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path) -> None:
    """Issue #6840: save() should work on Windows where os.fchmod doesn't exist.

    This simulates the Windows environment by removing os.fchmod temporarily.
    Before fix: Raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: Works gracefully with cross-platform fallback
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Simulate Windows by removing os.fchmod
    original_fchmod = getattr(os, "fchmod", None)
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError on Windows
        storage.save(todos)

        # Verify the save succeeded
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        # Restore original fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_works_with_mocked_missing_fchmod(tmp_path) -> None:
    """Issue #6840: Alternative test using mock to simulate missing os.fchmod.

    This test uses a more explicit mock approach to ensure the code path
    works correctly when os.fchmod is unavailable.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="cross-platform test")]

    # Store original and remove fchmod entirely (simulating Windows)
    original_fchmod = getattr(os, "fchmod", None)
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # Should work without AttributeError
        storage.save(todos)

        # Verify data was saved correctly
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "cross-platform test"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_works_with_hasattr_check_pattern(tmp_path) -> None:
    """Issue #6840: Verify save() uses hasattr check or try/except for os.fchmod.

    This test verifies that the code follows the recommended pattern:
    - Check hasattr(os, 'fchmod') before calling, OR
    - Use try/except with fallback

    The implementation should gracefully handle missing os.fchmod.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="graceful degradation test")]

    # Store original state
    original_has_fchmod = hasattr(os, "fchmod")

    # Remove fchmod to simulate Windows
    if original_has_fchmod:
        original_fchmod = os.fchmod
        delattr(os, "fchmod")

    try:
        # Should work without crashing
        storage.save(todos)

        # Verify the file was created and is readable
        assert db.exists(), "Database file should be created"
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "graceful degradation test"
    finally:
        # Restore fchmod if it existed originally
        if original_has_fchmod:
            os.fchmod = original_fchmod
