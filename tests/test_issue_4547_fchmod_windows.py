"""Regression tests for issue #4547: os.fchmod not available on Windows.

Issue: os.fchmod raises AttributeError on Windows because it's a Unix-only function.
The code should handle this gracefully with a hasattr check or try/except.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path) -> None:
    """Issue #4547: save() should work when os.fchmod is not available (Windows).

    Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() gracefully skips permission setting on unsupported platforms
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows environment where os.fchmod doesn't exist
    with patch.object(os, 'fchmod', None):
        # This should NOT raise AttributeError
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

    # Verify save succeeded
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_works_when_fchmod_raises_attribute_error(tmp_path) -> None:
    """Issue #4547: save() should handle missing os.fchmod gracefully.

    On Windows, os.fchmod doesn't exist at all, so we simulate this by
    deleting the attribute temporarily.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Store original function if it exists
    original_fchmod = getattr(os, 'fchmod', None)

    # Simulate Windows by deleting the attribute entirely
    if hasattr(os, 'fchmod'):
        delattr(os, 'fchmod')

    try:
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)
    finally:
        # Restore original
        if original_fchmod is not None:
            os.fchmod = original_fchmod

    # Verify save succeeded
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_works_on_current_platform(tmp_path) -> None:
    """Issue #4547: save() should continue to work on current platform.

    This test ensures the fix doesn't break existing functionality.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo", done=True),
    ]

    # Should succeed normally on any platform
    storage.save(todos)

    # Verify content
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first todo"
    assert loaded[1].text == "second todo"
    assert loaded[1].done is True
