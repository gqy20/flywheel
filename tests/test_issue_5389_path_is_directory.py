"""Regression tests for issue #5389: Misleading error when path itself is a directory.

Issue: _ensure_parent_directory checks all parent paths but doesn't check if the
target path itself is a directory. When the user accidentally specifies a directory
as the db_path, the error message is confusing (IsADirectoryError) instead of
a clear ValueError.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_save_fails_with_clear_error_when_target_is_directory(tmp_path) -> None:
    """Issue #5389: Should fail with clear error when target path is a directory.

    Before fix: save raises IsADirectoryError with confusing message
    After fix: Should detect that target is a directory and raise ValueError with clear message
    """
    # Create a directory at the target db path
    target_dir = tmp_path / "todo.json"
    target_dir.mkdir()

    # Try to use this directory as the db path
    storage = TodoStorage(str(target_dir))

    # Should fail with clear error message about path being a directory
    with pytest.raises(ValueError, match=r"(directory|not a file)"):
        storage.save([])


def test_save_fails_with_clear_error_when_target_is_directory_nested(tmp_path) -> None:
    """Issue #5389: Same test but with nested directory structure."""
    # Create parent directory
    parent_dir = tmp_path / "data"
    parent_dir.mkdir()

    # Create a directory where we expect a file
    target_dir = parent_dir / "todo.json"
    target_dir.mkdir()

    storage = TodoStorage(str(target_dir))

    with pytest.raises(ValueError, match=r"(directory|not a file)"):
        storage.save([])


def test_parent_is_file_still_works(tmp_path) -> None:
    """Issue #5389: Existing behavior for parent being a file should still work."""
    # This is existing test from issue 1894, but we verify it still works
    conflicting_file = tmp_path / "blocking.json"
    conflicting_file.write_text("file content")

    db_path = conflicting_file / "data.json"
    storage = TodoStorage(str(db_path))

    with pytest.raises(ValueError, match=r"(not a directory|file)"):
        storage.save([])
