"""Regression tests for issue #5175: os.fchmod not available on Windows.

Issue: os.fchmod() raises AttributeError on Windows because it's Unix-only.
The code should gracefully handle platforms where os.fchmod is unavailable.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_handles_missing_fchmod_gracefully(tmp_path) -> None:
    """Issue #5175: save() should not fail when os.fchmod is unavailable.

    On Windows, os.fchmod doesn't exist. The code should check for its
    availability before calling it.

    Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() completes successfully, skipping fchmod on unsupported platforms
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by removing fchmod from os module entirely
    original_fchmod = getattr(os, 'fchmod', None)
    if hasattr(os, 'fchmod'):
        delattr(os, 'fchmod')

    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test task")])

        # Verify the data was actually saved
        saved_todos = storage.load()
        assert len(saved_todos) == 1
        assert saved_todos[0].text == "test task"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_works_when_fchmod_attribute_missing(tmp_path) -> None:
    """Issue #5175: save() should work when os has no fchmod attribute at all.

    This simulates the actual Windows environment where os.fchmod doesn't exist.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save the original fchmod (may or may not exist depending on platform)
    original_fchmod = getattr(os, 'fchmod', None)

    # Remove fchmod entirely to simulate Windows
    if hasattr(os, 'fchmod'):
        delattr(os, 'fchmod')

    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=2, text="another test")])

        # Verify the data was saved
        saved_todos = storage.load()
        assert len(saved_todos) == 1
        assert saved_todos[0].text == "another test"
    finally:
        # Restore fchmod if it existed originally
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_still_sets_permissions_on_unix(tmp_path) -> None:
    """Issue #5175: On Unix-like systems, permissions should still be set correctly.

    This ensures the fix doesn't break the existing security behavior on Unix.
    This test only runs meaningfully on Unix-like systems.
    """
    if not hasattr(os, 'fchmod'):
        # Skip on Windows - this test is for Unix behavior
        return

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=3, text="permission test")])

    # On Unix, the file should have 0o600 permissions
    file_stat = db.stat()
    file_mode = file_stat.st_mode & 0o777

    # The file should have exactly 0o600 (rw-------) permissions
    assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"
