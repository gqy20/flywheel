"""Regression tests for issue #5389: Explicit parent directory check.

Issue: _ensure_parent_directory checks all parent paths but the check for
path.parent being a file is implicit in the loop. Should add explicit check
for parent with clear error message.

These tests validate the explicit parent check behavior.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory


def test_ensure_parent_directory_explicit_parent_is_file_check(tmp_path) -> None:
    """Issue #5389: Should raise ValueError with clear message when parent is a file.

    The error message should explicitly mention 'not a directory' for clarity.
    """
    # Create a file where we expect a directory
    parent_file = tmp_path / "blocking_file"
    parent_file.write_text("I am a file, not a directory")

    # db_path's parent is the file
    db_path = parent_file / "todo.json"

    # Should raise ValueError with clear message
    with pytest.raises(ValueError) as exc_info:
        _ensure_parent_directory(db_path)

    # Error message should contain 'not a directory'
    error_msg = str(exc_info.value)
    assert "not a directory" in error_msg.lower(), (
        f"Error message should contain 'not a directory': {error_msg}"
    )
    # Error message should mention the parent path
    assert str(parent_file) in error_msg, (
        f"Error message should mention the blocking file path: {error_msg}"
    )


def test_ensure_parent_directory_parent_not_exists_creates_dir(tmp_path) -> None:
    """Issue #5389: When parent doesn't exist, should successfully create it."""
    # Path with non-existent parent
    db_path = tmp_path / "new_dir" / "subdir" / "todo.json"

    # Should succeed without error
    _ensure_parent_directory(db_path)

    # Parent should now exist as a directory
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()


def test_ensure_parent_directory_parent_is_directory_succeeds(tmp_path) -> None:
    """Issue #5389: When parent exists as directory, should succeed."""
    # Pre-create parent directory
    parent_dir = tmp_path / "existing_dir"
    parent_dir.mkdir()

    db_path = parent_dir / "todo.json"

    # Should succeed without error
    _ensure_parent_directory(db_path)


def test_storage_save_parent_is_file_clear_error(tmp_path) -> None:
    """Issue #5389: TodoStorage.save should provide clear error when parent is a file."""
    # Create a file as the parent
    parent_file = tmp_path / "db.json"
    parent_file.write_text("file content")

    # Try to use it as parent directory
    db_path = parent_file / "data.json"
    storage = TodoStorage(str(db_path))

    # Save should fail with clear error
    with pytest.raises(ValueError) as exc_info:
        storage.save([])

    error_msg = str(exc_info.value)
    assert "not a directory" in error_msg.lower(), (
        f"Error message should contain 'not a directory': {error_msg}"
    )
