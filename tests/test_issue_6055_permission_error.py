"""Regression tests for issue #6055: load() should wrap PermissionError as ValueError.

Issue: load() raises raw PermissionError instead of wrapped ValueError when file
is not readable. The current code only catches json.JSONDecodeError but not
PermissionError from read_text().

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_unreadable_file_raises_value_error_not_permission_error(tmp_path) -> None:
    """Issue #6055: load() on unreadable file should raise ValueError, not PermissionError.

    Before fix: load() raises raw PermissionError when file has no read permissions
    After fix: load() raises ValueError with a clear message about permission denied
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file with valid JSON content first
    db.write_text("[]", encoding="utf-8")

    # Remove read permissions from the file
    os.chmod(db, 0o000)

    try:
        # Should raise ValueError (not PermissionError)
        with pytest.raises(ValueError, match=r"permission|denied|read") as exc_info:
            storage.load()

        # Verify the error message is helpful
        error_msg = str(exc_info.value).lower()
        assert "permission" in error_msg or "denied" in error_msg or "read" in error_msg, (
            f"Error message should mention permission/read issue: {exc_info.value}"
        )
    finally:
        # Restore permissions for cleanup
        os.chmod(db, 0o644)


def test_load_unreadable_file_error_message_contains_path(tmp_path) -> None:
    """Issue #6055: Error message should contain the file path for debugging."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file with valid JSON content first
    db.write_text("[]", encoding="utf-8")

    # Remove read permissions from the file
    os.chmod(db, 0o000)

    try:
        with pytest.raises(ValueError) as exc_info:
            storage.load()

        # Error message should contain the path
        error_msg = str(exc_info.value)
        assert "todo.json" in error_msg, (
            f"Error message should contain file path: {error_msg}"
        )
    finally:
        # Restore permissions for cleanup
        os.chmod(db, 0o644)


def test_load_readable_file_still_works(tmp_path) -> None:
    """Verify that the fix doesn't break normal file reading."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file with valid JSON content
    todos = [Todo(id=1, text="test task", done=False)]
    storage.save(todos)

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test task"
