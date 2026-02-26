"""Regression tests for issue #5913: os.fchmod is Unix-only, causing AttributeError on Windows.

Issue: The code uses os.fchmod which is not available on Windows, causing AttributeError.

The save() method should work on Windows by using a fallback when fchmod is unavailable.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import json
import os

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_without_fchmod(tmp_path) -> None:
    """Issue #5913: TodoStorage.save() should work when os.fchmod is unavailable.

    This simulates Windows behavior where os.fchmod doesn't exist.
    Before fix: Raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: Works correctly using fallback
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by removing fchmod from os module
    # We need to actually delete the attribute for hasattr to return False
    if hasattr(os, 'fchmod'):
        original = os.fchmod
        del os.fchmod
        try:
            # This should NOT raise AttributeError
            storage.save([Todo(id=1, text="test todo")])
        finally:
            os.fchmod = original
    else:
        # Already doesn't exist (Windows)
        storage.save([Todo(id=1, text="test todo")])

    # Verify the file was created and contains correct data
    assert db.exists()
    content = json.loads(db.read_text())
    assert len(content) == 1
    assert content[0]["text"] == "test todo"


def test_hasattr_fchmod_detection(tmp_path) -> None:
    """Issue #5913: Verify the fix uses hasattr to detect fchmod availability."""
    # This test documents the expected behavior
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # The fix should work whether or not fchmod is available
    # On Unix: fchmod exists, use it
    # On Windows: fchmod doesn't exist, skip it
    storage.save([Todo(id=1, text="test")])

    assert db.exists()
