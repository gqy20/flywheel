"""Regression tests for issue #2546: os.fchmod is Unix-only, need Windows compatibility.

Issue: Code uses os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR) which works on Unix
but os.fchmod doesn't exist on Windows, potentially causing crashes.

The fix should either:
1. Use a try/except to handle Windows gracefully
2. Use hasattr check to avoid calling os.fchmod on Windows
3. Use os.chmod with the path instead (works cross-platform)

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import builtins
import os
import stat
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_does_not_crash_on_windows(tmp_path) -> None:
    """Issue #2546: TodoStorage.save() should work on Windows where os.fchmod doesn't exist.

    Before fix: May crash with AttributeError on Windows when calling os.fchmod
    After fix: Gracefully handles Windows or uses cross-platform approach
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by making fchmod non-existent
    # We need to patch both hasattr and fchmod to properly simulate Windows
    original_hasattr = builtins.hasattr

    def mock_hasattr(obj, name):
        if obj is os and name == "fchmod":
            return False  # Simulate os.fchmod not existing
        return original_hasattr(obj, name)

    with patch('builtins.hasattr', side_effect=mock_hasattr):
        # This should NOT crash even on Windows
        storage.save([Todo(id=1, text="test")])

    # Verify the file was saved correctly
    assert db.exists()
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "test"


def test_save_works_without_fchmod(tmp_path) -> None:
    """Issue #2546: Verify save works even when os.fchmod is completely unavailable.

    This test simulates a Windows environment where os.fchmod doesn't exist.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Temporarily remove fchmod to simulate Windows
    original_fchmod = getattr(os, 'fchmod', None)
    if original_fchmod is not None:
        delattr(os, 'fchmod')

    try:
        # This should work on Windows too
        storage.save([Todo(id=1, text="test"), Todo(id=2, text="test2")])

        # Verify the file was saved correctly
        assert db.exists()
        todos = storage.load()
        assert len(todos) == 2
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_comment_matches_actual_behavior() -> None:
    """Issue #2546: The comment says 0o600 which is correct for stat.S_IRUSR | stat.S_IWUSR.

    Verify that stat.S_IRUSR | stat.S_IWUSR equals 0o600.
    """
    # Verify the constants match what the comment says
    expected = 0o600
    actual = stat.S_IRUSR | stat.S_IWUSR
    assert actual == expected, (
        f"Comment says 0o600 but code uses {oct(actual)}. "
        f"This creates confusion about actual permissions."
    )
